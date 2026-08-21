"""Testes do Traceability — correlação real sobre uma AuditLogger isolada em
arquivo temporário."""
from __future__ import annotations

import pytest

from core.audit_logs.logger import AuditLogger
from core.traceability.tracer import trace_by_correlation_key, trace_events
from shared.schemas import AuditEventType, TraceLink


@pytest.fixture()
def logger(tmp_path):
    return AuditLogger(log_path=tmp_path / "audit_log.jsonl")


def _seed(logger: AuditLogger) -> None:
    logger.record_event(AuditEventType.PII_SCAN, actor="a", payload={"project_name": "Projeto A", "step": 1})
    logger.record_event(AuditEventType.POLICY_EVALUATION, actor="a", payload={"project_name": "Projeto A", "step": 2})
    logger.record_event(AuditEventType.PII_SCAN, actor="b", payload={"project_name": "Projeto B", "step": 1})
    logger.record_event(AuditEventType.RIPD_GENERATED, actor="a", payload={"project_name": "Projeto A", "step": 3})
    logger.record_event(AuditEventType.RAG_QUERY, actor="c", payload={"unrelated": True})


def test_trace_events_groups_matching_events(logger):
    _seed(logger)
    events = logger.read_events()
    trace = trace_events(events, correlation_key="project_name", correlation_value="Projeto A")
    assert isinstance(trace, TraceLink)
    assert len(trace.event_ids) == 3


def test_trace_events_raises_when_no_match(logger):
    _seed(logger)
    events = logger.read_events()
    with pytest.raises(ValueError):
        trace_events(events, correlation_key="project_name", correlation_value="Projeto Inexistente")


def test_trace_events_summary_mentions_count_and_types(logger):
    _seed(logger)
    events = logger.read_events()
    trace = trace_events(events, correlation_key="project_name", correlation_value="Projeto A")
    assert "3 evento(s)" in trace.summary
    assert "pii_scan" in trace.summary
    assert "ripd_generated" in trace.summary


def test_trace_by_correlation_key_builds_one_trace_per_value(logger):
    _seed(logger)
    traces = trace_by_correlation_key("project_name", logger=logger)
    assert len(traces) == 2  # "Projeto A" e "Projeto B"
    sizes = sorted(len(t.event_ids) for t in traces)
    assert sizes == [1, 3]


def test_trace_by_correlation_key_ignores_events_without_key(logger):
    _seed(logger)
    traces = trace_by_correlation_key("project_name", logger=logger)
    all_event_ids = {eid for t in traces for eid in t.event_ids}
    all_events = logger.read_events()
    unrelated_event = next(e for e in all_events if "unrelated" in e.payload)
    assert unrelated_event.event_id not in all_event_ids


def test_trace_by_correlation_key_empty_log_returns_empty(logger):
    assert trace_by_correlation_key("project_name", logger=logger) == []


def test_trace_events_ordered_chronologically(logger):
    _seed(logger)
    events = logger.read_events()
    trace = trace_events(events, correlation_key="project_name", correlation_value="Projeto A")
    matched_events = [e for e in events if e.event_id in trace.event_ids]
    timestamps = [e.timestamp for e in matched_events]
    assert timestamps == sorted(timestamps)
