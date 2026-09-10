"""Data poisoning — contamina o conjunto de treino (label flipping) e mede a
degradação de acurácia do modelo retreinado sobre dados limpos.

É o ataque de poisoning mais simples e mais estudado: inverter o rótulo de
uma fração `poison_rate` das amostras de treino. O relatório mede quanto de
acurácia limpa se perde por ponto percentual de contaminação.
"""
from __future__ import annotations

import numpy as np

from core.adversarial_ml.models import LogisticRegressionModel
from shared.schemas import AdversarialAttackResult


def label_flip_poisoning(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    n_classes: int,
    poison_rate: float = 0.2,
    seed: int = 0,
) -> AdversarialAttackResult:
    X_train = np.asarray(X_train, dtype=float)
    y_train = np.asarray(y_train, dtype=int)
    X_test = np.asarray(X_test, dtype=float)
    y_test = np.asarray(y_test, dtype=int)
    rng = np.random.default_rng(seed)

    # baseline: modelo treinado em dados limpos
    clean_model = LogisticRegressionModel(X_train.shape[1], n_classes, seed=seed)
    clean_model.fit(X_train, y_train)
    clean_acc = float((clean_model.predict(X_test) == y_test).mean())

    # poisoning: inverte rótulos de poison_rate das amostras
    y_poisoned = y_train.copy()
    n_poison = int(len(y_train) * poison_rate)
    idx = rng.choice(len(y_train), size=n_poison, replace=False)
    y_poisoned[idx] = (y_poisoned[idx] + rng.integers(1, n_classes, size=n_poison)) % n_classes

    poisoned_model = LogisticRegressionModel(X_train.shape[1], n_classes, seed=seed)
    poisoned_model.fit(X_train, y_poisoned)
    poisoned_acc = float((poisoned_model.predict(X_test) == y_test).mean())

    return AdversarialAttackResult(
        attack="poisoning",
        clean_accuracy=round(clean_acc, 4),
        adversarial_accuracy=round(poisoned_acc, 4),
        accuracy_drop=round(clean_acc - poisoned_acc, 4),
        success_rate=round(max(clean_acc - poisoned_acc, 0.0) / max(poison_rate, 1e-9), 4),
        samples_evaluated=len(X_test),
        extra={"poison_rate": poison_rate, "n_poisoned": n_poison},
    )
