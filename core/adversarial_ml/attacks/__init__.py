"""Ataques adversariais reais contra modelos de decisão automatizada."""
from __future__ import annotations

from core.adversarial_ml.attacks.extraction import model_extraction_attack
from core.adversarial_ml.attacks.fgsm import fgsm_attack, fgsm_perturb
from core.adversarial_ml.attacks.pgd import pgd_attack, pgd_perturb
from core.adversarial_ml.attacks.poisoning import label_flip_poisoning

__all__ = [
    "fgsm_attack",
    "fgsm_perturb",
    "pgd_attack",
    "pgd_perturb",
    "model_extraction_attack",
    "label_flip_poisoning",
]
