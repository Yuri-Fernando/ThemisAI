"""Orquestrador do módulo Adversarial ML — roda a bateria completa (ataques
de evasão + extração + poisoning + defesa + LLM security) e devolve um
`ModelSecurityReport` consolidado, já renderizado como texto.

Este é o ponto de entrada consumido pelo Governance Copilot e pelo
"production robustness gate" do Argus.
"""
from __future__ import annotations

import numpy as np

from core.adversarial_ml.attacks.extraction import model_extraction_attack
from core.adversarial_ml.attacks.poisoning import label_flip_poisoning
from core.adversarial_ml.defenses.adversarial_training import adversarially_train
from core.adversarial_ml.llm_security.assessor import assess_llm_security
from core.adversarial_ml.models import TargetModel
from core.adversarial_ml.robustness.evaluator import evaluate_robustness
from core.adversarial_ml.robustness.metrics import classify_risk
from core.adversarial_ml.robustness.report import render_model_security_report
from shared.schemas import (
    DefenseEvaluation,
    ModelSecurityReport,
    RiskLevel,
)

_RISK_ORDER = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]


def _worst(*levels: RiskLevel) -> RiskLevel:
    return max(levels, key=_RISK_ORDER.index)


def _recommendations(report_risk: RiskLevel, improved: bool) -> list[str]:
    recs: list[str] = []
    if report_risk in (RiskLevel.HIGH, RiskLevel.CRITICAL):
        recs.append("adversarial training antes de promover o modelo para produção")
        recs.append("restrições de faixa/consistência nas features de entrada (input constraints)")
        recs.append("monitoramento contínuo de distribuição de entrada e de score em produção")
    if improved:
        recs.append("substituir o modelo base pelo modelo adversarialmente treinado avaliado neste relatório")
    if not recs:
        recs.append("manter monitoramento padrão; robustez dentro do aceitável para o caso de uso")
    return recs


def run_security_assessment(
    model: TargetModel,
    X_test: np.ndarray,
    y_test: np.ndarray,
    n_classes: int,
    *,
    model_name: str = "model",
    epsilon: float = 0.1,
    X_train: np.ndarray | None = None,
    y_train: np.ndarray | None = None,
    include_llm_security: bool = False,
    include_defense: bool = True,
) -> ModelSecurityReport:
    X_test = np.asarray(X_test, dtype=float)
    y_test = np.asarray(y_test, dtype=int)

    # --- evasão (FGSM + PGD) + curva de robustez
    attacks, robustness = evaluate_robustness(model, X_test, y_test, epsilon=epsilon)

    # --- extração e poisoning (quando há dados de treino disponíveis)
    if X_train is not None and y_train is not None:
        X_train = np.asarray(X_train, dtype=float)
        y_train = np.asarray(y_train, dtype=int)
        attacks.append(
            model_extraction_attack(model, X_train, X_test, y_test, n_classes)
        )
        attacks.append(
            label_flip_poisoning(X_train, y_train, X_test, y_test, n_classes)
        )

    # --- defesa: adversarial training (só quando há dados de treino)
    defenses: list[DefenseEvaluation] = []
    improved = False
    if include_defense and X_train is not None and y_train is not None:
        robust_model = adversarially_train(X_train, y_train, n_classes, epsilon=epsilon)
        _, robust_metrics = evaluate_robustness(robust_model, X_test, y_test, epsilon=epsilon)
        improved = robust_metrics.robust_accuracy > robustness.robust_accuracy
        defenses.append(
            DefenseEvaluation(
                defense="adversarial_training",
                robust_accuracy_before=robustness.robust_accuracy,
                robust_accuracy_after=robust_metrics.robust_accuracy,
                clean_accuracy_before=robustness.clean_accuracy,
                clean_accuracy_after=robust_metrics.clean_accuracy,
                summary=(
                    f"robust acc {robustness.robust_accuracy:.1%} -> "
                    f"{robust_metrics.robust_accuracy:.1%} "
                    f"(clean {robustness.clean_accuracy:.1%} -> {robust_metrics.clean_accuracy:.1%})"
                ),
            )
        )

    llm_security = assess_llm_security() if include_llm_security else {}

    overall = robustness.risk_level
    if llm_security:
        gap_count = len(llm_security.get("coverage_gaps", []))
        overall = _worst(overall, RiskLevel.MEDIUM if gap_count else RiskLevel.LOW)

    report = ModelSecurityReport(
        model_name=model_name,
        clean_accuracy=robustness.clean_accuracy,
        attacks=attacks,
        robustness=robustness,
        defenses=defenses,
        llm_security=llm_security,
        overall_risk=overall,
        recommendations=_recommendations(overall, improved),
    )
    report.rendered_report = render_model_security_report(report)
    return report
