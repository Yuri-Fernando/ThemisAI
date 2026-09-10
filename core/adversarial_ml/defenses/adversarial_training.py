"""Adversarial training (Madry et al.) — treina o modelo incluindo, a cada
época, exemplos perturbados por PGD gerados contra o próprio modelo no
estado atual. Formaliza o problema min-max:

    min_θ  E[(x,y)]  max_{||δ||<=ε}  L(f_θ(x+δ), y)

O `max` interno é aproximado por PGD; o `min` externo é o passo de treino.
"""
from __future__ import annotations

import numpy as np

from core.adversarial_ml.attacks.pgd import pgd_perturb
from core.adversarial_ml.models import LogisticRegressionModel


def adversarially_train(
    X_train: np.ndarray,
    y_train: np.ndarray,
    n_classes: int,
    epsilon: float = 0.1,
    alpha: float = 0.02,
    pgd_steps: int = 5,
    epochs: int = 40,
    lr: float = 0.1,
    seed: int = 0,
) -> LogisticRegressionModel:
    X_train = np.asarray(X_train, dtype=float)
    y_train = np.asarray(y_train, dtype=int)

    model = LogisticRegressionModel(X_train.shape[1], n_classes, seed=seed)
    # warm start em dados limpos para o PGD ter um gradiente útil
    model.fit(X_train, y_train, lr=lr, epochs=50)

    for epoch in range(epochs):
        X_adv = pgd_perturb(
            model, X_train, y_train,
            epsilon=epsilon, alpha=alpha, steps=pgd_steps, seed=seed + epoch,
        )
        # mistura 50/50 limpo + adversarial e dá um passo de treino
        X_mix = np.vstack([X_train, X_adv])
        y_mix = np.concatenate([y_train, y_train])
        model.fit(X_mix, y_mix, lr=lr, epochs=1)

    return model
