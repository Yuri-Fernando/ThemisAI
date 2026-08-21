"""Federated Governance — agrega métricas de governança de IA entre múltiplos
"nós" (unidades organizacionais, filiais, subsidiárias) SEM centralizar o
dado bruto: cada nó calcula localmente seu próprio `NodeReport` (agregado,
sem nenhum `TrustScoreResult` individual saindo do nó), e só os `NodeReport`
— já agregados — cruzam a fronteira para virar um `FederatedSummary`.

Esse é o padrão real de "governança federada": a organização central nunca
vê os scores individuais de decisão de cada filial, só os agregados que cada
filial decidiu expor — compatível com cenários onde cada unidade tem sua
própria base legal/jurisdição e não pode compartilhar dado granular.
"""
from __future__ import annotations

from shared.schemas import FederatedSummary, NodeReport, TrustScoreResult


def build_node_report(node_id: str, trust_scores: list[TrustScoreResult]) -> NodeReport:
    """Agrega uma lista de `TrustScoreResult` (produzidos localmente, ex. por
    `trust_score.compute_trust_score` real, dentro do nó) num `NodeReport`
    resumido — o único artefato que sai do nó.

    Levanta `ValueError` se `trust_scores` estiver vazio.
    """
    if not trust_scores:
        raise ValueError(f"Nó '{node_id}' não tem nenhum TrustScoreResult para agregar.")

    total = len(trust_scores)
    avg_score = sum(ts.score for ts in trust_scores) / total
    deny_count = sum(1 for ts in trust_scores if ts.score <= 5.0)  # piso de DENY documentado em trust_score
    risk_counts: dict[str, int] = {}
    for ts in trust_scores:
        key = ts.risk_level.value
        risk_counts[key] = risk_counts.get(key, 0) + 1

    return NodeReport(
        node_id=node_id,
        total_evaluations=total,
        avg_trust_score=round(avg_score, 2),
        deny_count=deny_count,
        risk_level_counts=risk_counts,
    )


def aggregate_federation(node_reports: list[NodeReport]) -> FederatedSummary:
    """Combina `NodeReport`s (já agregados por nó) num `FederatedSummary`
    global, ponderado pelo número de avaliações de cada nó — sem nunca
    precisar do dado bruto de nenhum nó individual.

    Levanta `ValueError` se `node_reports` estiver vazio.
    """
    if not node_reports:
        raise ValueError("aggregate_federation requer ao menos um NodeReport.")

    total_evaluations = sum(r.total_evaluations for r in node_reports)
    if total_evaluations == 0:
        weighted_avg = 0.0
    else:
        weighted_avg = sum(r.avg_trust_score * r.total_evaluations for r in node_reports) / total_evaluations

    total_deny = sum(r.deny_count for r in node_reports)
    worst_node = min(node_reports, key=lambda r: r.avg_trust_score)
    best_node = max(node_reports, key=lambda r: r.avg_trust_score)

    summary = (
        f"Federação de {len(node_reports)} nó(s), {total_evaluations} avaliação(ões) no total. "
        f"Trust score médio ponderado: {weighted_avg:.1f}/100. "
        f"{total_deny} decisão(ões) DENY no total. "
        f"Nó com pior score médio: '{worst_node.node_id}' ({worst_node.avg_trust_score:.1f}); "
        f"melhor: '{best_node.node_id}' ({best_node.avg_trust_score:.1f})."
    )

    return FederatedSummary(
        node_count=len(node_reports),
        total_evaluations=total_evaluations,
        weighted_avg_trust_score=round(weighted_avg, 2),
        total_deny_count=total_deny,
        per_node=list(node_reports),
        summary=summary,
    )
