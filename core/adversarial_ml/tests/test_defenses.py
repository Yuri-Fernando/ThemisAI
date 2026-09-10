"""Testes das defesas — adversarial training melhora a acurácia robusta,
pré-processamento não quebra a inferência limpa, e o detector estatístico
sinaliza mais entradas adversariais do que limpas."""
from __future__ import annotations

import numpy as np

from core.adversarial_ml.attacks.pgd import pgd_attack, pgd_perturb
from core.adversarial_ml.defenses import (
    AdversarialInputDetector,
    PreprocessingDefense,
    adversarially_train,
)
from core.adversarial_ml.robustness.evaluator import evaluate_robustness


def test_adversarial_training_improves_robust_accuracy(trained_model, synthetic_dataset):
    ds = synthetic_dataset
    _, base_metrics = evaluate_robustness(trained_model, ds["X_test"], ds["y_test"], epsilon=0.3)

    robust_model = adversarially_train(
        ds["X_train"], ds["y_train"], ds["n_classes"], epsilon=0.3, epochs=30
    )
    _, robust_metrics = evaluate_robustness(robust_model, ds["X_test"], ds["y_test"], epsilon=0.3)

    assert robust_metrics.robust_accuracy >= base_metrics.robust_accuracy


def test_preprocessing_defense_preserves_clean_predictions(trained_model, synthetic_dataset):
    ds = synthetic_dataset
    fmin = ds["X_train"].min(axis=0)
    fmax = ds["X_train"].max(axis=0)
    defended = PreprocessingDefense(trained_model, squeeze_levels=32, feature_min=fmin, feature_max=fmax)

    base_acc = (trained_model.predict(ds["X_test"]) == ds["y_test"]).mean()
    def_acc = (defended.predict(ds["X_test"]) == ds["y_test"]).mean()
    assert def_acc >= base_acc - 0.1  # não deve destruir a acurácia limpa


def test_detector_flags_adversarial_more_than_clean(trained_model, synthetic_dataset):
    ds = synthetic_dataset
    clean_probs = trained_model.predict_proba(ds["X_train"])
    detector = AdversarialInputDetector().fit(clean_probs)

    X_adv = pgd_perturb(trained_model, ds["X_test"], ds["y_test"], epsilon=0.4, alpha=0.08, steps=15)
    ev = detector.evaluate(
        trained_model.predict_proba(ds["X_test"]),
        trained_model.predict_proba(X_adv),
    )
    assert ev["detection_rate"] >= ev["false_positive_rate"]
