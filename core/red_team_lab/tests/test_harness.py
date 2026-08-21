"""Testes do Red Team Lab — harness real contra `prompt_security.scan` (sem
mock no motor por padrão) + testes estruturais com `scan_fn` injetado."""
from __future__ import annotations

from core.red_team_lab.harness import run_red_team_suite
from core.red_team_lab.payloads import ATTACK_PAYLOADS
from shared.schemas import PromptSecurityFinding, PromptSecurityResult, RedTeamReport, RiskLevel


def test_run_default_suite_against_real_prompt_security():
    report = run_red_team_suite()
    assert isinstance(report, RedTeamReport)
    assert report.total_attacks == len(ATTACK_PAYLOADS)
    assert 0.0 <= report.detection_rate <= 1.0


def test_benign_controls_are_not_falsely_flagged():
    report = run_red_team_suite()
    benign_results = [r for r in report.results if r.category == "benign_control"]
    assert len(benign_results) == 2
    assert all(r.detected is False for r in benign_results)
    assert all(r.passed is True for r in benign_results)


def test_classic_jailbreak_is_detected():
    # RT-03 (DAN) e RT-04 (developer mode) -- ataques clássicos, sem ofuscação --
    # devem ser detectados pelo motor real.
    report = run_red_team_suite()
    classic = [r for r in report.results if r.attack_id in {"RT-03", "RT-04"}]
    assert all(r.detected is True for r in classic)


def test_known_coverage_gaps_are_surfaced_not_hidden():
    # Achado real de red-teaming: RT-08 (paráfrase sem gatilhos) e RT-09
    # (homoglifos) driblam o motor atual -- o harness precisa SURFACAR isso
    # como passed=False, não escondê-lo.
    report = run_red_team_suite()
    gaps = {r.attack_id: r for r in report.results if r.attack_id in {"RT-08", "RT-09"}}
    assert gaps["RT-08"].detected is False
    assert gaps["RT-08"].passed is False
    assert gaps["RT-09"].detected is False
    assert gaps["RT-09"].passed is False


def test_summary_lists_failed_attack_ids_when_gaps_exist():
    report = run_red_team_suite()
    failed = [r.attack_id for r in report.results if not r.passed]
    if failed:
        assert any(fid in report.summary for fid in failed)


def test_detection_rate_matches_detected_count():
    report = run_red_team_suite()
    assert report.detection_rate == round(report.detected_count / report.total_attacks, 4)


# --- Testes estruturais com scan_fn injetado (independentes do comportamento
# real do prompt_security, garantem que o harness em si está correto) ---

def _always_safe(prompt: str) -> PromptSecurityResult:
    return PromptSecurityResult(findings=[], is_safe=True, score=1.0)


def _always_unsafe(prompt: str) -> PromptSecurityResult:
    return PromptSecurityResult(
        findings=[PromptSecurityFinding(technique="prompt_injection", matched_pattern="x", severity=RiskLevel.HIGH)],
        is_safe=False,
        score=0.1,
    )


def test_injected_scan_fn_always_safe_yields_zero_detection_rate():
    report = run_red_team_suite(scan_fn=_always_safe)
    assert report.detected_count == 0
    assert report.detection_rate == 0.0


def test_injected_scan_fn_always_unsafe_yields_full_detection_rate():
    report = run_red_team_suite(scan_fn=_always_unsafe)
    assert report.detected_count == report.total_attacks
    assert report.detection_rate == 1.0
    # Payloads benignos (expected_detection=False) agora falham -- falso positivo real.
    benign = [r for r in report.results if r.category == "benign_control"]
    assert all(r.passed is False for r in benign)


def test_custom_payload_list():
    custom = [{"id": "X-01", "category": "test", "payload": "oi", "expected_detection": False}]
    report = run_red_team_suite(scan_fn=_always_safe, payloads=custom)
    assert report.total_attacks == 1
    assert report.results[0].attack_id == "X-01"


def test_empty_payload_list_returns_empty_report():
    report = run_red_team_suite(scan_fn=_always_safe, payloads=[])
    assert report.total_attacks == 0
    assert report.detection_rate == 0.0
    assert report.results == []
