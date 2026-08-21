"""Testes do Blockchain Audit Layer — checkpoints Merkle sobre uma hash-chain
real de `core.audit_logs`, isolados em arquivos temporários (nunca tocam o
log de produção nem os checkpoints reais do projeto)."""
from __future__ import annotations

import pytest

from core.audit_logs.logger import AuditLogger
from core.blockchain_audit_layer.engine import (
    create_checkpoint,
    get_proof,
    merkle_root,
    verify_checkpoint_chain,
)
from shared.schemas import AuditEventType


@pytest.fixture()
def audit_logger(tmp_path):
    return AuditLogger(log_path=tmp_path / "audit_log.jsonl")


@pytest.fixture()
def checkpoint_path(tmp_path):
    return tmp_path / "checkpoints.jsonl"


def _record_events(logger: AuditLogger, n: int) -> None:
    for i in range(n):
        logger.record_event(AuditEventType.PII_SCAN, actor="test", payload={"i": i})


def test_merkle_root_deterministic_and_order_sensitive():
    root1 = merkle_root(["a", "b", "c", "d"])
    root2 = merkle_root(["a", "b", "c", "d"])
    root3 = merkle_root(["d", "c", "b", "a"])
    assert root1 == root2
    assert root1 != root3


def test_merkle_root_handles_odd_number_of_leaves():
    root = merkle_root(["a", "b", "c"])
    assert isinstance(root, str) and len(root) == 64


def test_create_checkpoint_covers_all_events_first_time(audit_logger, checkpoint_path):
    _record_events(audit_logger, 5)
    checkpoint = create_checkpoint(logger=audit_logger, checkpoint_path=checkpoint_path)
    assert checkpoint.event_range_start == 0
    assert checkpoint.event_range_end == 5
    assert checkpoint.event_count == 5
    assert checkpoint.prev_checkpoint_hash == "0" * 64


def test_second_checkpoint_covers_only_new_events(audit_logger, checkpoint_path):
    _record_events(audit_logger, 3)
    cp1 = create_checkpoint(logger=audit_logger, checkpoint_path=checkpoint_path)
    _record_events(audit_logger, 2)
    cp2 = create_checkpoint(logger=audit_logger, checkpoint_path=checkpoint_path)

    assert cp2.event_range_start == 3
    assert cp2.event_range_end == 5
    assert cp2.prev_checkpoint_hash == cp1.checkpoint_hash


def test_create_checkpoint_raises_when_no_new_events(audit_logger, checkpoint_path):
    _record_events(audit_logger, 2)
    create_checkpoint(logger=audit_logger, checkpoint_path=checkpoint_path)
    with pytest.raises(ValueError):
        create_checkpoint(logger=audit_logger, checkpoint_path=checkpoint_path)


def test_verify_checkpoint_chain_valid(audit_logger, checkpoint_path):
    _record_events(audit_logger, 4)
    create_checkpoint(logger=audit_logger, checkpoint_path=checkpoint_path)
    _record_events(audit_logger, 3)
    create_checkpoint(logger=audit_logger, checkpoint_path=checkpoint_path)
    assert verify_checkpoint_chain(checkpoint_path=checkpoint_path) is True


def test_verify_checkpoint_chain_empty_is_valid(checkpoint_path):
    assert verify_checkpoint_chain(checkpoint_path=checkpoint_path) is True


def test_verify_checkpoint_chain_detects_tampering(audit_logger, checkpoint_path):
    _record_events(audit_logger, 4)
    create_checkpoint(logger=audit_logger, checkpoint_path=checkpoint_path)

    # Adultera o merkle_root gravado no checkpoint.
    lines = checkpoint_path.read_text(encoding="utf-8").splitlines()
    import json

    record = json.loads(lines[0])
    record["merkle_root"] = "0" * 64
    checkpoint_path.write_text(json.dumps(record) + "\n", encoding="utf-8")

    assert verify_checkpoint_chain(checkpoint_path=checkpoint_path) is False


def test_get_proof_valid_for_every_event_in_checkpoint(audit_logger, checkpoint_path):
    _record_events(audit_logger, 5)
    create_checkpoint(logger=audit_logger, checkpoint_path=checkpoint_path)

    events = audit_logger.read_events()
    for event in events:
        proof = get_proof(event.hash, logger=audit_logger, checkpoint_path=checkpoint_path)
        assert proof.valid is True
        assert proof.event_hash == event.hash


def test_get_proof_raises_for_unknown_event(audit_logger, checkpoint_path):
    _record_events(audit_logger, 2)
    create_checkpoint(logger=audit_logger, checkpoint_path=checkpoint_path)
    with pytest.raises(ValueError):
        get_proof("hash-inexistente", logger=audit_logger, checkpoint_path=checkpoint_path)


def test_get_proof_across_multiple_checkpoints(audit_logger, checkpoint_path):
    _record_events(audit_logger, 3)
    create_checkpoint(logger=audit_logger, checkpoint_path=checkpoint_path)
    _record_events(audit_logger, 4)
    create_checkpoint(logger=audit_logger, checkpoint_path=checkpoint_path)

    events = audit_logger.read_events()
    # Um evento do primeiro checkpoint e um do segundo.
    proof_first = get_proof(events[0].hash, logger=audit_logger, checkpoint_path=checkpoint_path)
    proof_last = get_proof(events[-1].hash, logger=audit_logger, checkpoint_path=checkpoint_path)
    assert proof_first.valid is True
    assert proof_last.valid is True
    assert proof_first.checkpoint_id != proof_last.checkpoint_id


def test_single_event_checkpoint_proof_is_trivial(audit_logger, checkpoint_path):
    _record_events(audit_logger, 1)
    create_checkpoint(logger=audit_logger, checkpoint_path=checkpoint_path)
    event = audit_logger.read_events()[0]
    proof = get_proof(event.hash, logger=audit_logger, checkpoint_path=checkpoint_path)
    assert proof.valid is True
    assert proof.merkle_root == event.hash  # árvore de 1 folha: raiz == a própria folha
