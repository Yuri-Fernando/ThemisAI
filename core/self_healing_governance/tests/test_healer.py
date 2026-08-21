"""Testes do Self-Healing Governance — abertura real de incidente via
incident_response.IncidentLog, isolado em arquivo temporário."""
from __future__ import annotations

import pytest

from core.blockchain_audit_layer.engine import create_checkpoint, verify_checkpoint_chain
from core.audit_logs.logger import AuditLogger
from core.incident_response.log import IncidentLog
from core.self_healing_governance.healer import check_and_heal
from shared.schemas import AuditEventType, IncidentStatus, RiskLevel


@pytest.fixture()
def incident_log(tmp_path):
    return IncidentLog(storage_path=tmp_path / "incidents.json")


def test_healthy_check_creates_no_incident(incident_log):
    actions = check_and_heal({"audit_chain_integrity": True}, incident_log=incident_log)
    assert actions[0].healthy is True
    assert actions[0].incident_id is None
    assert actions[0].suggested_steps == []
    assert incident_log.list_incidents() == []


def test_unhealthy_check_opens_real_incident(incident_log):
    actions = check_and_heal({"audit_chain_integrity": False}, incident_log=incident_log)
    action = actions[0]
    assert action.healthy is False
    assert action.incident_id is not None
    assert len(action.suggested_steps) > 0

    incidents = incident_log.list_incidents()
    assert len(incidents) == 1
    assert incidents[0].incident_id == action.incident_id
    assert incidents[0].status == IncidentStatus.OPEN
    assert incidents[0].severity == RiskLevel.CRITICAL


def test_unknown_check_uses_default_steps(incident_log):
    actions = check_and_heal({"check_nunca_visto": False}, incident_log=incident_log)
    assert actions[0].suggested_steps == ["Investigar manualmente — nenhum runbook declarado para este check."]


def test_multiple_checks_mixed_health(incident_log):
    actions = check_and_heal(
        {"audit_chain_integrity": True, "prompt_security_coverage": False},
        incident_log=incident_log,
    )
    by_name = {a.check_name: a for a in actions}
    assert by_name["audit_chain_integrity"].healthy is True
    assert by_name["prompt_security_coverage"].healthy is False
    assert len(incident_log.list_incidents()) == 1


def test_real_integration_with_blockchain_audit_layer(tmp_path, incident_log):
    # Cadeia real, íntegra -- check_and_heal não deve abrir incidente.
    audit_logger = AuditLogger(log_path=tmp_path / "audit_log.jsonl")
    checkpoint_path = tmp_path / "checkpoints.jsonl"
    audit_logger.record_event(AuditEventType.PII_SCAN, actor="test", payload={})
    create_checkpoint(logger=audit_logger, checkpoint_path=checkpoint_path)

    healthy_result = verify_checkpoint_chain(checkpoint_path=checkpoint_path)
    actions = check_and_heal({"checkpoint_chain_integrity": healthy_result}, incident_log=incident_log)
    assert actions[0].healthy is True
    assert incident_log.list_incidents() == []

    # Adultera o checkpoint e roda de novo -- agora deve abrir incidente real.
    import json

    lines = checkpoint_path.read_text(encoding="utf-8").splitlines()
    record = json.loads(lines[0])
    record["merkle_root"] = "0" * 64
    checkpoint_path.write_text(json.dumps(record) + "\n", encoding="utf-8")

    tampered_result = verify_checkpoint_chain(checkpoint_path=checkpoint_path)
    assert tampered_result is False
    actions2 = check_and_heal({"checkpoint_chain_integrity": tampered_result}, incident_log=incident_log)
    assert actions2[0].healthy is False
    assert len(incident_log.list_incidents()) == 1
