"""Testes do Regulatory Sandbox — composição real de policy_engine + trust_score,
verificando explicitamente ausência de efeitos colaterais em audit_logs."""
from __future__ import annotations

from core.audit_logs.logger import default_logger
from core.regulatory_sandbox.sandbox import compare_scenarios, simulate
from shared.schemas import DataCategory, LegalBasis, RiskLevel, SandboxComparison, SandboxResult, SandboxScenario


def test_simulate_low_risk_scenario():
    scenario = SandboxScenario(
        name="Baixo risco",
        data_categories=[DataCategory.PERSONAL],
        legal_basis=LegalBasis.LEGITIMATE_INTEREST,
    )
    result = simulate(scenario)
    assert isinstance(result, SandboxResult)
    assert result.scenario_name == "Baixo risco"
    assert result.trust_score.risk_level == RiskLevel.LOW


def test_simulate_high_risk_biometric_denies():
    scenario = SandboxScenario(
        name="Biometria sem revisão",
        data_categories=[DataCategory.SENSITIVE],
        legal_basis=LegalBasis.NOT_DETERMINED,
        context={"data_subtype": "biometric", "automated_decision": True, "human_review": False},
    )
    result = simulate(scenario)
    assert any(d.status.value == "deny" for d in result.policy_decisions)
    assert result.trust_score.risk_level == RiskLevel.CRITICAL


def test_simulate_does_not_write_to_audit_log():
    logger = default_logger()
    before = len(logger.read_events())

    simulate(SandboxScenario(name="X", data_categories=[DataCategory.PERSONAL], legal_basis=LegalBasis.CONSENT))

    after = len(logger.read_events())
    assert after == before  # nenhum efeito colateral -- é isso que distingue o sandbox do ripd_engine


def test_compare_scenarios_shows_score_delta():
    scenario_a = SandboxScenario(
        name="Base legal não determinada",
        data_categories=[DataCategory.SENSITIVE],
        legal_basis=LegalBasis.NOT_DETERMINED,
        context={"data_subtype": "biometric", "automated_decision": True, "human_review": False},
    )
    scenario_b = SandboxScenario(
        name="Com revisão humana habilitada",
        data_categories=[DataCategory.SENSITIVE],
        legal_basis=LegalBasis.NOT_DETERMINED,
        context={"data_subtype": "biometric", "automated_decision": True, "human_review": True},
    )
    comparison = compare_scenarios(scenario_a, scenario_b)
    assert isinstance(comparison, SandboxComparison)
    # Habilitar revisão humana deveria melhorar (ou ao menos não piorar) o score.
    assert comparison.score_delta >= 0


def test_compare_scenarios_lists_added_and_removed_decisions():
    scenario_a = SandboxScenario(name="A", data_categories=[DataCategory.PERSONAL], legal_basis=LegalBasis.LEGITIMATE_INTEREST)
    scenario_b = SandboxScenario(
        name="B",
        data_categories=[DataCategory.SENSITIVE],
        legal_basis=LegalBasis.NOT_DETERMINED,
        context={"data_subtype": "biometric", "automated_decision": True, "human_review": False},
    )
    comparison = compare_scenarios(scenario_a, scenario_b)
    assert len(comparison.decisions_added) > 0 or len(comparison.decisions_removed) > 0


def test_compare_scenarios_summary_mentions_names():
    scenario_a = SandboxScenario(name="Cenário Alfa", data_categories=[DataCategory.PERSONAL], legal_basis=LegalBasis.CONSENT)
    scenario_b = SandboxScenario(name="Cenário Beta", data_categories=[DataCategory.PERSONAL], legal_basis=LegalBasis.CONSENT)
    comparison = compare_scenarios(scenario_a, scenario_b)
    assert "Cenário Alfa" in comparison.summary
    assert "Cenário Beta" in comparison.summary


def test_identical_scenarios_have_zero_delta():
    scenario = SandboxScenario(name="Igual", data_categories=[DataCategory.PERSONAL], legal_basis=LegalBasis.CONSENT)
    comparison = compare_scenarios(scenario, scenario.model_copy())
    assert comparison.score_delta == 0.0
    assert comparison.decisions_added == []
    assert comparison.decisions_removed == []
