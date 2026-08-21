"""Red Team Lab — harness de ataques automatizados contra `core/prompt_security`
(V1), medindo a taxa de detecção real do motor contra um conjunto de payloads
adversariais reais (`payloads.py`), incluindo tentativas de evasão dedicada.

**Nada é simulado**: cada payload é executado de verdade contra
`prompt_security.scan()` (ou qualquer função `scan`-compatível injetada) — o
`detected` de cada `AttackResult` vem da resposta real do motor, não de uma
tabela hardcoded. `expected_detection` é o julgamento independente de
segurança de um red-teamer sobre se aquele payload DEVERIA ser sinalizado —
propositalmente não ajustado para bater com o resultado real, para que gaps
de cobertura apareçam no relatório em vez de serem escondidos.
"""
from __future__ import annotations

from typing import Callable

from core.prompt_security.scanner import scan as _default_scan
from core.red_team_lab.payloads import ATTACK_PAYLOADS
from shared.schemas import AttackResult, PromptSecurityResult, RedTeamReport


def run_red_team_suite(
    scan_fn: Callable[[str], PromptSecurityResult] | None = None,
    payloads: list[dict] | None = None,
) -> RedTeamReport:
    """Roda todos os payloads de ataque contra `scan_fn` (default:
    `prompt_security.scan`) e mede a taxa de detecção real.

    Args:
        scan_fn: função `str -> PromptSecurityResult` a ser atacada. Default
            usa o motor real de `core.prompt_security`. Parametrizável para
            permitir testar uma versão futura/alternativa do scanner sem
            duplicar o harness.
        payloads: lista de payloads (default: `ATTACK_PAYLOADS`).

    Returns:
        `RedTeamReport` com o resultado de cada ataque e a taxa de detecção
        agregada. `passed` em cada `AttackResult` é `detected ==
        expected_detection` — ou seja, "o motor se comportou como um
        red-teamer esperaria", não "o motor está seguro" (payloads de
        controle benignos que são incorretamente sinalizados também contam
        como `passed=False`, um falso positivo).
    """
    scan_fn = scan_fn or _default_scan
    payloads = payloads if payloads is not None else ATTACK_PAYLOADS

    results: list[AttackResult] = []
    for attack in payloads:
        scan_result = scan_fn(attack["payload"])
        detected = not scan_result.is_safe
        expected = bool(attack["expected_detection"])
        results.append(
            AttackResult(
                attack_id=attack["id"],
                category=attack["category"],
                payload=attack["payload"],
                detected=detected,
                expected_detection=expected,
                passed=(detected == expected),
            )
        )

    total = len(results)
    detected_count = sum(1 for r in results if r.detected)
    detection_rate = (detected_count / total) if total else 0.0
    passed_count = sum(1 for r in results if r.passed)

    failed = [r for r in results if not r.passed]
    if not failed:
        summary = (
            f"{total} ataque(s) executados contra o motor real de prompt_security: "
            f"comportamento esperado em 100% dos casos (taxa de detecção {detection_rate:.0%})."
        )
    else:
        failed_ids = ", ".join(r.attack_id for r in failed)
        summary = (
            f"{total} ataque(s) executados: {passed_count}/{total} com comportamento esperado "
            f"(taxa de detecção real {detection_rate:.0%}). Gaps encontrados: {failed_ids}."
        )

    return RedTeamReport(
        total_attacks=total,
        detected_count=detected_count,
        detection_rate=round(detection_rate, 4),
        results=results,
        summary=summary,
    )
