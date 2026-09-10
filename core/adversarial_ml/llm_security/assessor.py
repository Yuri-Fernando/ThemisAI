"""LLM security assessment — fachada que compõe os módulos de segurança de
LLM já existentes no Themis (`core/prompt_security` e `core/red_team_lab`)
numa única seção do relatório de segurança do modelo.

Não reimplementa detecção: chama o motor real de `prompt_security.scan` via
o harness real de `red_team_lab.run_red_team_suite`, e resume o resultado
por categoria de ataque (prompt injection, jailbreak, exfiltração de PII,
ofuscação/evasão).
"""
from __future__ import annotations

from collections import defaultdict

from core.red_team_lab import run_red_team_suite


def assess_llm_security() -> dict:
    """Roda a suíte de red-team real contra o motor de prompt security e
    devolve um dicionário pronto para entrar em `ModelSecurityReport.llm_security`."""
    report = run_red_team_suite()

    by_category: dict[str, list] = defaultdict(list)
    for r in report.results:
        by_category[r.category].append(r)

    per_category = {}
    for cat, results in by_category.items():
        detected = sum(1 for r in results if r.detected)
        per_category[cat] = {
            "total": len(results),
            "detected": detected,
            "detection_rate": round(detected / len(results), 4),
        }

    gaps = sorted(r.attack_id for r in report.results if not r.passed)

    return {
        "overall_detection_rate": report.detection_rate,
        "prompt_injection": per_category.get("prompt_injection", {}),
        "jailbreak": per_category.get("jailbreak", {}),
        "pii_exfiltration": per_category.get("pii_exfiltration", {}),
        "evasion_and_obfuscation": {
            k: v for k, v in per_category.items()
            if k.startswith("evasion") or k == "obfuscation"
        },
        "coverage_gaps": gaps,
        "summary": report.summary,
    }
