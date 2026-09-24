"""Casos de referência compartilhados (`fixtures/cases/*.json`).

Os MESMOS arquivos são executados pela implementação TypeScript do Conecta AI
(`Direito/core`, aba Direito do SaaS) — é o contrato que mantém as duas
implementações do motor com o mesmo comportamento.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from core.legal_change_intelligence import analyze_legal_change

CASES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "cases"
CASES = sorted(CASES_DIR.glob("*.json"))


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_there_are_reference_cases():
    assert len(CASES) >= 9


@pytest.mark.parametrize("case_path", CASES, ids=[p.stem for p in CASES])
def test_reference_case(case_path: Path):
    case = _load(case_path)
    expected = case["expected"]
    result = analyze_legal_change(
        case["previous"],
        case["current"],
        metadata=case["metadata"],
        client_context=case["client_context"],
        analyzed_at=datetime(2026, 9, 23, tzinfo=timezone.utc),
    )

    changes = {c.unit_id: c.change_type.value for c in result.changes}
    assert changes == expected["changes"], result.summary

    for unit_id, signal_ids in expected.get("signals_include", {}).items():
        found = {s.signal_id for c in result.changes if c.unit_id == unit_id for s in c.signals}
        assert set(signal_ids) <= found, (unit_id, found)

    for unit_id, acts in expected.get("amended_by_include", {}).items():
        found = {a for c in result.changes if c.unit_id == unit_id for a in c.amended_by}
        assert set(acts) <= found, (unit_id, found)

    assert result.impact_level.value == expected["impact_level"]
    assert result.risk_level.value == expected["risk_level"]
    assert result.requires_human_review is expected["requires_human_review"]

    rules = {r.rule_id for r in result.rules_fired}
    assert set(expected.get("rules_include", [])) <= rules, rules
    assert not (set(expected.get("rules_exclude", [])) & rules), rules
    assert set(expected.get("topics_include", [])) <= set(result.affected_topics), result.affected_topics

    related = {r.client_id: r.strength for r in result.related_clients}
    assert related == expected["related_clients"]

    # Toda regra disparada (exceto R0) traz evidência — nada sem justificativa.
    assert all(r.evidence for r in result.rules_fired if r.rule_id != "R0_NO_CHANGE")


def test_vetoed_paragraph_is_flagged_in_real_lgpd_case():
    from core.legal_change_intelligence import parse_legal_text

    case = _load(CASES_DIR / "01_lgpd_art20_revisao_humana.json")
    units = {u.unit_id: u for u in parse_legal_text(case["current"])}
    assert units["art-20.par-3"].vetoed is True
    assert units["art-20.par-3"].text == ""
    # "Vigência" e a anotação saem do texto comparável do caput.
    assert units["art-20"].text.endswith("personalidade.")
    assert units["art-20"].amended_by == ["Lei 13.853/2019"]
