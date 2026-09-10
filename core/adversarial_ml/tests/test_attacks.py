"""Testes dos ataques — verificam que FGSM/PGD realmente derrubam a acurácia
de um modelo não defendido, que PGD >= FGSM em força, e que os ataques de
extração e poisoning produzem os efeitos esperados."""
from __future__ import annotations

import numpy as np

from core.adversarial_ml.attacks import (
    fgsm_attack,
    fgsm_perturb,
    label_flip_poisoning,
    model_extraction_attack,
    pgd_attack,
)
from core.adversarial_ml.models import BlackBoxModel


def test_fgsm_reduces_accuracy(trained_model, synthetic_dataset):
    ds = synthetic_dataset
    res = fgsm_attack(trained_model, ds["X_test"], ds["y_test"], epsilon=0.5)
    assert res.attack == "fgsm"
    assert res.adversarial_accuracy < res.clean_accuracy
    assert 0.0 <= res.success_rate <= 1.0


def test_pgd_at_least_as_strong_as_fgsm(trained_model, synthetic_dataset):
    ds = synthetic_dataset
    fg = fgsm_attack(trained_model, ds["X_test"], ds["y_test"], epsilon=0.3)
    pg = pgd_attack(trained_model, ds["X_test"], ds["y_test"], epsilon=0.3, alpha=0.05, steps=20)
    assert pg.adversarial_accuracy <= fg.adversarial_accuracy + 1e-6


def test_epsilon_zero_is_a_noop(trained_model, synthetic_dataset):
    ds = synthetic_dataset
    res = fgsm_attack(trained_model, ds["X_test"], ds["y_test"], epsilon=0.0)
    assert abs(res.clean_accuracy - res.adversarial_accuracy) < 1e-9


def test_fgsm_perturbation_is_bounded(trained_model, synthetic_dataset):
    ds = synthetic_dataset
    eps = 0.1
    X = ds["X_test"]
    X_adv = fgsm_perturb(trained_model, X, ds["y_test"], epsilon=eps)
    assert np.max(np.abs(X_adv - X)) <= eps + 1e-9


def test_blackbox_finite_difference_gradient_also_attacks(trained_model, synthetic_dataset):
    ds = synthetic_dataset
    bb = BlackBoxModel(trained_model.predict_proba)
    res = fgsm_attack(bb, ds["X_test"], ds["y_test"], epsilon=0.5)
    assert res.adversarial_accuracy < res.clean_accuracy


def test_model_extraction_recovers_behavior(trained_model, synthetic_dataset):
    ds = synthetic_dataset
    res = model_extraction_attack(
        trained_model, ds["X_train"], ds["X_test"], ds["y_test"], ds["n_classes"]
    )
    assert res.attack == "extraction"
    # surrogate treinado nas predições do alvo deve concordar bastante com o alvo
    assert res.extra["fidelity"] > 0.8


def test_label_flip_poisoning_degrades_clean_accuracy(synthetic_dataset):
    ds = synthetic_dataset
    res = label_flip_poisoning(
        ds["X_train"], ds["y_train"], ds["X_test"], ds["y_test"],
        ds["n_classes"], poison_rate=0.4,
    )
    assert res.attack == "poisoning"
    assert res.adversarial_accuracy <= res.clean_accuracy
