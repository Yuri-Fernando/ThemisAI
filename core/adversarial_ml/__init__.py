"""Adversarial ML / AI Security — módulo V4 do Themis AI.

Ataca modelos de decisão automatizada com ataques adversariais reais
(FGSM, PGD, model extraction, data poisoning), avalia defesas (adversarial
training, pré-processamento, detecção) e consolida tudo num
`ModelSecurityReport` — o "MODEL SECURITY REPORT" textual.

`nada é simulado`: as acurácias limpa/adversarial e as taxas de sucesso
reportadas vêm da avaliação real do modelo sobre os dados perturbados.

API pública:
    from core.adversarial_ml import run_security_assessment
    report = run_security_assessment(model, X_test, y_test, n_classes=2, X_train=X_tr, y_train=y_tr)
    print(report.rendered_report)
"""
from __future__ import annotations

from core.adversarial_ml.assessment import run_security_assessment
from core.adversarial_ml.models import BlackBoxModel, LogisticRegressionModel

__all__ = [
    "run_security_assessment",
    "LogisticRegressionModel",
    "BlackBoxModel",
]

__version__ = "0.1.0"
