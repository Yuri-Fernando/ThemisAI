"""Detecção de entradas adversariais — classificador estatístico simples que
sinaliza amostras cuja distribuição de probabilidade de saída é atípica.

Heurística (real, sem ML adicional): exemplos adversariais gerados por
FGSM/PGD tendem a produzir distribuições de saída mais "achatadas" (entropia
alta) ou a cair muito perto da fronteira de decisão (margem baixa) em
comparação com a distribuição observada em dados limpos. O detector calibra
limiares de entropia/margem num conjunto limpo e sinaliza o que escapa.
"""
from __future__ import annotations

import numpy as np


def _entropy(probs: np.ndarray) -> np.ndarray:
    p = np.clip(probs, 1e-12, 1.0)
    return -(p * np.log(p)).sum(axis=1)


def _margin(probs: np.ndarray) -> np.ndarray:
    sorted_p = np.sort(probs, axis=1)
    return sorted_p[:, -1] - sorted_p[:, -2]


class AdversarialInputDetector:
    def __init__(self, entropy_q: float = 0.95, margin_q: float = 0.05):
        self.entropy_q = entropy_q
        self.margin_q = margin_q
        self.entropy_threshold_: float | None = None
        self.margin_threshold_: float | None = None

    def fit(self, clean_probs: np.ndarray) -> "AdversarialInputDetector":
        ent = _entropy(clean_probs)
        mar = _margin(clean_probs)
        self.entropy_threshold_ = float(np.quantile(ent, self.entropy_q))
        self.margin_threshold_ = float(np.quantile(mar, self.margin_q))
        return self

    def predict(self, probs: np.ndarray) -> np.ndarray:
        """1 = sinalizado como possivelmente adversarial, 0 = normal."""
        if self.entropy_threshold_ is None:
            raise RuntimeError("chame .fit() com probabilidades de dados limpos primeiro")
        ent = _entropy(probs)
        mar = _margin(probs)
        return ((ent > self.entropy_threshold_) | (mar < self.margin_threshold_)).astype(int)

    def evaluate(self, clean_probs: np.ndarray, adv_probs: np.ndarray) -> dict:
        flags_clean = self.predict(clean_probs)
        flags_adv = self.predict(adv_probs)
        return {
            "false_positive_rate": round(float(flags_clean.mean()), 4),
            "detection_rate": round(float(flags_adv.mean()), 4),
        }
