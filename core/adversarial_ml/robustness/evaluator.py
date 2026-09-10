"""Avaliador de robustez — roda a bateria de ataques contra um modelo,
opcionalmente compara com uma defesa, e monta o `RobustnessMetrics`.
"""
from __future__ import annotations

import numpy as np

from core.adversarial_ml.attacks.fgsm import fgsm_attack
from core.adversarial_ml.attacks.pgd import pgd_attack
from core.adversarial_ml.models import TargetModel
from core.adversarial_ml.robustness.metrics import (
    classify_risk,
    min_perturbation_budget,
    robustness_curve,
)
from shared.schemas import AdversarialAttackResult, RobustnessMetrics


def evaluate_robustness(
    model: TargetModel,
    X: np.ndarray,
    y: np.ndarray,
    epsilon: float = 0.1,
    curve_epsilons: list[float] | None = None,
) -> tuple[list[AdversarialAttackResult], RobustnessMetrics]:
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=int)
    curve_epsilons = curve_epsilons or [0.0, 0.02, 0.05, 0.1, 0.2, 0.3]

    fgsm_res = fgsm_attack(model, X, y, epsilon=epsilon)
    pgd_res = pgd_attack(model, X, y, epsilon=epsilon)

    curve = robustness_curve(model, X, y, curve_epsilons)
    clean_acc = fgsm_res.clean_accuracy
    robust_acc = pgd_res.adversarial_accuracy

    metrics = RobustnessMetrics(
        clean_accuracy=clean_acc,
        robust_accuracy=robust_acc,
        min_perturbation_budget=min_perturbation_budget(curve, target_accuracy=clean_acc * 0.5),
        robustness_curve=curve,
        risk_level=classify_risk(clean_acc, robust_acc),
    )
    return [fgsm_res, pgd_res], metrics
