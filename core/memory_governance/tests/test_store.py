"""Testes do Memory Governance — redação real via pii_detection.detect,
persistência real em arquivo temporário."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from core.memory_governance.store import MemoryStore
from shared.schemas import DataCategory, MemoryItem


@pytest.fixture()
def store(tmp_path):
    return MemoryStore(storage_path=tmp_path / "memory.json")


def test_store_content_without_pii_is_not_redacted(store):
    item = store.store("Lembrete: revisar o relatório trimestral na sexta-feira.")
    assert item.redacted is False
    assert item.category == DataCategory.NOT_PERSONAL
    assert "revisar o relatório" in item.content


def test_store_content_with_cpf_is_redacted(store):
    item = store.store("Cliente João, CPF 111.444.777-35, pediu reembolso.")
    assert item.redacted is True
    assert "111.444.777-35" not in item.content
    assert "[REDACTED:CPF]" in item.content
    assert "Cliente João" in item.content  # resto do texto preservado


def test_store_sensitive_content_marks_sensitive_category(store):
    item = store.store("Paciente com histórico de câncer, CPF 111.444.777-35.")
    assert item.category in (DataCategory.SENSITIVE, DataCategory.PERSONAL)
    assert item.redacted is True


def test_store_with_ttl_sets_expires_at(store):
    item = store.store("Nota sem PII.", ttl_days=7)
    assert item.expires_at is not None
    assert item.expires_at > datetime.now(timezone.utc)


def test_store_without_ttl_never_expires(store):
    item = store.store("Nota permanente sem PII.")
    assert item.expires_at is None


def test_list_active_excludes_expired_items(store):
    store.store("Item ativo.", ttl_days=30)

    # Injeta diretamente um item já expirado (contorna store(), que só aceita TTL futuro).
    expired_item = MemoryItem(
        memory_id="expired-1",
        created_at=datetime.now(timezone.utc) - timedelta(days=10),
        content="Item expirado.",
        category=DataCategory.NOT_PERSONAL,
        redacted=False,
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    items = store._read()
    items.append(expired_item)
    store._write(items)

    active = store.list_active()
    assert len(active) == 1
    assert active[0].content == "Item ativo."


def test_purge_expired_removes_from_disk(store):
    store.store("Item ativo.", ttl_days=30)
    expired_item = MemoryItem(
        memory_id="expired-2",
        created_at=datetime.now(timezone.utc) - timedelta(days=10),
        content="Item expirado.",
        category=DataCategory.NOT_PERSONAL,
        redacted=False,
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    items = store._read()
    items.append(expired_item)
    store._write(items)

    purged = store.purge_expired()
    assert purged == 1
    assert len(store._read()) == 1


def test_purge_expired_returns_zero_when_nothing_expired(store):
    store.store("Item ativo.", ttl_days=30)
    assert store.purge_expired() == 0
