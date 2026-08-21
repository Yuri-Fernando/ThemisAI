"""Memory Governance — governa o que um sistema de IA pode persistir entre
sessões (memória de longo prazo de um agente, cache de conversas, etc.).

Toda escrita passa primeiro pelo `pii_detection.detect()` real (V1): se o
conteúdo contém PII, os spans encontrados são redigidos (`[REDACTED:TIPO]`)
ANTES de persistir — o texto original com PII nunca toca o disco. Isso não é
uma política opcional configurável nesta versão: é o comportamento padrão e
único de `MemoryStore.store()`, por design (memória de longo prazo é
exatamente o tipo de superfície onde PII vaza sem ninguém perceber, se não
houver um portão automático).
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from core.pii_detection.detector import detect
from shared.schemas import DataCategory, MemoryItem

DEFAULT_STORE_PATH = Path(__file__).parent / "data" / "memory_items.json"


def _redact(content: str, findings: list) -> str:
    """Substitui cada span de PII encontrado por `[REDACTED:TIPO]`, processando
    de trás para frente (maior `start` primeiro) para não invalidar os
    offsets dos spans anteriores."""
    redacted = content
    for finding in sorted(findings, key=lambda f: f.start, reverse=True):
        replacement = f"[REDACTED:{finding.entity_type}]"
        redacted = redacted[: finding.start] + replacement + redacted[finding.end :]
    return redacted


class MemoryStore:
    """Armazenamento de itens de memória com redação automática de PII e
    expiração opcional (TTL), persistido em JSON mutável (mesmo padrão de
    `human_oversight`/`incident_response` — itens não são append-only, a
    purga de expirados reescreve o arquivo)."""

    def __init__(self, storage_path: str | Path | None = None) -> None:
        self.storage_path = Path(storage_path) if storage_path else DEFAULT_STORE_PATH

    def _read(self) -> list[MemoryItem]:
        if not self.storage_path.exists():
            return []
        raw = json.loads(self.storage_path.read_text(encoding="utf-8"))
        return [MemoryItem.model_validate(i) for i in raw]

    def _write(self, items: list[MemoryItem]) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [json.loads(i.model_dump_json()) for i in items]
        self.storage_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def store(self, content: str, ttl_days: int | None = None) -> MemoryItem:
        """Escaneia `content` por PII real (`pii_detection.detect`), redige
        qualquer achado, e persiste o item resultante — nunca o texto
        original se houve PII encontrado.
        """
        pii_result = detect(content)

        if pii_result.findings:
            stored_content = _redact(content, pii_result.findings)
            redacted = True
            category = (
                DataCategory.SENSITIVE if pii_result.has_sensitive_data else DataCategory.PERSONAL
            )
        else:
            stored_content = content
            redacted = False
            category = DataCategory.NOT_PERSONAL

        now = datetime.now(timezone.utc)
        item = MemoryItem(
            memory_id=str(uuid.uuid4()),
            created_at=now,
            content=stored_content,
            category=category,
            redacted=redacted,
            expires_at=(now + timedelta(days=ttl_days)) if ttl_days else None,
        )
        items = self._read()
        items.append(item)
        self._write(items)
        return item

    def list_active(self) -> list[MemoryItem]:
        """Lista itens não expirados (não remove nada do disco — use
        `purge_expired()` para isso)."""
        now = datetime.now(timezone.utc)
        return [i for i in self._read() if i.expires_at is None or i.expires_at > now]

    def purge_expired(self) -> int:
        """Remove permanentemente itens expirados do armazenamento. Retorna
        quantos itens foram removidos."""
        now = datetime.now(timezone.utc)
        items = self._read()
        active = [i for i in items if i.expires_at is None or i.expires_at > now]
        purged_count = len(items) - len(active)
        if purged_count:
            self._write(active)
        return purged_count
