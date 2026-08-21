"""Constitutional AI — princípios declarativos (`constitution.yaml`) compilados
em checks executáveis, versão simples (conforme escopo do ROADMAP: "regras
declarativas → políticas executáveis, versão simples").

Mesmo padrão declarativo do `policy_engine`, mas mais simples de propósito:
cada artigo é uma linha vermelha ("nunca faça X quando Y"), sem branching de
múltiplos outcomes — `policy_engine` já cobre o caso de múltiplas decisões
possíveis; este módulo cobre invariantes que NUNCA podem ser violadas,
independentemente de qual política se aplique.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from shared.schemas import ConstitutionalCheckResult, ConstitutionalViolation, RiskLevel

_DEFAULT_CONSTITUTION_PATH = Path(__file__).parent / "constitution.yaml"


def _load_constitution(constitution_path: Path | str | None = None) -> list[dict[str, Any]]:
    path = Path(constitution_path) if constitution_path else _DEFAULT_CONSTITUTION_PATH
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not data:
        return []
    return data.get("constitution", [])


def _condition_matches(condition: dict[str, Any], context: dict[str, Any]) -> bool:
    ctx_eq = condition.get("context", {}) or {}
    if not ctx_eq:
        return False
    for key, expected in ctx_eq.items():
        if context.get(key) != expected:
            return False
    return True


def check_constitution(
    context: dict[str, Any],
    constitution_path: Path | str | None = None,
) -> ConstitutionalCheckResult:
    """Avalia `context` contra todos os artigos da constituição declarativa.

    Args:
        context: sinais operacionais do sistema avaliado (ex.:
            `{"automated_decision": True, "explainable": False}`). Vocabulário
            de chaves reconhecidas: ver `constitution.yaml`.
        constitution_path: caminho alternativo (usado em testes). Se omitido,
            usa `core/constitutional_ai/constitution.yaml`.

    Returns:
        `ConstitutionalCheckResult` com todas as violações encontradas
        (pode haver mais de uma) e `compliant = (len(violations) == 0)`.
    """
    context = context or {}
    articles = _load_constitution(constitution_path)

    violations: list[ConstitutionalViolation] = []
    for article in articles:
        condition = article.get("forbidden_when", {}) or {}
        if _condition_matches(condition, context):
            violations.append(
                ConstitutionalViolation(
                    principle_id=article["id"],
                    principle=article["principle"],
                    severity=RiskLevel(article["severity"]),
                    rationale=" ".join(article["description"].split()),
                )
            )

    compliant = len(violations) == 0
    if compliant:
        summary = f"Nenhuma violação constitucional detectada ({len(articles)} artigo(s) avaliado(s))."
    else:
        principles = ", ".join(f"{v.principle_id} ({v.principle})" for v in violations)
        summary = (
            f"{len(violations)} violação(ões) constitucional(is) detectada(s) de "
            f"{len(articles)} artigo(s) avaliado(s): {principles}."
        )

    return ConstitutionalCheckResult(
        context=context,
        violations=violations,
        compliant=compliant,
        summary=summary,
    )
