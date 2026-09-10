"""Testes das métricas de robustez, do orquestrador `run_security_assessment`
e da renderização do MODEL SECURITY REPORT."""
from __future__ import annotations

from core.adversarial_ml import run_security_assessment
from core.adversarial_ml.robustness.metrics import (
    classify_risk,
    min_perturbation_budget,
    robustness_curve,
)
from shared.schemas import ModelSecurityReport, RiskLevel


def test_robustness_curve_is_monotone_nonincreasing(trained_model, synthetic_dataset):
    ds = synthetic_dataset
    curve = robustness_curve(trained_model, ds["X_test"], ds["y_test"], [0.0, 0.05, 0.1, 0.2, 0.4])
    accs = [p["adversarial_accuracy"] for p in curve]
    # tolerância pequena para ruído do PGD com random start
    assert all(accs[i] >= accs[i + 1] - 0.1 for i in range(len(accs) - 1))


def test_min_perturbation_budget_picks_smallest_epsilon():
    curve = [
        {"epsilon": 0.0, "adversarial_accuracy": 0.95},
        {"epsilon": 0.1, "adversarial_accuracy": 0.7},
        {"epsilon": 0.2, "adversarial_accuracy": 0.3},
        {"epsilon": 0.4, "adversarial_accuracy": 0.1},
    ]
    assert min_perturbation_budget(curve, target_accuracy=0.5) == 0.2


def test_classify_risk_levels():
    assert classify_risk(0.95, 0.93) == RiskLevel.LOW
    assert classify_risk(0.95, 0.10) == RiskLevel.CRITICAL


def test_full_assessment_produces_rendered_report(trained_model, synthetic_dataset):
    ds = synthetic_dataset
    report = run_security_assessment(
        trained_model,
        ds["X_test"], ds["y_test"], n_classes=ds["n_classes"],
        model_name="synthetic-logreg",
        epsilon=0.3,
        X_train=ds["X_train"], y_train=ds["y_train"],
        include_defense=True,
    )
    assert isinstance(report, ModelSecurityReport)
    assert report.rendered_report.startswith("=")
    assert "MODEL SECURITY REPORT" in report.rendered_report
    assert {a.attack for a in report.attacks} >= {"fgsm", "pgd", "extraction", "poisoning"}
    assert len(report.defenses) == 1
    assert report.recommendations
