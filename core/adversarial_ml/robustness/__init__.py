"""Avaliação e métricas de robustez adversarial + renderização de relatório."""
from __future__ import annotations

from core.adversarial_ml.robustness.evaluator import evaluate_robustness
from core.adversarial_ml.robustness.metrics import (
    classify_risk,
    min_perturbation_budget,
    robustness_curve,
)
from core.adversarial_ml.robustness.report import render_model_security_report

__all__ = [
    "evaluate_robustness",
    "robustness_curve",
    "min_perturbation_budget",
    "classify_risk",
    "render_model_security_report",
]
