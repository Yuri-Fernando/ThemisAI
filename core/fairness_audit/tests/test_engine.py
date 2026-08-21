"""Testes do Fairness Audit — motor estatístico determinístico."""
from __future__ import annotations

import pytest

from core.fairness_audit.engine import audit_fairness
from shared.schemas import FairnessAuditResult


def _records(n_a_favorable, n_a_total, n_b_favorable, n_b_total):
    records = []
    for i in range(n_a_total):
        records.append({"outcome": i < n_a_favorable, "group": "A"})
    for i in range(n_b_total):
        records.append({"outcome": i < n_b_favorable, "group": "B"})
    return records


def test_equal_rates_are_fair():
    records = _records(50, 100, 50, 100)  # 50% vs 50%
    result = audit_fairness(records, outcome_key="outcome", protected_attribute_key="group")
    assert isinstance(result, FairnessAuditResult)
    assert result.overall_fair is True
    assert all(m.passed for m in result.metrics)


def test_disparate_impact_below_threshold_flags_unfair():
    # A: 90% favorável, B: 40% favorável -> ratio = 0.44, bem abaixo de 0.8
    records = _records(90, 100, 40, 100)
    result = audit_fairness(records, outcome_key="outcome", protected_attribute_key="group")
    assert result.overall_fair is False
    di_metrics = [m for m in result.metrics if m.metric_name == "disparate_impact_ratio"]
    assert len(di_metrics) == 1
    assert di_metrics[0].passed is False
    assert di_metrics[0].value == pytest.approx(40 / 90, abs=0.01)


def test_reference_group_is_highest_rate():
    records = _records(90, 100, 40, 100)
    result = audit_fairness(records, outcome_key="outcome", protected_attribute_key="group")
    assert result.reference_group == "A"
    assert result.selection_rates["A"] == pytest.approx(0.9)
    assert result.selection_rates["B"] == pytest.approx(0.4)


def test_three_groups_all_compared_to_reference():
    records = (
        [{"outcome": i < 80, "group": "A"} for i in range(100)]
        + [{"outcome": i < 78, "group": "B"} for i in range(100)]
        + [{"outcome": i < 20, "group": "C"} for i in range(100)]
    )
    result = audit_fairness(records, outcome_key="outcome", protected_attribute_key="group")
    assert result.reference_group == "A"
    metric_groups = {m.group for m in result.metrics}
    assert metric_groups == {"B", "C"}
    assert result.overall_fair is False  # C está longe de A


def test_single_group_is_vacuously_fair():
    records = [{"outcome": True, "group": "A"}, {"outcome": False, "group": "A"}]
    result = audit_fairness(records, outcome_key="outcome", protected_attribute_key="group")
    assert result.overall_fair is True
    assert result.metrics == []


def test_custom_favorable_outcome_and_threshold():
    records = [
        {"decision": "approved", "gender": "F"},
        {"decision": "denied", "gender": "F"},
        {"decision": "approved", "gender": "M"},
        {"decision": "approved", "gender": "M"},
    ]
    result = audit_fairness(
        records,
        outcome_key="decision",
        protected_attribute_key="gender",
        favorable_outcome="approved",
        threshold=0.9,
    )
    assert result.selection_rates["F"] == pytest.approx(0.5)
    assert result.selection_rates["M"] == pytest.approx(1.0)
    # ratio 0.5 < 0.9 -> falha
    assert result.overall_fair is False


def test_empty_records_raises():
    with pytest.raises(ValueError):
        audit_fairness([], outcome_key="outcome", protected_attribute_key="group")


def test_missing_protected_attribute_key_raises():
    with pytest.raises(ValueError):
        audit_fairness([{"outcome": True}], outcome_key="outcome", protected_attribute_key="group")


def test_summary_is_portuguese_and_mentions_groups():
    records = _records(50, 100, 50, 100)
    result = audit_fairness(records, outcome_key="outcome", protected_attribute_key="group")
    assert "Auditoria de equidade" in result.summary
    assert "group" in result.summary


def test_zero_favorable_in_reference_group_handled():
    # Todos os grupos com taxa 0 -> reference_rate = 0, evita divisão por zero.
    records = [{"outcome": False, "group": "A"}, {"outcome": False, "group": "B"}]
    result = audit_fairness(records, outcome_key="outcome", protected_attribute_key="group")
    # ratio tratado como 1.0 (ambos zero) -> justo
    assert result.overall_fair is True
