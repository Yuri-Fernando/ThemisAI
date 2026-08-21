"""Testes do Agent Tribunal — regra de precedência determinística, inclusive
contra decisões REAIS produzidas pelo policy_engine (não só fixtures)."""
from __future__ import annotations

import pytest

from core.agent_tribunal.tribunal import adjudicate
from core.policy_engine.engine import evaluate
from shared.schemas import DataCategory, LegalBasis, PolicyDecision, PolicyDecisionStatus, RiskLevel


def _decision(policy_id, status, risk_level="medium", rationale="motivo"):
    return PolicyDecision(policy_id=policy_id, status=PolicyDecisionStatus(status), rationale=rationale, risk_level=RiskLevel(risk_level))


def test_deny_beats_everything():
    decisions = [
        _decision("POL-A", "allow"),
        _decision("POL-B", "deny", "critical"),
        _decision("POL-C", "requires_human_review", "high"),
    ]
    verdict = adjudicate(decisions)
    assert verdict.final_status == PolicyDecisionStatus.DENY
    assert verdict.risk_level == RiskLevel.CRITICAL


def test_requires_human_review_beats_allow_with_mitigation():
    decisions = [
        _decision("POL-A", "allow_with_mitigation", "medium"),
        _decision("POL-B", "requires_human_review", "medium"),
    ]
    verdict = adjudicate(decisions)
    assert verdict.final_status == PolicyDecisionStatus.REQUIRES_HUMAN_REVIEW


def test_single_decision_passthrough():
    decisions = [_decision("POL-009", "allow", "low")]
    verdict = adjudicate(decisions)
    assert verdict.final_status == PolicyDecisionStatus.ALLOW
    assert verdict.decisions_considered == ["POL-009"]


def test_tie_on_status_broken_by_risk_level():
    decisions = [
        _decision("POL-A", "requires_human_review", "medium"),
        _decision("POL-B", "requires_human_review", "critical"),
    ]
    verdict = adjudicate(decisions)
    assert verdict.risk_level == RiskLevel.CRITICAL


def test_empty_decisions_raises():
    with pytest.raises(ValueError):
        adjudicate([])


def test_rationale_mentions_all_considered_policies():
    decisions = [_decision("POL-A", "allow"), _decision("POL-B", "deny", "critical")]
    verdict = adjudicate(decisions)
    assert "POL-A" in verdict.rationale
    assert "POL-B" in verdict.rationale


def test_real_concurrent_decisions_from_policy_engine():
    # Dado de saúde (sensível) sem base legal determinada -- aciona múltiplas
    # políticas reais simultaneamente (mesmo cenário testado em policy_engine/tests).
    decisions = evaluate(
        data_categories=[DataCategory.SENSITIVE],
        legal_basis=LegalBasis.NOT_DETERMINED,
        context={"data_subtype": "health"},
    )
    assert len(decisions) >= 1
    verdict = adjudicate(decisions)
    # A decisão mais restritiva dentre as reais deve vencer -- sanity check
    # de que o vencedor está de fato entre as piores presentes.
    statuses = {d.status for d in decisions}
    if PolicyDecisionStatus.DENY in statuses:
        assert verdict.final_status == PolicyDecisionStatus.DENY
    elif PolicyDecisionStatus.REQUIRES_HUMAN_REVIEW in statuses:
        assert verdict.final_status == PolicyDecisionStatus.REQUIRES_HUMAN_REVIEW
