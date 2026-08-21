"""Governance Copilot — persistência de RIPDs gerados (V5, item 14).

`POST /api/v1/ripd/generate` (V1/V2) retornava o `RIPDReport` mas não o
guardava em lugar nenhum — sem histórico, sem `GET /api/v1/ripd/{id}`. Este
módulo fecha essa lacuna com um armazenamento real (JSON, mesmo padrão
mutável de `human_oversight`/`incident_response`): cada RIPD gerado ganha um
`ripd_id` e fica consultável depois.

Não reimplementa `ripd_engine` — só persiste o `RIPDReport` já produzido por
ele.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

from shared.schemas import RIPDReport

DEFAULT_STORE_PATH = Path(__file__).parent / "data" / "ripd_reports.json"


class StoredRIPD:
    """Um RIPD armazenado, com o id gerado no momento do armazenamento."""

    def __init__(self, ripd_id: str, report: RIPDReport) -> None:
        self.ripd_id = ripd_id
        self.report = report


class RIPDStore:
    """Armazenamento real de `RIPDReport`s gerados, persistido em JSON."""

    def __init__(self, storage_path: str | Path | None = None) -> None:
        self.storage_path = Path(storage_path) if storage_path else DEFAULT_STORE_PATH

    def _read(self) -> dict[str, RIPDReport]:
        if not self.storage_path.exists():
            return {}
        raw = json.loads(self.storage_path.read_text(encoding="utf-8"))
        return {ripd_id: RIPDReport.model_validate(data) for ripd_id, data in raw.items()}

    def _write(self, items: dict[str, RIPDReport]) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {ripd_id: json.loads(report.model_dump_json()) for ripd_id, report in items.items()}
        self.storage_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def save(self, report: RIPDReport) -> str:
        """Persiste `report` e retorna o `ripd_id` gerado."""
        items = self._read()
        ripd_id = str(uuid.uuid4())
        items[ripd_id] = report
        self._write(items)
        return ripd_id

    def get(self, ripd_id: str) -> RIPDReport:
        """Levanta `KeyError` se `ripd_id` não existir."""
        items = self._read()
        if ripd_id not in items:
            raise KeyError(f"RIPD '{ripd_id}' não encontrado.")
        return items[ripd_id]

    def list_summaries(self) -> list[dict[str, str]]:
        """Lista resumida (id, nome do projeto, data de geração, nível de
        risco) — sem devolver o `RIPDReport` inteiro de cada um."""
        items = self._read()
        return [
            {
                "ripd_id": ripd_id,
                "project_name": report.project_name,
                "generated_at": report.generated_at.isoformat(),
                "risk_level": report.trust_score.risk_level.value,
            }
            for ripd_id, report in items.items()
        ]
