"""Fixtures compartilhadas: um dataset sintético 2D linearmente separável (com
ruído) e um modelo logístico treinado nele. Determinístico (seed fixa)."""
from __future__ import annotations

import numpy as np
import pytest

from core.adversarial_ml.models import LogisticRegressionModel


@pytest.fixture(scope="session")
def synthetic_dataset():
    rng = np.random.default_rng(42)
    n = 400
    X0 = rng.normal(loc=[-1.0, -1.0], scale=0.6, size=(n // 2, 2))
    X1 = rng.normal(loc=[1.0, 1.0], scale=0.6, size=(n // 2, 2))
    X = np.vstack([X0, X1])
    y = np.array([0] * (n // 2) + [1] * (n // 2))
    perm = rng.permutation(n)
    X, y = X[perm], y[perm]
    split = int(0.7 * n)
    return {
        "X_train": X[:split], "y_train": y[:split],
        "X_test": X[split:], "y_test": y[split:],
        "n_classes": 2,
    }


@pytest.fixture(scope="session")
def trained_model(synthetic_dataset):
    ds = synthetic_dataset
    model = LogisticRegressionModel(2, ds["n_classes"], seed=0)
    model.fit(ds["X_train"], ds["y_train"], lr=0.2, epochs=400)
    return model
