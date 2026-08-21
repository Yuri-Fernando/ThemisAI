"""Testes do Meta-Governance Layer — inclusive integração real com
self_healing_governance (V2) para construir node_health de verdade."""
from __future__ import annotations

import pytest

from core.meta_governance.audit import audit_federation_health
from shared.schemas import MetaGovernanceReport


def test_all_nodes_fully_compliant():
    node_health = {"A": {"c1": True, "c2": True}, "B": {"c1": True}}
    result = audit_federation_health(node_health)
    assert isinstance(result, MetaGovernanceReport)
    assert result.non_compliant_nodes == []
    assert result.federation_compliance_rate == 1.0


def test_one_node_non_compliant():
    node_health = {"A": {"c1": True, "c2": True}, "B": {"c1": True, "c2": False}}
    result = audit_federation_health(node_health)
    assert result.non_compliant_nodes == ["B"]
    b_report = next(n for n in result.per_node if n.node_id == "B")
    assert b_report.compliance_rate == 0.5
    assert b_report.compliant is False


def test_custom_threshold_allows_partial_compliance():
    node_health = {"A": {"c1": True, "c2": False, "c3": True}}  # 2/3 = 66,7%
    strict = audit_federation_health(node_health, compliance_threshold=1.0)
    lenient = audit_federation_health(node_health, compliance_threshold=0.5)
    assert strict.non_compliant_nodes == ["A"]
    assert lenient.non_compliant_nodes == []


def test_federation_rate_is_weighted_by_checks_not_nodes():
    node_health = {
        "grande": {f"c{i}": True for i in range(9)} | {"c9": False},  # 9/10
        "pequeno": {"c1": False},  # 0/1
    }
    result = audit_federation_health(node_health)
    # Total: 9 saudáveis de 11 checks = 0.818..., não a média simples (0.45+0)/2
    assert result.federation_compliance_rate == pytest.approx(9 / 11, abs=0.001)


def test_empty_node_health_raises():
    with pytest.raises(ValueError):
        audit_federation_health({})


def test_node_without_checks_raises():
    with pytest.raises(ValueError):
        audit_federation_health({"A": {}})


def test_summary_lists_non_compliant_nodes():
    node_health = {"A": {"c1": False}}
    result = audit_federation_health(node_health)
    assert "A" in result.summary


def test_real_integration_with_self_healing_governance(tmp_path):
    from core.incident_response.log import IncidentLog
    from core.self_healing_governance.healer import check_and_heal

    incident_log = IncidentLog(storage_path=tmp_path / "incidents.json")
    actions_node_a = check_and_heal({"audit_chain_integrity": True, "prompt_security_coverage": True}, incident_log=incident_log)
    actions_node_b = check_and_heal({"audit_chain_integrity": False}, incident_log=incident_log)

    node_health = {
        "node_a": {a.check_name: a.healthy for a in actions_node_a},
        "node_b": {a.check_name: a.healthy for a in actions_node_b},
    }
    result = audit_federation_health(node_health)
    assert "node_a" not in result.non_compliant_nodes
    assert "node_b" in result.non_compliant_nodes
