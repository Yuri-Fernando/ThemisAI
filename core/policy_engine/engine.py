"""Policy Engine — avalia decisões de política LGPD para tratamento de dados por IA.

O motor carrega uma base declarativa de políticas (`policies.yaml`) e, para um dado
cenário de entrada (categorias de dado, base legal e contexto operacional), retorna
todas as decisões de política aplicáveis (`shared.schemas.PolicyDecision`). Mais de
uma política pode se aplicar simultaneamente — por exemplo, dado sensível de saúde
sobre um menor de idade aciona tanto a política de dado de saúde quanto a de menor.

Ver `policies.yaml` para a estrutura declarativa completa (trigger/outcomes) e o
vocabulário de chaves de contexto reconhecidas.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from shared.schemas import (
    DataCategory,
    LegalBasis,
    PolicyDecision,
    PolicyDecisionStatus,
    RiskLevel,
)

_DEFAULT_POLICIES_PATH = Path(__file__).parent / "policies.yaml"


def _load_policies(policies_path: Path | str | None = None) -> list[dict[str, Any]]:
    """Carrega e retorna a lista de políticas declaradas em `policies.yaml`."""
    path = Path(policies_path) if policies_path else _DEFAULT_POLICIES_PATH
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not data:
        return []
    return data.get("policies", [])


def _as_value(item: Any) -> str:
    """Normaliza um DataCategory/LegalBasis (Enum) ou string crua para seu valor string."""
    return item.value if hasattr(item, "value") else item


def _trigger_matches(
    trigger: dict[str, Any],
    data_category_values: set[str],
    legal_basis_value: str,
    context: dict[str, Any],
) -> bool:
    """Verifica se um `trigger` de política casa com o cenário avaliado."""
    cats_any = trigger.get("data_categories_any")
    if cats_any is not None and not (set(cats_any) & data_category_values):
        return False

    cats_all = trigger.get("data_categories_all")
    if cats_all is not None and not set(cats_all).issubset(data_category_values):
        return False

    cats_none = trigger.get("data_categories_none")
    if cats_none is not None and (set(cats_none) & data_category_values):
        return False

    legal_basis_in = trigger.get("legal_basis_in")
    if legal_basis_in is not None and legal_basis_value not in legal_basis_in:
        return False

    legal_basis_not_in = trigger.get("legal_basis_not_in")
    if legal_basis_not_in is not None and legal_basis_value in legal_basis_not_in:
        return False

    ctx_eq = trigger.get("context", {}) or {}
    for key, expected in ctx_eq.items():
        if context.get(key) != expected:
            return False

    ctx_ne = trigger.get("context_ne", {}) or {}
    for key, forbidden in ctx_ne.items():
        if context.get(key) == forbidden:
            return False

    return True


def _outcome_matches(
    when: dict[str, Any] | None,
    legal_basis_value: str,
    context: dict[str, Any],
) -> bool:
    """Verifica se o `when` de um outcome casa com o cenário avaliado.

    `when` ausente/vazio funciona como default (sempre casa) — deve ser o último
    outcome da lista de uma política.
    """
    if not when:
        return True

    legal_basis_in = when.get("legal_basis_in")
    if legal_basis_in is not None and legal_basis_value not in legal_basis_in:
        return False

    legal_basis_not_in = when.get("legal_basis_not_in")
    if legal_basis_not_in is not None and legal_basis_value in legal_basis_not_in:
        return False

    ctx_eq = when.get("context", {}) or {}
    for key, expected in ctx_eq.items():
        if context.get(key) != expected:
            return False

    ctx_ne = when.get("context_ne", {}) or {}
    for key, forbidden in ctx_ne.items():
        if context.get(key) == forbidden:
            return False

    return True


def evaluate(
    data_categories: list[DataCategory],
    legal_basis: LegalBasis,
    context: dict[str, Any] | None = None,
    policies_path: Path | str | None = None,
) -> list[PolicyDecision]:
    """Avalia as políticas de LGPD aplicáveis a um cenário de tratamento de dados por IA.

    Args:
        data_categories: categorias de dado envolvidas (Art. 5º LGPD).
        legal_basis: base legal declarada para o tratamento.
        context: sinais operacionais adicionais (ex.: `involves_minor`,
            `international_transfer`, `automated_decision`...). Ver `policies.yaml`
            para o vocabulário completo de chaves reconhecidas. `None` equivale a `{}`.
        policies_path: caminho alternativo para a base de políticas (usado em testes).
            Se omitido, usa `core/policy_engine/policies.yaml`.

    Returns:
        Lista de `PolicyDecision` — uma por política aplicável. Pode ser vazia quando
        nenhuma política do arquivo é relevante para o cenário informado (ex.: dado
        exclusivamente `not_personal`, sem nenhuma circunstância especial no contexto).
        Pode conter múltiplas decisões quando mais de uma política se aplica ao mesmo
        cenário — cada decisão é independente e deve ser considerada pelo chamador
        (o Governance Copilot é responsável por agregá-las, não este módulo).
    """
    context = context or {}
    category_values = {_as_value(cat) for cat in data_categories}
    legal_basis_value = _as_value(legal_basis)

    decisions: list[PolicyDecision] = []
    for policy in _load_policies(policies_path):
        trigger = policy.get("trigger", {}) or {}
        if not _trigger_matches(trigger, category_values, legal_basis_value, context):
            continue

        outcomes = policy.get("outcomes", []) or []
        chosen = next(
            (o for o in outcomes if _outcome_matches(o.get("when"), legal_basis_value, context)),
            None,
        )
        if chosen is None:
            # Trigger casou mas nenhum outcome (nem default) casou — política
            # incompleta para este cenário. Não inventamos um resultado: pulamos.
            continue

        decisions.append(
            PolicyDecision(
                policy_id=policy["id"],
                status=PolicyDecisionStatus(chosen["status"]),
                rationale=" ".join(chosen["rationale"].split()),
                mitigations=list(chosen.get("mitigations", [])),
                risk_level=RiskLevel(chosen["risk_level"]),
            )
        )

    return decisions
