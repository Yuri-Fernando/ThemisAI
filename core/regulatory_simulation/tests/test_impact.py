"""Testes do Regulatory Simulation Sandbox — composição real de
regulatory_knowledge_graph + regulatory_sandbox (V2), sem mocks."""
from __future__ import annotations

import pytest

from core.regulatory_simulation.impact import simulate_regulatory_change
from shared.schemas import DataCategory, LegalBasis, RegulatoryChangeImpact, SandboxScenario


def test_simulate_human_review_change_improves_biometric_scenario():
    scenario = SandboxScenario(
        name="Biometria sem revisão",
        data_categories=[DataCategory.SENSITIVE],
        legal_basis=LegalBasis.NOT_DETERMINED,
        context={"data_subtype": "biometric", "automated_decision": True, "human_review": False},
    )
    result = simulate_regulatory_change(
        article_number="20",
        context_override={"human_review": True},
        test_scenarios=[scenario],
    )
    assert isinstance(result, RegulatoryChangeImpact)
    assert result.scenarios_evaluated == 1
    assert result.scenarios_with_score_change == 1
    assert result.comparisons[0].score_delta > 0  # forçar revisão humana melhora o score


def test_directly_affected_articles_come_from_real_graph():
    scenario = SandboxScenario(name="X", data_categories=[DataCategory.PERSONAL], legal_basis=LegalBasis.CONSENT)
    result = simulate_regulatory_change("38", {"human_review": True}, [scenario])
    # Art. 38 (RIPD) referencia Art. 11 e Art. 20 no corpus real -- ver
    # core/regulatory_knowledge_graph/tests/test_graph.py.
    assert "11º" in result.directly_affected_articles
    assert "20º" in result.directly_affected_articles


def test_no_op_override_yields_no_score_change():
    scenario = SandboxScenario(name="Neutro", data_categories=[DataCategory.PERSONAL], legal_basis=LegalBasis.CONSENT)
    # human_review já não é usado por nenhuma política aplicável a este cenário simples.
    result = simulate_regulatory_change("7", {"chave_inexistente_no_policy_engine": True}, [scenario])
    assert result.scenarios_with_score_change == 0


def test_multiple_scenarios_evaluated_independently():
    scenarios = [
        SandboxScenario(name="A", data_categories=[DataCategory.PERSONAL], legal_basis=LegalBasis.CONSENT),
        SandboxScenario(
            name="B", data_categories=[DataCategory.SENSITIVE], legal_basis=LegalBasis.NOT_DETERMINED,
            context={"data_subtype": "biometric", "automated_decision": True, "human_review": False},
        ),
    ]
    result = simulate_regulatory_change("20", {"human_review": True}, scenarios)
    assert result.scenarios_evaluated == 2
    assert len(result.comparisons) == 2


def test_empty_scenarios_raises():
    with pytest.raises(ValueError):
        simulate_regulatory_change("20", {"human_review": True}, [])


def test_unknown_article_yields_empty_affected_list():
    scenario = SandboxScenario(name="X", data_categories=[DataCategory.PERSONAL], legal_basis=LegalBasis.CONSENT)
    result = simulate_regulatory_change("999", {"human_review": True}, [scenario])
    assert result.directly_affected_articles == []


def test_summary_mentions_article_and_scenario_count():
    scenario = SandboxScenario(name="X", data_categories=[DataCategory.PERSONAL], legal_basis=LegalBasis.CONSENT)
    result = simulate_regulatory_change("20", {"human_review": True}, [scenario])
    assert "20" in result.summary
    assert "1 de 1" in result.summary or "1" in result.summary
