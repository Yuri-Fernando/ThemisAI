"""Human Oversight — fila determinística de itens que exigem revisão humana.

Alimentada tipicamente por `PolicyDecisionStatus.REQUIRES_HUMAN_REVIEW` (do
`policy_engine`, V1), mas aceita qualquer motivo (`enqueue` é genérico). Cada
item tem um ciclo de vida simples: `pending -> approved` ou `pending ->
rejected`, decidido uma única vez, por um revisor identificado, com timestamp
e notas — a peça que falta para o "direito à revisão" do Art. 20 da LGPD
virar um fluxo operacional real, não só uma flag num `PolicyDecision`.

Persistência: arquivo JSON único (lista de itens), não um `.jsonl`
append-only como `audit_logs` — diferente de um log de auditoria, um item da
fila de revisão é **mutável** (muda de `pending` para `approved`/`rejected`),
então precisa de leitura+escrita completa, não só apêndice.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from shared.schemas import OversightItem, OversightItemStatus, RiskLevel

DEFAULT_QUEUE_PATH = Path(__file__).parent / "data" / "oversight_queue.json"


class OversightQueue:
    """Fila de itens pendentes de revisão humana, persistida em JSON."""

    def __init__(self, storage_path: str | Path | None = None) -> None:
        self.storage_path = Path(storage_path) if storage_path else DEFAULT_QUEUE_PATH

    # ------------------------------------------------------------------
    # Persistência
    # ------------------------------------------------------------------

    def _read_items(self) -> list[OversightItem]:
        if not self.storage_path.exists():
            return []
        raw = json.loads(self.storage_path.read_text(encoding="utf-8"))
        return [OversightItem.model_validate(item) for item in raw]

    def _write_items(self, items: list[OversightItem]) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [json.loads(item.model_dump_json()) for item in items]
        self.storage_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def enqueue(self, subject: str, reason: str, risk_level: RiskLevel) -> OversightItem:
        """Adiciona um novo item `pending` à fila."""
        item = OversightItem(
            item_id=str(uuid.uuid4()),
            created_at=datetime.now(timezone.utc),
            subject=subject,
            reason=reason,
            risk_level=risk_level,
            status=OversightItemStatus.PENDING,
        )
        items = self._read_items()
        items.append(item)
        self._write_items(items)
        return item

    def list_items(self, status: OversightItemStatus | None = None) -> list[OversightItem]:
        """Lista itens da fila, opcionalmente filtrados por status."""
        items = self._read_items()
        if status is None:
            return items
        return [i for i in items if i.status == status]

    def get(self, item_id: str) -> OversightItem:
        for item in self._read_items():
            if item.item_id == item_id:
                return item
        raise ValueError(f"Item de revisão '{item_id}' não encontrado.")

    def decide(
        self,
        item_id: str,
        approve: bool,
        reviewer: str,
        notes: str | None = None,
    ) -> OversightItem:
        """Registra a decisão de um revisor sobre um item `pending`.

        Levanta `ValueError` se o item não existir ou já tiver sido decidido
        (a decisão é definitiva nesta versão — reabrir um item decidido não é
        suportado, por design: cria um novo item se necessário).
        """
        items = self._read_items()
        for idx, item in enumerate(items):
            if item.item_id != item_id:
                continue
            if item.status != OversightItemStatus.PENDING:
                raise ValueError(
                    f"Item '{item_id}' já foi decidido (status atual: {item.status.value})."
                )
            decided = item.model_copy(
                update={
                    "status": OversightItemStatus.APPROVED if approve else OversightItemStatus.REJECTED,
                    "reviewer": reviewer,
                    "decided_at": datetime.now(timezone.utc),
                    "decision_notes": notes,
                }
            )
            items[idx] = decided
            self._write_items(items)
            return decided

        raise ValueError(f"Item de revisão '{item_id}' não encontrado.")
