"""Propriedade formal concreta verificada por `checker.verify_invariant`:
o `agent_tribunal` (V2) SEMPRE escolhe `DENY` quando pelo menos uma
`PolicyDecision` de entrada tem `status=DENY` — a invariante de segurança
mais crítica desse módulo (é o que garante que uma única política restritiva
nunca é "diluída" por outras mais permissivas).

Este é um exemplo real de uso de `formal_verification` sobre um módulo já
existente do V2 — não uma demonstração isolada e descartável.
"""
from __future__ import annotations

import itertools

from core.agent_tribunal.tribunal import adjudicate
from core.formal_verification.checker import verify_invariant
from shared.schemas import PolicyDecision, PolicyDecisionStatus, RiskLevel, VerificationResult

_ALL_STATUSES = list(PolicyDecisionStatus)
_ALL_RISKS = list(RiskLevel)


def _build_domain(max_decisions: int):
    """Gera todas as combinações de 1 a `max_decisions` PolicyDecision,
    variando status e risk_level sobre a grade finita completa (4 status x 4
    níveis de risco = 16 combinações por decisão)."""
    grid = list(itertools.product(_ALL_STATUSES, _ALL_RISKS))
    for n in range(1, max_decisions + 1):
        for combo in itertools.product(grid, repeat=n):
            decisions = [
                PolicyDecision(
                    policy_id=f"P{i}",
                    status=status,
                    rationale="verificação formal",
                    risk_level=risk,
                )
                for i, (status, risk) in enumerate(combo)
            ]
            yield decisions


def _deny_precedence_holds(decisions: list[PolicyDecision]) -> bool:
    verdict = adjudicate(decisions)
    any_deny = any(d.status == PolicyDecisionStatus.DENY for d in decisions)
    if any_deny:
        return verdict.final_status == PolicyDecisionStatus.DENY
    return True  # propriedade só afirma algo quando há DENY na entrada


def verify_tribunal_deny_precedence(max_decisions: int = 3) -> VerificationResult:
    """Verifica exaustivamente, para toda combinação de 1 a `max_decisions`
    `PolicyDecision` sobre a grade finita completa de status x risco, que
    `adjudicate()` escolhe `DENY` sempre que ao menos uma decisão de entrada
    é `DENY`.

    `max_decisions=3` já cobre 16 + 16² + 16³ = 4.368 combinações — segundos
    de execução, mas cobre exaustivamente o espaço de estados até 3 decisões
    concorrentes (o caso realista mais comum do `policy_engine`).
    """
    return verify_invariant(
        property_name="agent_tribunal: DENY sempre vence quando presente na entrada",
        domain=_build_domain(max_decisions),
        check_fn=_deny_precedence_holds,
        describe_fn=lambda decs: str([(d.status.value, d.risk_level.value) for d in decs]),
    )
