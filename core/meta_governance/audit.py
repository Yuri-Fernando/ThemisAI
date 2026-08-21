"""Meta-Governance Layer — extração REAL do item "Meta-Governance Layer" do
V4: governança SOBRE governança. Enquanto `federated_governance` (V2) agrega
métricas de DECISÃO entre nós (trust score médio, contagem de DENY), este
módulo audita se cada nó da federação está de fato EXECUTANDO seus próprios
checks de saúde/compliance corretamente — governança recursiva de um nível
acima.

Recebe, por nó, um dict de resultados de checks já computados (o mesmo
formato que `self_healing_governance.check_and_heal` recebe) e calcula uma
taxa de compliance por nó e da federação inteira, sem nunca precisar dos
dados brutos por trás de cada check (mesmo princípio de fronteira mínima já
usado por `federated_governance`).
"""
from __future__ import annotations

from shared.schemas import MetaGovernanceReport, NodeComplianceReport

DEFAULT_COMPLIANCE_THRESHOLD = 1.0  # por padrão, exige 100% dos checks saudáveis


def audit_federation_health(
    node_health: dict[str, dict[str, bool]],
    compliance_threshold: float = DEFAULT_COMPLIANCE_THRESHOLD,
) -> MetaGovernanceReport:
    """Audita a saúde/compliance de múltiplos nós de uma federação.

    Args:
        node_health: `{node_id: {check_name: saudável?}}` — resultado de
            checks já computados por cada nó (ex. via
            `self_healing_governance.check_and_heal`, ou qualquer outra
            fonte de checks booleanos).
        compliance_threshold: taxa mínima de checks saudáveis (0.0-1.0) para
            um nó ser considerado "compliant". Default 1.0 (exige 100%).

    Levanta `ValueError` se `node_health` estiver vazio, ou se algum nó não
    tiver nenhum check (`{}`).
    """
    if not node_health:
        raise ValueError("audit_federation_health requer ao menos um nó em `node_health`.")

    per_node: list[NodeComplianceReport] = []
    for node_id, checks in node_health.items():
        if not checks:
            raise ValueError(f"Nó '{node_id}' não tem nenhum check em `node_health`.")

        total = len(checks)
        healthy = sum(1 for ok in checks.values() if ok)
        rate = healthy / total
        per_node.append(
            NodeComplianceReport(
                node_id=node_id,
                checks_total=total,
                checks_healthy=healthy,
                compliance_rate=round(rate, 4),
                compliant=rate >= compliance_threshold,
            )
        )

    non_compliant = [n.node_id for n in per_node if not n.compliant]
    total_checks = sum(n.checks_total for n in per_node)
    total_healthy = sum(n.checks_healthy for n in per_node)
    federation_rate = round(total_healthy / total_checks, 4) if total_checks else 0.0

    if not non_compliant:
        summary = (
            f"Federação com {len(per_node)} nó(s) totalmente em compliance "
            f"(taxa agregada {federation_rate:.0%}, limiar {compliance_threshold:.0%})."
        )
    else:
        summary = (
            f"Federação com {len(per_node)} nó(s), taxa agregada {federation_rate:.0%}. "
            f"{len(non_compliant)} nó(s) ABAIXO do limiar de {compliance_threshold:.0%}: "
            f"{', '.join(non_compliant)}."
        )

    return MetaGovernanceReport(
        federation_compliance_rate=federation_rate,
        non_compliant_nodes=non_compliant,
        per_node=per_node,
        summary=summary,
    )
