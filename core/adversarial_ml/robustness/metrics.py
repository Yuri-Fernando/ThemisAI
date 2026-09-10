"""Métricas de robustez adversarial.

- `robust_accuracy`: acurácia sob o ataque mais forte avaliado (PGD).
- `min_perturbation_budget`: menor epsilon (L-inf) que derruba a acurácia
  abaixo de um alvo — mede quão "frágil" é a fronteira de decisão.
- `robustness_curve`: acurácia adversarial em função de epsilon.
"""
from __future__ import annotations

import numpy as np

from core.adversarial_ml.attacks.pgd import pgd_perturb
from core.adversarial_ml.models import TargetModel
from shared.schemas import RiskLevel


def robustness_curve(
    model: TargetModel,
    X: np.ndarray,
    y: np.ndarray,
    epsilons: list[float],
    alpha_ratio: float = 0.25,
    steps: int = 10,
) -> list[dict]:
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=int)
    curve = []
    for eps in epsilons:
        if eps == 0:
            acc = float((model.predict(X) == y).mean())
        else:
            X_adv = pgd_perturb(model, X, y, epsilon=eps, alpha=eps * alpha_ratio, steps=steps)
            acc = float((model.predict(X_adv) == y).mean())
        curve.append({"epsilon": round(float(eps), 4), "adversarial_accuracy": round(acc, 4)})
    return curve


def min_perturbation_budget(curve: list[dict], target_accuracy: float = 0.5) -> float | None:
    """Menor epsilon do `curve` em que a acurácia adversarial cai <= alvo."""
    for point in sorted(curve, key=lambda p: p["epsilon"]):
        if point["adversarial_accuracy"] <= target_accuracy:
            return point["epsilon"]
    return None


def classify_risk(clean_acc: float, robust_acc: float) -> RiskLevel:
    """Traduz a queda de acurácia sob ataque em um nível de risco de negócio."""
    drop = clean_acc - robust_acc
    if robust_acc < 0.25 or drop > 0.6:
        return RiskLevel.CRITICAL
    if robust_acc < 0.5 or drop > 0.4:
        return RiskLevel.HIGH
    if drop > 0.15:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW
