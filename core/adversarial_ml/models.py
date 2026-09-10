"""Modelos-alvo para os ataques adversariais.

O motor de Adversarial ML do Themis opera sobre uma interface mínima
(`predict_proba` + `gradient`), sem depender de nenhum framework de deep
learning no núcleo. Duas implementações são fornecidas:

- `LogisticRegressionModel`: modelo linear treinado por gradiente
  descendente em numpy puro. O gradiente da loss em relação à ENTRADA é
  analítico e exato — FGSM/PGD sobre ele são ataques reais, não
  aproximações.
- `BlackBoxModel`: wrapper sobre qualquer callable `X -> probas` (ex.: um
  modelo scikit-learn, um endpoint remoto). O gradiente em relação à
  entrada é estimado por diferenças finitas — também um ataque real, apenas
  mais caro em número de consultas (o mesmo custo que um atacante externo
  pagaria).

`nada é simulado`: as acurácias/robustez reportadas pelos módulos de
`attacks/` e `robustness/` vêm da avaliação real do modelo sobre os dados
perturbados.
"""
from __future__ import annotations

from typing import Callable, Protocol

import numpy as np


class TargetModel(Protocol):
    """Interface que os ataques esperam de um modelo-alvo."""

    def predict_proba(self, X: np.ndarray) -> np.ndarray:  # (n, n_classes)
        ...

    def predict(self, X: np.ndarray) -> np.ndarray:  # (n,)
        ...

    def gradient(self, X: np.ndarray, y: np.ndarray) -> np.ndarray:
        """∂ loss(f(X), y) / ∂ X — shape (n, n_features)."""
        ...


def _softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


class LogisticRegressionModel:
    """Regressão logística multinomial em numpy, com gradiente analítico
    em relação à entrada (usado por FGSM/PGD)."""

    def __init__(self, n_features: int, n_classes: int, seed: int = 0):
        rng = np.random.default_rng(seed)
        self.W = rng.normal(0, 0.01, size=(n_features, n_classes))
        self.b = np.zeros(n_classes)
        self.n_classes = n_classes

    def fit(self, X: np.ndarray, y: np.ndarray, lr: float = 0.1, epochs: int = 300) -> "LogisticRegressionModel":
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=int)
        Y = np.eye(self.n_classes)[y]
        n = len(X)
        for _ in range(epochs):
            probs = _softmax(X @ self.W + self.b)
            grad_logits = (probs - Y) / n
            self.W -= lr * (X.T @ grad_logits)
            self.b -= lr * grad_logits.sum(axis=0)
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        return _softmax(X @ self.W + self.b)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.predict_proba(X).argmax(axis=1)

    def gradient(self, X: np.ndarray, y: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=int)
        Y = np.eye(self.n_classes)[y]
        probs = self.predict_proba(X)
        # ∂CE/∂logits = (probs - Y);  ∂logits/∂X = W^T
        return (probs - Y) @ self.W.T


class BlackBoxModel:
    """Wrapper sobre um `predict_proba` arbitrário. O gradiente em relação à
    entrada é estimado por diferenças finitas centrais."""

    def __init__(self, proba_fn: Callable[[np.ndarray], np.ndarray], epsilon_fd: float = 1e-3):
        self._proba_fn = proba_fn
        self.epsilon_fd = epsilon_fd

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return np.asarray(self._proba_fn(np.asarray(X, dtype=float)), dtype=float)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.predict_proba(X).argmax(axis=1)

    def _ce_loss(self, X: np.ndarray, y: np.ndarray) -> np.ndarray:
        probs = np.clip(self.predict_proba(X), 1e-12, 1.0)
        return -np.log(probs[np.arange(len(X)), y])

    def gradient(self, X: np.ndarray, y: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=int)
        grad = np.zeros_like(X)
        eps = self.epsilon_fd
        for j in range(X.shape[1]):
            Xp, Xm = X.copy(), X.copy()
            Xp[:, j] += eps
            Xm[:, j] -= eps
            grad[:, j] = (self._ce_loss(Xp, y) - self._ce_loss(Xm, y)) / (2 * eps)
        return grad
