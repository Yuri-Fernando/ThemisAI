"""Testes do Policy Engine — cobrem os 8 casos de política declarados em policies.yaml,
os 4 status possíveis de PolicyDecision, o caso de borda "nenhuma política aplicável" e
a robustez de carregamento (contexto ausente, caminho de políticas customizado).

Execução (a partir da raiz do repo):
    .venv/Scripts/python.exe -m pytest core/policy_engine/tests -v
"""
from __future__ import annotations

import pytest

from core.policy_engine.engine import evaluate
from shared.schemas import DataCategory, LegalBasis, PolicyDecision, PolicyDecisionStatus


def _by_id(decisions: list[PolicyDecision], policy_id: str) -> PolicyDecision:
    match = next((d for d in decisions if d.policy_id == policy_id), None)
    assert match is not None, f"esperava decisão de {policy_id}, obtive {[d.policy_id for d in decisions]}"
    return match


# ---------------------------------------------------------------------------
# POL-001 — dado de saúde
# ---------------------------------------------------------------------------

def test_health_data_with_consent_and_ripd_allows_with_mitigation():
    decisions = evaluate(
        data_categories=[DataCategory.SENSITIVE],
        legal_basis=LegalBasis.CONSENT,
        context={"data_subtype": "health", "ripd_conducted": True, "purpose_specified": True},
    )
    assert len(decisions) == 1
    decision = decisions[0]
    assert decision.policy_id == "POL-001"
    assert decision.status == PolicyDecisionStatus.ALLOW_WITH_MITIGATION
    assert decision.risk_level.value == "high"
    assert decision.mitigations  # deve trazer mitigações concretas


def test_health_data_without_consent_or_ripd_requires_human_review():
    decisions = evaluate(
        data_categories=[DataCategory.SENSITIVE],
        legal_basis=LegalBasis.CONSENT,
        context={"data_subtype": "health", "ripd_conducted": False},
    )
    assert len(decisions) == 1
    decision = decisions[0]
    assert decision.policy_id == "POL-001"
    assert decision.status == PolicyDecisionStatus.REQUIRES_HUMAN_REVIEW
    assert decision.risk_level.value == "critical"


# ---------------------------------------------------------------------------
# POL-002 — dado biométrico
# ---------------------------------------------------------------------------

def test_biometric_automated_decision_without_human_review_denies():
    decisions = evaluate(
        data_categories=[DataCategory.SENSITIVE],
        legal_basis=LegalBasis.LEGITIMATE_INTEREST,
        context={"data_subtype": "biometric", "automated_decision": True},
    )
    decision = _by_id(decisions, "POL-002")
    assert decision.status == PolicyDecisionStatus.DENY
    assert decision.risk_level.value == "critical"


def test_biometric_with_human_review_allows_with_mitigation():
    decisions = evaluate(
        data_categories=[DataCategory.SENSITIVE],
        legal_basis=LegalBasis.LEGITIMATE_INTEREST,
        context={"data_subtype": "biometric", "automated_decision": True, "human_review": True},
    )
    decision = _by_id(decisions, "POL-002")
    assert decision.status == PolicyDecisionStatus.ALLOW_WITH_MITIGATION


def test_biometric_without_automation_or_review_signal_requires_human_review():
    decisions = evaluate(
        data_categories=[DataCategory.SENSITIVE],
        legal_basis=LegalBasis.LEGITIMATE_INTEREST,
        context={"data_subtype": "biometric"},
    )
    decision = _by_id(decisions, "POL-002")
    assert decision.status == PolicyDecisionStatus.REQUIRES_HUMAN_REVIEW


# ---------------------------------------------------------------------------
# POL-003 — dado de menor de idade
# ---------------------------------------------------------------------------

def test_minor_without_guardian_consent_denies():
    decisions = evaluate(
        data_categories=[DataCategory.PERSONAL],
        legal_basis=LegalBasis.CONSENT,
        context={"involves_minor": True},
    )
    decision = _by_id(decisions, "POL-003")
    assert decision.status == PolicyDecisionStatus.DENY
    assert decision.risk_level.value == "critical"


def test_minor_with_guardian_consent_allows_with_mitigation():
    decisions = evaluate(
        data_categories=[DataCategory.PERSONAL],
        legal_basis=LegalBasis.CONSENT,
        context={"involves_minor": True, "guardian_consent": True},
    )
    decision = _by_id(decisions, "POL-003")
    assert decision.status == PolicyDecisionStatus.ALLOW_WITH_MITIGATION


# ---------------------------------------------------------------------------
# POL-004 — transferência internacional
# ---------------------------------------------------------------------------

def test_international_transfer_without_adequacy_requires_human_review():
    decisions = evaluate(
        data_categories=[DataCategory.PERSONAL],
        legal_basis=LegalBasis.CONTRACT_EXECUTION,
        context={"international_transfer": True},
    )
    decision = _by_id(decisions, "POL-004")
    assert decision.status == PolicyDecisionStatus.REQUIRES_HUMAN_REVIEW


def test_international_transfer_with_adequacy_safeguard_allows_with_mitigation():
    decisions = evaluate(
        data_categories=[DataCategory.PERSONAL],
        legal_basis=LegalBasis.CONTRACT_EXECUTION,
        context={"international_transfer": True, "adequacy_safeguard": True},
    )
    decision = _by_id(decisions, "POL-004")
    assert decision.status == PolicyDecisionStatus.ALLOW_WITH_MITIGATION
    assert decision.risk_level.value == "medium"


# ---------------------------------------------------------------------------
# POL-005 — dado anonimizado
# ---------------------------------------------------------------------------

def test_anonymized_only_data_is_allowed():
    decisions = evaluate(
        data_categories=[DataCategory.ANONYMIZED],
        legal_basis=LegalBasis.NOT_DETERMINED,
        context=None,
    )
    assert len(decisions) == 1
    decision = decisions[0]
    assert decision.policy_id == "POL-005"
    assert decision.status == PolicyDecisionStatus.ALLOW
    assert decision.risk_level.value == "low"


# ---------------------------------------------------------------------------
# POL-006 — decisão automatizada com efeito jurídico (Art. 20)
# ---------------------------------------------------------------------------

def test_automated_decision_with_explainability_and_review_allows_with_mitigation():
    decisions = evaluate(
        data_categories=[DataCategory.PERSONAL],
        legal_basis=LegalBasis.LEGITIMATE_INTEREST,
        context={
            "automated_decision": True,
            "legal_effect": True,
            "explainability_available": True,
            "human_review": True,
        },
    )
    decision = _by_id(decisions, "POL-006")
    assert decision.status == PolicyDecisionStatus.ALLOW_WITH_MITIGATION


def test_automated_decision_with_explainability_but_no_review_requires_human_review():
    decisions = evaluate(
        data_categories=[DataCategory.PERSONAL],
        legal_basis=LegalBasis.LEGITIMATE_INTEREST,
        context={
            "automated_decision": True,
            "legal_effect": True,
            "explainability_available": True,
        },
    )
    decision = _by_id(decisions, "POL-006")
    assert decision.status == PolicyDecisionStatus.REQUIRES_HUMAN_REVIEW


def test_automated_decision_without_explainability_denies():
    decisions = evaluate(
        data_categories=[DataCategory.PERSONAL],
        legal_basis=LegalBasis.LEGITIMATE_INTEREST,
        context={"automated_decision": True, "legal_effect": True},
    )
    decision = _by_id(decisions, "POL-006")
    assert decision.status == PolicyDecisionStatus.DENY
    assert decision.risk_level.value == "critical"


# ---------------------------------------------------------------------------
# POL-007 — finalidade não especificada
# ---------------------------------------------------------------------------

def test_purpose_not_specified_denies():
    decisions = evaluate(
        data_categories=[DataCategory.PERSONAL],
        legal_basis=LegalBasis.LEGITIMATE_INTEREST,
        context={"purpose_specified": False},
    )
    assert len(decisions) == 1
    decision = decisions[0]
    assert decision.policy_id == "POL-007"
    assert decision.status == PolicyDecisionStatus.DENY


# ---------------------------------------------------------------------------
# POL-008 — base legal não determinada
# ---------------------------------------------------------------------------

def test_legal_basis_not_determined_requires_human_review():
    decisions = evaluate(
        data_categories=[DataCategory.PERSONAL],
        legal_basis=LegalBasis.NOT_DETERMINED,
        context=None,
    )
    assert len(decisions) == 1
    decision = decisions[0]
    assert decision.policy_id == "POL-008"
    assert decision.status == PolicyDecisionStatus.REQUIRES_HUMAN_REVIEW


# ---------------------------------------------------------------------------
# POL-009 — linha de base (allow)
# ---------------------------------------------------------------------------

def test_baseline_personal_data_with_determined_basis_and_purpose_is_allowed():
    decisions = evaluate(
        data_categories=[DataCategory.PERSONAL],
        legal_basis=LegalBasis.CONTRACT_EXECUTION,
        context={"purpose_specified": True},
    )
    assert len(decisions) == 1
    decision = decisions[0]
    assert decision.policy_id == "POL-009"
    assert decision.status == PolicyDecisionStatus.ALLOW
    assert decision.risk_level.value == "low"


# ---------------------------------------------------------------------------
# Caso de borda — nenhuma política aplicável
# ---------------------------------------------------------------------------

def test_not_personal_data_with_no_special_context_yields_no_decisions():
    decisions = evaluate(
        data_categories=[DataCategory.NOT_PERSONAL],
        legal_basis=LegalBasis.LEGITIMATE_INTEREST,
        context=None,
    )
    assert decisions == []


def test_empty_data_categories_with_no_context_yields_no_decisions():
    decisions = evaluate(
        data_categories=[],
        legal_basis=LegalBasis.LEGAL_OBLIGATION,
        context=None,
    )
    assert decisions == []


# ---------------------------------------------------------------------------
# Cobertura explícita dos 4 status possíveis + múltiplas decisões simultâneas
# ---------------------------------------------------------------------------

def test_all_four_decision_statuses_are_reachable():
    observed_statuses = set()

    observed_statuses.add(
        evaluate(
            data_categories=[DataCategory.ANONYMIZED],
            legal_basis=LegalBasis.NOT_DETERMINED,
        )[0].status
    )
    observed_statuses.add(
        evaluate(
            data_categories=[DataCategory.SENSITIVE],
            legal_basis=LegalBasis.CONSENT,
            context={"data_subtype": "health", "ripd_conducted": True},
        )[0].status
    )
    observed_statuses.add(
        evaluate(
            data_categories=[DataCategory.PERSONAL],
            legal_basis=LegalBasis.LEGITIMATE_INTEREST,
            context={"purpose_specified": False},
        )[0].status
    )
    observed_statuses.add(
        evaluate(
            data_categories=[DataCategory.PERSONAL],
            legal_basis=LegalBasis.NOT_DETERMINED,
        )[0].status
    )

    assert observed_statuses == {
        PolicyDecisionStatus.ALLOW,
        PolicyDecisionStatus.ALLOW_WITH_MITIGATION,
        PolicyDecisionStatus.DENY,
        PolicyDecisionStatus.REQUIRES_HUMAN_REVIEW,
    }


def test_multiple_policies_can_apply_simultaneously():
    # Menor de idade + dado de saúde sem RIPD: aciona POL-001 (saúde) e POL-003 (menor).
    decisions = evaluate(
        data_categories=[DataCategory.SENSITIVE],
        legal_basis=LegalBasis.CONSENT,
        context={"data_subtype": "health", "ripd_conducted": False, "involves_minor": True},
    )
    policy_ids = {d.policy_id for d in decisions}
    assert {"POL-001", "POL-003"}.issubset(policy_ids)
    assert len(decisions) >= 2


# ---------------------------------------------------------------------------
# Contrato de retorno / robustez de carregamento
# ---------------------------------------------------------------------------

def test_evaluate_returns_policy_decision_instances():
    decisions = evaluate(
        data_categories=[DataCategory.PERSONAL],
        legal_basis=LegalBasis.CONTRACT_EXECUTION,
        context={"purpose_specified": True},
    )
    assert all(isinstance(d, PolicyDecision) for d in decisions)
    for d in decisions:
        assert d.policy_id
        assert d.rationale.strip()
        assert isinstance(d.mitigations, list)


def test_evaluate_accepts_missing_context_argument():
    # context é opcional (default None) — não deve levantar exceção.
    decisions = evaluate(
        data_categories=[DataCategory.PERSONAL],
        legal_basis=LegalBasis.CONTRACT_EXECUTION,
    )
    assert isinstance(decisions, list)


def test_evaluate_accepts_string_enum_values_directly():
    # DataCategory/LegalBasis são str Enum: comparação por valor deve funcionar
    # mesmo se strings cruas forem passadas (robustez de _as_value).
    decisions = evaluate(
        data_categories=["personal"],
        legal_basis="contract_execution",
        context={"purpose_specified": True},
    )
    assert len(decisions) == 1
    assert decisions[0].policy_id == "POL-009"


def test_evaluate_with_custom_policies_path(tmp_path):
    custom_policies = tmp_path / "custom_policies.yaml"
    custom_policies.write_text(
        """
policies:
  - id: TEST-CUSTOM-001
    description: "Política de teste isolada."
    trigger:
      data_categories_any: [personal]
    outcomes:
      - status: allow
        risk_level: low
        rationale: "Regra de teste customizada."
        mitigations: []
""",
        encoding="utf-8",
    )
    decisions = evaluate(
        data_categories=[DataCategory.PERSONAL],
        legal_basis=LegalBasis.CONSENT,
        policies_path=custom_policies,
    )
    assert len(decisions) == 1
    assert decisions[0].policy_id == "TEST-CUSTOM-001"
    assert decisions[0].status == PolicyDecisionStatus.ALLOW


def test_default_policies_file_has_at_least_eight_policies():
    from core.policy_engine.engine import _load_policies

    policies = _load_policies()
    assert len(policies) >= 8
    ids = [p["id"] for p in policies]
    assert len(ids) == len(set(ids)), "IDs de política devem ser únicos"
