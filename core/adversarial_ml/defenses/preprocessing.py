"""Defesas por pré-processamento da entrada — aplicadas antes da inferência,
sem retreinar o modelo. Reduzem o espaço em que a perturbação adversarial
pode operar.

- `feature_squeezing`: quantiza cada feature em `levels` níveis (Xu et al.,
  2018). Perturbações menores que um nível são absorvidas.
- `clip_to_range`: recorta a entrada para a faixa observada em treino
  (perturbações que jogam a feature para fora da distribuição são contidas).
"""
from __future__ import annotations

import numpy as np


def feature_squeezing(X: np.ndarray, levels: int = 16, lo: float = 0.0, hi: float = 1.0) -> np.ndarray:
    X = np.asarray(X, dtype=float)
    X_norm = np.clip((X - lo) / (hi - lo + 1e-12), 0.0, 1.0)
    X_q = np.round(X_norm * (levels - 1)) / (levels - 1)
    return X_q * (hi - lo) + lo


def clip_to_range(X: np.ndarray, feature_min: np.ndarray, feature_max: np.ndarray) -> np.ndarray:
    return np.clip(np.asarray(X, dtype=float), feature_min, feature_max)


class PreprocessingDefense:
    """Envolve um modelo-alvo aplicando pré-processamento à entrada antes de
    delegar `predict`/`predict_proba`. Mantém a interface `TargetModel`."""

    def __init__(self, model, *, squeeze_levels: int | None = 16,
                 feature_min: np.ndarray | None = None, feature_max: np.ndarray | None = None):
        self.model = model
        self.squeeze_levels = squeeze_levels
        self.feature_min = feature_min
        self.feature_max = feature_max

    def _pre(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        if self.feature_min is not None and self.feature_max is not None:
            X = clip_to_range(X, self.feature_min, self.feature_max)
        if self.squeeze_levels:
            lo = float(self.feature_min.min()) if self.feature_min is not None else X.min()
            hi = float(self.feature_max.max()) if self.feature_max is not None else X.max()
            X = feature_squeezing(X, self.squeeze_levels, lo, hi)
        return X

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(self._pre(X))

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict(self._pre(X))

    def gradient(self, X: np.ndarray, y: np.ndarray) -> np.ndarray:
        # gradiente através do pré-processamento (aprox.: quantização tratada como identidade)
        return self.model.gradient(self._pre(X), y)
