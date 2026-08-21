"""Fairness Audit — auditoria de equidade determinística sobre decisões de IA.

Motor 100% estatístico e determinístico (sem ML/treinamento): recebe um lote de
registros de decisão (cada um com um resultado e o valor de um atributo protegido,
ex. gênero, raça autodeclarada, faixa etária) e calcula métricas de equidade
padrão da literatura de fairness em ML — a **regra dos 80%** (disparate impact,
usada pela EEOC americana e citada em auditorias de IA no Brasil também) e a
**diferença de paridade demográfica**.

Não reimplementa nada de outro módulo — este é um motor standalone, assim como
`explainability` e `trust_score` documentaram no V1: recebe dados já produzidos
por um sistema de decisão (o próprio `policy_engine`/`trust_score`, ou qualquer
sistema externo) via injeção simples de uma lista de dicts.
"""
from __future__ import annotations

from typing import Any

from shared.schemas import FairnessAuditResult, FairnessMetric

DEFAULT_DISPARATE_IMPACT_THRESHOLD = 0.8  # "regra dos 80%"


def _selection_rate(records: list[dict[str, Any]], outcome_key: str, favorable_outcome: Any) -> float:
    if not records:
        return 0.0
    favorable = sum(1 for r in records if r.get(outcome_key) == favorable_outcome)
    return favorable / len(records)


def audit_fairness(
    records: list[dict[str, Any]],
    outcome_key: str,
    protected_attribute_key: str,
    favorable_outcome: Any = True,
    threshold: float = DEFAULT_DISPARATE_IMPACT_THRESHOLD,
) -> FairnessAuditResult:
    """Audita equidade de um lote de decisões em relação a um atributo protegido.

    Args:
        records: lista de decisões, cada uma um dict com ao menos `outcome_key`
            (o resultado da decisão) e `protected_attribute_key` (o grupo do
            titular dos dados, ex. `{"outcome": True, "gender": "F"}`).
        outcome_key: chave em cada record que contém o resultado da decisão.
        protected_attribute_key: chave em cada record que contém o valor do
            atributo protegido (o grupo a comparar).
        favorable_outcome: valor de `outcome_key` considerado "favorável" (ex.
            aprovado, contratado, crédito concedido). Default `True`.
        threshold: limiar da regra dos 80% (`disparate_impact_ratio >= threshold`
            para passar). Default 0.8 (convenção EEOC).

    Returns:
        FairnessAuditResult com taxa de seleção por grupo, métricas de
        disparate impact e diferença de paridade demográfica em relação ao
        grupo de maior taxa de seleção (`reference_group`), e um resumo em
        português.

    Levanta:
        ValueError: se `records` estiver vazio ou se `protected_attribute_key`
            não estiver presente em nenhum registro.
    """
    if not records:
        raise ValueError("audit_fairness requer ao menos um registro em `records`.")

    groups: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        if protected_attribute_key not in record:
            raise ValueError(
                f"Registro sem a chave de atributo protegido '{protected_attribute_key}': {record}"
            )
        group = str(record[protected_attribute_key])
        groups.setdefault(group, []).append(record)

    sample_sizes = {group: len(recs) for group, recs in groups.items()}
    selection_rates = {
        group: _selection_rate(recs, outcome_key, favorable_outcome) for group, recs in groups.items()
    }

    # Grupo de referência: maior taxa de seleção (convenção da regra dos 80%:
    # compara-se sempre contra o grupo mais favorecido).
    reference_group = max(selection_rates, key=lambda g: selection_rates[g])
    reference_rate = selection_rates[reference_group]

    metrics: list[FairnessMetric] = []
    if len(groups) < 2:
        # Só um grupo no lote: não há comparação possível. Documentado como
        # "justo por vacuidade" (nenhuma disparidade detectável), não como
        # "auditoria completa" — ver notebook de dev-log para a discussão.
        overall_fair = True
    else:
        overall_fair = True
        for group, rate in selection_rates.items():
            if group == reference_group:
                continue

            # Disparate impact ratio (regra dos 80%): grupo_rate / referência_rate.
            di_ratio = (rate / reference_rate) if reference_rate > 0 else 1.0
            di_passed = di_ratio >= threshold
            overall_fair = overall_fair and di_passed
            metrics.append(
                FairnessMetric(
                    metric_name="disparate_impact_ratio",
                    group=group,
                    reference_group=reference_group,
                    value=round(di_ratio, 4),
                    threshold=threshold,
                    passed=di_passed,
                    interpretation=(
                        f"Grupo '{group}' tem taxa de seleção {di_ratio:.1%} da taxa do grupo de "
                        f"referência '{reference_group}' — "
                        + (
                            "dentro da regra dos 80%."
                            if di_passed
                            else "ABAIXO da regra dos 80%, indício de impacto desproporcional."
                        )
                    ),
                )
            )

            # Diferença de paridade demográfica (em pontos percentuais).
            dpd = reference_rate - rate
            dpd_threshold = 1.0 - threshold  # mesma folga em escala de diferença
            dpd_passed = dpd <= dpd_threshold
            overall_fair = overall_fair and dpd_passed
            metrics.append(
                FairnessMetric(
                    metric_name="demographic_parity_difference",
                    group=group,
                    reference_group=reference_group,
                    value=round(dpd, 4),
                    threshold=round(dpd_threshold, 4),
                    passed=dpd_passed,
                    interpretation=(
                        f"Diferença de {dpd:.1%} na taxa de seleção entre '{reference_group}' e "
                        f"'{group}' — "
                        + ("dentro do limiar aceitável." if dpd_passed else "ACIMA do limiar aceitável.")
                    ),
                )
            )

    verdict = "SEM indícios de disparidade" if overall_fair else "COM indícios de disparidade"
    groups_summary = ", ".join(f"{g} ({r:.1%})" for g, r in sorted(selection_rates.items()))
    summary = (
        f"Auditoria de equidade sobre '{protected_attribute_key}' ({len(records)} registros, "
        f"{len(groups)} grupo(s)): {verdict} em relação ao grupo de referência "
        f"'{reference_group}' ({reference_rate:.1%} de taxa de seleção). "
        f"Taxas de seleção por grupo: {groups_summary}."
    )

    return FairnessAuditResult(
        protected_attribute=protected_attribute_key,
        reference_group=reference_group,
        sample_sizes=sample_sizes,
        selection_rates={g: round(r, 4) for g, r in selection_rates.items()},
        metrics=metrics,
        overall_fair=overall_fair,
        summary=summary,
    )
