"""Testes do Constitutional AI — motor declarativo contra constitution.yaml real."""
from __future__ import annotations

import pytest

from core.constitutional_ai.engine import check_constitution
from shared.schemas import ConstitutionalCheckResult, RiskLevel


def test_compliant_context_no_violations():
    context = {
        "automated_decision": False,
        "in_production": False,
    }
    result = check_constitution(context)
    assert isinstance(result, ConstitutionalCheckResult)
    assert result.compliant is True
    assert result.violations == []


def test_transparency_violation_detected():
    context = {"automated_decision": True, "explainable": False}
    result = check_constitution(context)
    assert result.compliant is False
    assert any(v.principle_id == "CONST-01" for v in result.violations)


def test_fairness_violation_is_critical():
    context = {"fairness_audit_passed": False}
    result = check_constitution(context)
    violation = next(v for v in result.violations if v.principle_id == "CONST-02")
    assert violation.severity == RiskLevel.CRITICAL


def test_human_oversight_violation():
    context = {"automated_decision": True, "high_impact": True, "human_review_available": False}
    result = check_constitution(context)
    assert any(v.principle_id == "CONST-03" for v in result.violations)


def test_human_oversight_not_violated_when_review_available():
    context = {"automated_decision": True, "high_impact": True, "human_review_available": True}
    result = check_constitution(context)
    assert not any(v.principle_id == "CONST-03" for v in result.violations)


def test_multiple_violations_simultaneously():
    context = {
        "automated_decision": True,
        "explainable": False,
        "fairness_audit_passed": False,
        "in_production": True,
        "audit_logging_enabled": False,
    }
    result = check_constitution(context)
    violated_ids = {v.principle_id for v in result.violations}
    assert {"CONST-01", "CONST-02", "CONST-05"}.issubset(violated_ids)
    assert result.compliant is False


def test_empty_context_is_compliant():
    result = check_constitution({})
    assert result.compliant is True


def test_data_minimization_violation():
    context = {"data_category": "sensitive", "purpose_specified": False}
    result = check_constitution(context)
    assert any(v.principle_id == "CONST-04" for v in result.violations)


def test_summary_mentions_violation_count():
    context = {"in_production": True, "prompt_security_scanned": False}
    result = check_constitution(context)
    assert "1 violação" in result.summary or "violação(ões)" in result.summary


def test_custom_constitution_path(tmp_path):
    custom = tmp_path / "custom_constitution.yaml"
    custom.write_text(
        """
constitution:
  - id: "CUSTOM-01"
    principle: "Teste"
    description: "Princípio de teste."
    forbidden_when:
      context:
        flag: true
    severity: low
""",
        encoding="utf-8",
    )
    result = check_constitution({"flag": True}, constitution_path=custom)
    assert result.compliant is False
    assert result.violations[0].principle_id == "CUSTOM-01"
    assert result.violations[0].severity == RiskLevel.LOW
