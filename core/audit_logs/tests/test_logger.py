"""Testes do hash-chain de audit_logs."""
from __future__ import annotations

import json

import pytest

from core.audit_logs.logger import AuditLogger, GENESIS_HASH
from shared.schemas import AuditEventType


def test_record_single_event_and_verify_chain(tmp_path):
    log_path = tmp_path / "audit_log.jsonl"
    logger = AuditLogger(log_path=log_path)

    event = logger.record_event(
        AuditEventType.PII_SCAN,
        actor="pii_detection_module",
        payload={"findings_count": 2, "has_sensitive_data": True},
    )

    assert event.prev_hash == GENESIS_HASH
    assert len(event.hash) == 64
    assert event.event_type == AuditEventType.PII_SCAN
    assert event.actor == "pii_detection_module"

    assert log_path.exists()
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1

    assert logger.verify_chain() is True


def test_record_multiple_events_and_verify_chain(tmp_path):
    log_path = tmp_path / "audit_log.jsonl"
    logger = AuditLogger(log_path=log_path)

    e1 = logger.record_event(
        AuditEventType.PII_SCAN, actor="pii_detection", payload={"n": 1}
    )
    e2 = logger.record_event(
        AuditEventType.POLICY_EVALUATION,
        actor="policy_engine",
        payload={"decision": "allow"},
    )
    e3 = logger.record_event(
        AuditEventType.TRUST_SCORE_COMPUTED,
        actor="trust_score",
        payload={"score": 87.5},
    )

    # Cadeia encadeada corretamente.
    assert e1.prev_hash == GENESIS_HASH
    assert e2.prev_hash == e1.hash
    assert e3.prev_hash == e2.hash

    events = logger.read_events()
    assert len(events) == 3
    assert [e.event_id for e in events] == [e1.event_id, e2.event_id, e3.event_id]

    assert logger.verify_chain() is True


def test_tampered_middle_event_breaks_chain(tmp_path):
    log_path = tmp_path / "audit_log.jsonl"
    logger = AuditLogger(log_path=log_path)

    logger.record_event(AuditEventType.PII_SCAN, actor="a", payload={"n": 1})
    logger.record_event(
        AuditEventType.POLICY_EVALUATION, actor="b", payload={"decision": "allow"}
    )
    logger.record_event(
        AuditEventType.TRUST_SCORE_COMPUTED, actor="c", payload={"score": 50}
    )

    assert logger.verify_chain() is True

    # Adultera o payload do evento do meio (linha 2), sem recalcular hashes.
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3

    record = json.loads(lines[1])
    record["payload"] = {"decision": "deny"}  # payload alterado maliciosamente
    lines[1] = json.dumps(record)

    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    assert logger.verify_chain() is False


def test_tampered_hash_also_breaks_chain(tmp_path):
    log_path = tmp_path / "audit_log.jsonl"
    logger = AuditLogger(log_path=log_path)

    logger.record_event(AuditEventType.PII_SCAN, actor="a", payload={"n": 1})
    logger.record_event(
        AuditEventType.POLICY_EVALUATION, actor="b", payload={"decision": "allow"}
    )

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    record = json.loads(lines[0])
    record["hash"] = "f" * 64  # hash forjado
    lines[0] = json.dumps(record)
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    assert logger.verify_chain() is False


def test_empty_or_missing_file_does_not_crash(tmp_path):
    # Arquivo inexistente.
    missing_path = tmp_path / "does_not_exist.jsonl"
    logger = AuditLogger(log_path=missing_path)
    assert logger.verify_chain() is True
    assert logger.read_events() == []

    # Arquivo existente mas vazio.
    empty_path = tmp_path / "empty.jsonl"
    empty_path.write_text("", encoding="utf-8")
    logger_empty = AuditLogger(log_path=empty_path)
    assert logger_empty.verify_chain() is True
    assert logger_empty.read_events() == []


def test_first_event_uses_genesis_hash(tmp_path):
    log_path = tmp_path / "audit_log.jsonl"
    logger = AuditLogger(log_path=log_path)
    event = logger.record_event(
        AuditEventType.RAG_QUERY, actor="rag_module", payload={"query": "lgpd art 5"}
    )
    assert event.prev_hash == GENESIS_HASH
    assert GENESIS_HASH == "0" * 64
