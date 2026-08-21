"""Testes do Behavioral Monitoring — teste KS real (scipy), sem simulação."""
from __future__ import annotations

import random

import pytest

from core.behavioral_monitoring.drift import detect_drift
from core.policy_engine.engine import evaluate
from core.trust_score.scorer import compute_trust_score
from shared.schemas import DataCategory, DriftReport, LegalBasis, PIIDetectionResult

_NEUTRAL_PII = PIIDetectionResult(findings=[], has_sensitive_data=False, summary="sem PII")


def test_identical_distributions_no_drift():
    rng = random.Random(1)
    baseline = [rng.gauss(50, 10) for _ in range(200)]
    rng2 = random.Random(1)
    current = [rng2.gauss(50, 10) for _ in range(200)]
    result = detect_drift(baseline, current, metric_name="teste")
    assert isinstance(result, DriftReport)
    assert result.drift_detected is False
    assert result.p_value > result.alpha


def test_clearly_shifted_distribution_detects_drift():
    rng = random.Random(2)
    baseline = [rng.gauss(50, 5) for _ in range(200)]
    current = [rng.gauss(90, 5) for _ in range(200)]  # média bem diferente
    result = detect_drift(baseline, current, metric_name="latencia_ms")
    assert result.drift_detected is True
    assert result.p_value < result.alpha
    assert "Drift DETECTADO" in result.summary


def test_sample_sizes_recorded():
    result = detect_drift([1.0, 2.0, 3.0], [1.0, 2.0], metric_name="x")
    assert result.baseline_size == 3
    assert result.current_size == 2


def test_custom_alpha_threshold():
    rng = random.Random(3)
    baseline = [rng.gauss(0, 1) for _ in range(100)]
    current = [rng.gauss(0.3, 1) for _ in range(100)]  # diferença pequena
    strict = detect_drift(baseline, current, alpha=0.001)
    lenient = detect_drift(baseline, current, alpha=0.5)
    # Com alpha mais permissivo, mais fácil detectar "drift" (limiar mais alto).
    assert lenient.p_value == strict.p_value  # mesmo teste estatístico
    assert lenient.alpha > strict.alpha


def test_too_few_values_raises():
    with pytest.raises(ValueError):
        detect_drift([1.0], [1.0, 2.0])
    with pytest.raises(ValueError):
        detect_drift([1.0, 2.0], [1.0])


def test_drift_over_real_trust_scores_low_vs_high_risk():
    # Composição real: policy_engine + trust_score reais, duas "populações"
    # de decisão bem diferentes -- prova que a métrica monitorada pode vir
    # de qualquer módulo V1/V2 sem adaptação.
    low_risk_scores = []
    for _ in range(15):
        decisions = evaluate(data_categories=[DataCategory.PERSONAL], legal_basis=LegalBasis.LEGITIMATE_INTEREST)
        low_risk_scores.append(compute_trust_score(pii_result=_NEUTRAL_PII, policy_decisions=decisions).score)

    high_risk_scores = []
    for _ in range(15):
        decisions = evaluate(
            data_categories=[DataCategory.SENSITIVE], legal_basis=LegalBasis.NOT_DETERMINED,
            context={"data_subtype": "biometric", "automated_decision": True, "human_review": False},
        )
        high_risk_scores.append(compute_trust_score(pii_result=_NEUTRAL_PII, policy_decisions=decisions).score)

    result = detect_drift(low_risk_scores, high_risk_scores, metric_name="trust_score")
    assert result.drift_detected is True  # 100.0 constante vs 5.0 constante -- claramente diferente
