"""Defesas contra ataques adversariais: treino adversarial, pré-processamento
de entrada e detecção estatística de entradas adversariais."""
from __future__ import annotations

from core.adversarial_ml.defenses.adversarial_training import adversarially_train
from core.adversarial_ml.defenses.detection import AdversarialInputDetector
from core.adversarial_ml.defenses.preprocessing import (
    PreprocessingDefense,
    clip_to_range,
    feature_squeezing,
)

__all__ = [
    "adversarially_train",
    "AdversarialInputDetector",
    "PreprocessingDefense",
    "feature_squeezing",
    "clip_to_range",
]
