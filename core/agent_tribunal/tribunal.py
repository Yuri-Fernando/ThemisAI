"""Agent Tribunal — adjudica um veredito único quando múltiplas `PolicyDecision`
concorrentes se aplicam ao mesmo cenário.

Fecha um TODO real deixado explicitamente pelo `policy_engine` no V1 (ver
`core/policy_engine/CHANGELOG.md`: "Não faz agregação/priorização entre
PolicyDecision concorrentes (delegado ao governance_copilot)") — este é o
módulo que assume essa responsabilidade, com uma regra determinística e
declarada: **a decisão mais restritiva vence** (precedência de severidade),
o mesmo princípio de "fail-cautious" já usado em `prompt_security` (V1).
"""
from __future__ import annotations

from shared.schemas import PolicyDecision, PolicyDecisionStatus, RiskLevel, TribunalVerdict

# Ordem de precedência: índice menor = mais restritivo = vence o "tribunal".
_STATUS_PRECEDENCE = {
    PolicyDecisionStatus.DENY: 0,
    PolicyDecisionStatus.REQUIRES_HUMAN_REVIEW: 1,
    PolicyDecisionStatus.ALLOW_WITH_MITIGATION: 2,
    PolicyDecisionStatus.ALLOW: 3,
}

_RISK_PRECEDENCE = {
    RiskLevel.CRITICAL: 0,
    RiskLevel.HIGH: 1,
    RiskLevel.MEDIUM: 2,
    RiskLevel.LOW: 3,
}

_STATUS_LABEL_PT = {
    PolicyDecisionStatus.DENY: "NEGADA",
    PolicyDecisionStatus.REQUIRES_HUMAN_REVIEW: "REQUER REVISÃO HUMANA",
    PolicyDecisionStatus.ALLOW_WITH_MITIGATION: "PERMITIDA COM MITIGAÇÃO",
    PolicyDecisionStatus.ALLOW: "PERMITIDA",
}


def adjudicate(decisions: list[PolicyDecision]) -> TribunalVerdict:
    """Adjudica um veredito único a partir de uma ou mais `PolicyDecision`.

    Regra determinística: vence a decisão de `status` mais restritivo
    (`DENY` > `REQUIRES_HUMAN_REVIEW` > `ALLOW_WITH_MITIGATION` > `ALLOW`);
    em caso de empate de `status`, vence o `risk_level` mais alto.

    Levanta `ValueError` se `decisions` estiver vazio (não há nada a
    adjudicar — o chamador deve decidir o comportamento default, este módulo
    não inventa um).
    """
    if not decisions:
        raise ValueError("adjudicate() requer ao menos uma PolicyDecision para adjudicar.")

    winner = min(
        decisions,
        key=lambda d: (_STATUS_PRECEDENCE[d.status], _RISK_PRECEDENCE[d.risk_level]),
    )

    considered = [d.policy_id for d in decisions]
    if len(decisions) == 1:
        rationale = (
            f"Única decisão considerada ({winner.policy_id}): {_STATUS_LABEL_PT[winner.status]}. "
            f"{winner.rationale}"
        )
    else:
        others = [d.policy_id for d in decisions if d.policy_id != winner.policy_id]
        rationale = (
            f"{len(decisions)} decisões concorrentes consideradas ({', '.join(considered)}). "
            f"Vencedora (mais restritiva): {winner.policy_id} — {_STATUS_LABEL_PT[winner.status]}. "
            f"{winner.rationale} Demais decisões consideradas mas superadas por precedência: "
            f"{', '.join(others)}."
        )

    return TribunalVerdict(
        decisions_considered=considered,
        final_status=winner.status,
        risk_level=winner.risk_level,
        rationale=rationale,
    )
