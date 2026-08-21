"""Testes do Federated Governance — agregação real, inclusive contra
TrustScoreResult produzidos de verdade por trust_score.compute_trust_score."""
from __future__ import annotations

import pytest

from core.federated_governance.federation import aggregate_federation, build_node_report
from core.policy_engine.engine import evaluate
from core.trust_score.scorer import compute_trust_score
from shared.schemas import (
    DataCategory,
    FederatedSummary,
    LegalBasis,
    NodeReport,
    PIIDetectionResult,
    RiskLevel,
    TrustScoreResult,
)

_NEUTRAL_PII = PIIDetectionResult(findings=[], has_sensitive_data=False, summary="sem PII")


def _score(value: float, risk: RiskLevel) -> TrustScoreResult:
    return TrustScoreResult(score=value, risk_level=risk, components={})


def test_build_node_report_aggregates_correctly():
    scores = [_score(90, RiskLevel.LOW), _score(80, RiskLevel.LOW), _score(3, RiskLevel.CRITICAL)]
    report = build_node_report("filial-sp", scores)
    assert isinstance(report, NodeReport)
    assert report.total_evaluations == 3
    assert report.avg_trust_score == pytest.approx((90 + 80 + 3) / 3, abs=0.01)
    assert report.deny_count == 1
    assert report.risk_level_counts == {"low": 2, "critical": 1}


def test_build_node_report_empty_raises():
    with pytest.raises(ValueError):
        build_node_report("filial-x", [])


def test_build_node_report_from_real_trust_score():
    # Composição real: policy_engine -> trust_score -> federated_governance,
    # sem nenhum mock.
    decisions = evaluate(data_categories=[DataCategory.PERSONAL], legal_basis=LegalBasis.LEGITIMATE_INTEREST)
    real_score = compute_trust_score(pii_result=_NEUTRAL_PII, policy_decisions=decisions)
    report = build_node_report("filial-rj", [real_score])
    assert report.total_evaluations == 1
    assert report.avg_trust_score == real_score.score


def test_aggregate_federation_weighted_average():
    node_a = build_node_report("A", [_score(100, RiskLevel.LOW)] * 10)
    node_b = build_node_report("B", [_score(0, RiskLevel.CRITICAL)] * 1)
    summary = aggregate_federation([node_a, node_b])
    assert isinstance(summary, FederatedSummary)
    # Ponderado por volume: 10 avaliações a 100 + 1 a 0 -> média = 1000/11
    assert summary.weighted_avg_trust_score == pytest.approx(1000 / 11, abs=0.1)


def test_aggregate_federation_totals():
    node_a = build_node_report("A", [_score(90, RiskLevel.LOW), _score(3, RiskLevel.CRITICAL)])
    node_b = build_node_report("B", [_score(4, RiskLevel.CRITICAL)])
    summary = aggregate_federation([node_a, node_b])
    assert summary.node_count == 2
    assert summary.total_evaluations == 3
    assert summary.total_deny_count == 2


def test_aggregate_federation_empty_raises():
    with pytest.raises(ValueError):
        aggregate_federation([])


def test_aggregate_federation_summary_mentions_worst_and_best_node():
    node_a = build_node_report("Melhor", [_score(95, RiskLevel.LOW)])
    node_b = build_node_report("Pior", [_score(2, RiskLevel.CRITICAL)])
    summary = aggregate_federation([node_a, node_b])
    assert "Melhor" in summary.summary
    assert "Pior" in summary.summary


def test_single_node_federation():
    node = build_node_report("Único", [_score(50, RiskLevel.MEDIUM)])
    summary = aggregate_federation([node])
    assert summary.node_count == 1
    assert summary.weighted_avg_trust_score == 50.0
