"""Testes do AI Incident Response — registro real em arquivo temporário +
runbook declarativo real."""
from __future__ import annotations

import pytest

from core.incident_response.log import IncidentLog, get_runbook
from shared.schemas import IncidentStatus, RiskLevel


@pytest.fixture()
def log(tmp_path):
    return IncidentLog(storage_path=tmp_path / "incidents.json")


def test_report_incident_creates_open_incident(log):
    incident = log.report_incident("Gap de detecção explorado", "RT-08 driblou o prompt_security em produção.", RiskLevel.HIGH)
    assert incident.status == IncidentStatus.OPEN
    assert incident.resolved_at is None


def test_report_incident_persists_across_instances(tmp_path):
    path = tmp_path / "incidents.json"
    IncidentLog(storage_path=path).report_incident("X", "Y", RiskLevel.LOW)
    incidents = IncidentLog(storage_path=path).list_incidents()
    assert len(incidents) == 1


def test_update_status_to_investigating(log):
    incident = log.report_incident("A", "B", RiskLevel.MEDIUM)
    updated = log.update_status(incident.incident_id, IncidentStatus.INVESTIGATING)
    assert updated.status == IncidentStatus.INVESTIGATING
    assert updated.resolved_at is None


def test_resolve_requires_notes(log):
    incident = log.report_incident("A", "B", RiskLevel.MEDIUM)
    with pytest.raises(ValueError):
        log.update_status(incident.incident_id, IncidentStatus.RESOLVED)


def test_resolve_sets_resolved_at_and_notes(log):
    incident = log.report_incident("A", "B", RiskLevel.MEDIUM)
    resolved = log.update_status(incident.incident_id, IncidentStatus.RESOLVED, resolution_notes="Corrigido no deploy X.")
    assert resolved.status == IncidentStatus.RESOLVED
    assert resolved.resolution_notes == "Corrigido no deploy X."
    assert resolved.resolved_at is not None


def test_cannot_reopen_resolved_incident(log):
    incident = log.report_incident("A", "B", RiskLevel.LOW)
    log.update_status(incident.incident_id, IncidentStatus.RESOLVED, resolution_notes="ok")
    with pytest.raises(ValueError):
        log.update_status(incident.incident_id, IncidentStatus.OPEN)


def test_list_incidents_filters_by_status(log):
    log.report_incident("A", "B", RiskLevel.LOW)
    inc2 = log.report_incident("C", "D", RiskLevel.HIGH)
    log.update_status(inc2.incident_id, IncidentStatus.RESOLVED, resolution_notes="ok")

    open_incidents = log.list_incidents(status=IncidentStatus.OPEN)
    resolved_incidents = log.list_incidents(status=IncidentStatus.RESOLVED)
    assert len(open_incidents) == 1
    assert len(resolved_incidents) == 1


def test_related_event_ids_stored(log):
    incident = log.report_incident("A", "B", RiskLevel.HIGH, related_event_ids=["ev1", "ev2"])
    assert incident.related_event_ids == ["ev1", "ev2"]


def test_get_unknown_incident_raises(log):
    with pytest.raises(ValueError):
        log.get("id-inexistente")


def test_get_runbook_critical_has_notification_step():
    steps = get_runbook(RiskLevel.CRITICAL)
    assert any("Art. 48" in s or "ANPD" in s for s in steps)


def test_get_runbook_all_severities_have_steps():
    for severity in [RiskLevel.CRITICAL, RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW]:
        steps = get_runbook(severity)
        assert len(steps) > 0
