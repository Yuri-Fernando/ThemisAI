"""FGSM — Fast Gradient Sign Method (Goodfellow et al., 2015).

x_adv = clip(x + epsilon * sign(∇_x loss(f(x), y)))

Ataque real: usa o gradiente do próprio modelo-alvo (analítico no
`LogisticRegressionModel`, por diferenças finitas no `BlackBoxModel`) e a
acurácia adversarial reportada é medida sobre `x_adv`.
"""
from __future__ import annotations

import numpy as np

from core.adversarial_ml.models import TargetModel
from shared.schemas import AdversarialAttackResult


def fgsm_perturb(
    model: TargetModel,
    X: np.ndarray,
    y: np.ndarray,
    epsilon: float,
    clip_min: float | None = None,
    clip_max: float | None = None,
) -> np.ndarray:
    """Retorna X_adv = X + epsilon * sign(grad)."""
    X = np.asarray(X, dtype=float)
    grad = model.gradient(X, np.asarray(y, dtype=int))
    X_adv = X + epsilon * np.sign(grad)
    if clip_min is not None or clip_max is not None:
        X_adv = np.clip(X_adv, clip_min, clip_max)
    return X_adv


def fgsm_attack(
    model: TargetModel,
    X: np.ndarray,
    y: np.ndarray,
    epsilon: float = 0.1,
    clip_min: float | None = None,
    clip_max: float | None = None,
) -> AdversarialAttackResult:
    """Executa FGSM e mede a queda de acurácia real do modelo."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=int)

    clean_pred = model.predict(X)
    clean_acc = float((clean_pred == y).mean())

    X_adv = fgsm_perturb(model, X, y, epsilon, clip_min, clip_max)
    adv_pred = model.predict(X_adv)
    adv_acc = float((adv_pred == y).mean())

    correct_before = clean_pred == y
    flipped = correct_before & (adv_pred != y)
    success_rate = float(flipped.sum() / max(correct_before.sum(), 1))

    return AdversarialAttackResult(
        attack="fgsm",
        epsilon=epsilon,
        clean_accuracy=round(clean_acc, 4),
        adversarial_accuracy=round(adv_acc, 4),
        accuracy_drop=round(clean_acc - adv_acc, 4),
        success_rate=round(success_rate, 4),
        samples_evaluated=len(X),
    )
