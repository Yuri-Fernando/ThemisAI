"""Renderiza o `ModelSecurityReport` como texto — o MODEL SECURITY REPORT."""
from __future__ import annotations

from shared.schemas import ModelSecurityReport, RiskLevel

_RISK_LABEL = {
    RiskLevel.LOW: "LOW",
    RiskLevel.MEDIUM: "MEDIUM",
    RiskLevel.HIGH: "HIGH RISK",
    RiskLevel.CRITICAL: "CRITICAL",
}


def render_model_security_report(report: ModelSecurityReport) -> str:
    lines: list[str] = []
    lines.append("=" * 52)
    lines.append(f"  MODEL SECURITY REPORT  —  {report.model_name}")
    lines.append("=" * 52)
    lines.append("")
    lines.append(f"Clean Accuracy .............. {report.clean_accuracy:.1%}")

    for atk in report.attacks:
        if atk.attack in ("fgsm", "pgd"):
            label = f"{atk.attack.upper()} Accuracy (eps={atk.epsilon})"
            lines.append(f"{label:.<28} {atk.adversarial_accuracy:.1%}")
    lines.append("")

    rob = report.robustness
    lines.append(f"Robust Accuracy (PGD) ...... {rob.robust_accuracy:.1%}")
    if rob.min_perturbation_budget is not None:
        lines.append(f"Min Perturbation Budget .... eps={rob.min_perturbation_budget}")
    lines.append(f"Adversarial Robustness ..... {_RISK_LABEL[rob.risk_level]}")
    lines.append("")

    for atk in report.attacks:
        if atk.attack == "poisoning":
            lines.append(f"Data Poisoning Risk ........ drop {atk.accuracy_drop:.1%} @ {atk.extra.get('poison_rate')} contaminação")
        if atk.attack == "extraction":
            lines.append(f"Model Extraction Risk ...... fidelity {atk.extra.get('fidelity'):.1%} em {atk.extra.get('n_queries')} consultas")
    lines.append("")

    for dfn in report.defenses:
        lines.append(
            f"Defense [{dfn.defense}] ......... robust {dfn.robust_accuracy_before:.1%} -> {dfn.robust_accuracy_after:.1%}"
        )
    if report.defenses:
        lines.append("")

    if report.llm_security:
        lines.append("LLM Security:")
        for k, v in report.llm_security.items():
            lines.append(f"  - {k}: {v}")
        lines.append("")

    lines.append(f"Overall Risk ............... {_RISK_LABEL[report.overall_risk]}")
    lines.append("")
    lines.append("Recommended Mitigation:")
    for rec in report.recommendations:
        lines.append(f"  - {rec}")
    lines.append("=" * 52)
    return "\n".join(lines)
