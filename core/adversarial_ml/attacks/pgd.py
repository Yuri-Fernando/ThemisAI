"""PGD — Projected Gradient Descent (Madry et al., 2018).

Iteração de FGSM com passo `alpha`, projetada de volta na bola L-infinito de
raio `epsilon` a cada passo. É o ataque de referência ("first-order
adversary") para avaliar robustez — mais forte que FGSM.
"""
from __future__ import annotations

import numpy as np

from core.adversarial_ml.models import TargetModel
from shared.schemas import AdversarialAttackResult


def pgd_perturb(
    model: TargetModel,
    X: np.ndarray,
    y: np.ndarray,
    epsilon: float = 0.1,
    alpha: float = 0.02,
    steps: int = 10,
    clip_min: float | None = None,
    clip_max: float | None = None,
    random_start: bool = True,
    seed: int = 0,
) -> np.ndarray:
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=int)
    rng = np.random.default_rng(seed)

    if random_start:
        delta = rng.uniform(-epsilon, epsilon, size=X.shape)
    else:
        delta = np.zeros_like(X)
    X_adv = X + delta

    for _ in range(steps):
        grad = model.gradient(X_adv, y)
        X_adv = X_adv + alpha * np.sign(grad)
        # projeta de volta na bola L-inf de raio epsilon em torno de X
        X_adv = np.clip(X_adv, X - epsilon, X + epsilon)
        if clip_min is not None or clip_max is not None:
            X_adv = np.clip(X_adv, clip_min, clip_max)

    return X_adv


def pgd_attack(
    model: TargetModel,
    X: np.ndarray,
    y: np.ndarray,
    epsilon: float = 0.1,
    alpha: float = 0.02,
    steps: int = 10,
    clip_min: float | None = None,
    clip_max: float | None = None,
) -> AdversarialAttackResult:
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=int)

    clean_pred = model.predict(X)
    clean_acc = float((clean_pred == y).mean())

    X_adv = pgd_perturb(model, X, y, epsilon, alpha, steps, clip_min, clip_max)
    adv_pred = model.predict(X_adv)
    adv_acc = float((adv_pred == y).mean())

    correct_before = clean_pred == y
    flipped = correct_before & (adv_pred != y)
    success_rate = float(flipped.sum() / max(correct_before.sum(), 1))

    return AdversarialAttackResult(
        attack="pgd",
        epsilon=epsilon,
        clean_accuracy=round(clean_acc, 4),
        adversarial_accuracy=round(adv_acc, 4),
        accuracy_drop=round(clean_acc - adv_acc, 4),
        success_rate=round(success_rate, 4),
        samples_evaluated=len(X),
        extra={"alpha": alpha, "steps": steps},
    )
