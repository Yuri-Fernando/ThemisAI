"""Testes do Human Oversight — fila real persistida em arquivo temporário."""
from __future__ import annotations

import pytest

from core.human_oversight.queue import OversightQueue
from shared.schemas import OversightItemStatus, RiskLevel


@pytest.fixture()
def queue(tmp_path):
    return OversightQueue(storage_path=tmp_path / "oversight_queue.json")


def test_enqueue_creates_pending_item(queue):
    item = queue.enqueue(subject="Projeto X", reason="Dado de saúde sem consentimento", risk_level=RiskLevel.HIGH)
    assert item.status == OversightItemStatus.PENDING
    assert item.reviewer is None
    assert item.decided_at is None


def test_enqueue_persists_across_instances(tmp_path):
    path = tmp_path / "queue.json"
    OversightQueue(storage_path=path).enqueue("Projeto Y", "motivo", RiskLevel.MEDIUM)
    # Nova instância, mesmo arquivo -- prova que é persistência real, não em memória.
    items = OversightQueue(storage_path=path).list_items()
    assert len(items) == 1
    assert items[0].subject == "Projeto Y"


def test_list_items_filters_by_status(queue):
    item1 = queue.enqueue("A", "motivo A", RiskLevel.LOW)
    queue.enqueue("B", "motivo B", RiskLevel.HIGH)
    queue.decide(item1.item_id, approve=True, reviewer="ana@empresa.com")

    pending = queue.list_items(status=OversightItemStatus.PENDING)
    approved = queue.list_items(status=OversightItemStatus.APPROVED)
    assert len(pending) == 1
    assert pending[0].subject == "B"
    assert len(approved) == 1
    assert approved[0].subject == "A"


def test_decide_approve_sets_fields(queue):
    item = queue.enqueue("Projeto Z", "revisão de rotina", RiskLevel.MEDIUM)
    decided = queue.decide(item.item_id, approve=True, reviewer="joao@empresa.com", notes="Ok, sem ressalvas.")
    assert decided.status == OversightItemStatus.APPROVED
    assert decided.reviewer == "joao@empresa.com"
    assert decided.decision_notes == "Ok, sem ressalvas."
    assert decided.decided_at is not None


def test_decide_reject_sets_status(queue):
    item = queue.enqueue("Projeto W", "risco alto", RiskLevel.CRITICAL)
    decided = queue.decide(item.item_id, approve=False, reviewer="ana@empresa.com")
    assert decided.status == OversightItemStatus.REJECTED


def test_decide_twice_raises(queue):
    item = queue.enqueue("Projeto V", "motivo", RiskLevel.LOW)
    queue.decide(item.item_id, approve=True, reviewer="ana@empresa.com")
    with pytest.raises(ValueError):
        queue.decide(item.item_id, approve=False, reviewer="joao@empresa.com")


def test_decide_unknown_item_raises(queue):
    with pytest.raises(ValueError):
        queue.decide("id-inexistente", approve=True, reviewer="ana@empresa.com")


def test_get_returns_item(queue):
    item = queue.enqueue("Projeto U", "motivo", RiskLevel.LOW)
    fetched = queue.get(item.item_id)
    assert fetched.item_id == item.item_id


def test_get_unknown_raises(queue):
    with pytest.raises(ValueError):
        queue.get("id-inexistente")


def test_empty_queue_lists_nothing(queue):
    assert queue.list_items() == []
