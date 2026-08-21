"""Regulatory Sandbox — simulação what-if de cenários regulatórios, SEM
efeitos colaterais: compõe `policy_engine.evaluate` + `trust_score.compute_trust_score`
de verdade (mesmos motores reais do V1), mas propositalmente NÃO grava nada
em `audit_logs` — essa é a diferença estrutural em relação ao `ripd_engine`,
que sempre grava evento de auditoria. Um sandbox serve para responder "e se
eu mudasse a base legal para X?" sem gerar ruído na trilha de auditoria de
produção.

Não reimplementa nenhuma lógica de política/score — só orquestra os módulos
reais do V1 num modo "dry-run".
"""
from __future__ import annotations

from core.policy_engine.engine import evaluate
from core.trust_score.scorer import compute_trust_score
from shared.schemas import PIIDetectionResult, SandboxComparison, SandboxResult, SandboxScenario

_NEUTRAL_PII_RESULT = PIIDetectionResult(
    findings=[],
    has_sensitive_data=False,
    summary="Sandbox: nenhum texto de projeto avaliado neste cenário (simulação declarativa, não escaneia PII).",
)


def simulate(scenario: SandboxScenario) -> SandboxResult:
    """Roda um cenário hipotético contra `policy_engine` + `trust_score`
    reais, sem gravar nada em `audit_logs`.

    Args:
        scenario: `SandboxScenario` com `data_categories`, `legal_basis` e
            `context` hipotéticos.

    Returns:
        `SandboxResult` com as decisões de política e o trust score que
        aquele cenário produziria de verdade.
    """
    decisions = evaluate(
        data_categories=scenario.data_categories,
        legal_basis=scenario.legal_basis,
        context=scenario.context,
    )
    trust = compute_trust_score(pii_result=_NEUTRAL_PII_RESULT, policy_decisions=decisions)
    return SandboxResult(scenario_name=scenario.name, policy_decisions=decisions, trust_score=trust)


def compare_scenarios(scenario_a: SandboxScenario, scenario_b: SandboxScenario) -> SandboxComparison:
    """Simula dois cenários e retorna a diferença entre eles — útil para
    responder "o que muda no trust score/decisões se eu trocar a base legal
    (ou o contexto) de A para B?".
    """
    result_a = simulate(scenario_a)
    result_b = simulate(scenario_b)

    ids_a = {d.policy_id for d in result_a.policy_decisions}
    ids_b = {d.policy_id for d in result_b.policy_decisions}
    added = sorted(ids_b - ids_a)
    removed = sorted(ids_a - ids_b)
    score_delta = round(result_b.trust_score.score - result_a.trust_score.score, 2)

    direction = "melhora" if score_delta > 0 else ("piora" if score_delta < 0 else "mantém")
    summary = (
        f"Cenário '{scenario_a.name}' ({result_a.trust_score.score:.1f}) -> "
        f"'{scenario_b.name}' ({result_b.trust_score.score:.1f}): {direction} o trust score em "
        f"{abs(score_delta):.1f} ponto(s)."
    )
    if added:
        summary += f" Novas políticas acionadas: {', '.join(added)}."
    if removed:
        summary += f" Políticas que deixam de se aplicar: {', '.join(removed)}."

    return SandboxComparison(
        scenario_a=result_a,
        scenario_b=result_b,
        score_delta=score_delta,
        decisions_added=added,
        decisions_removed=removed,
        summary=summary,
    )
