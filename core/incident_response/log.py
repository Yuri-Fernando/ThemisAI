"""AI Incident Response — registro real de incidentes (persistido em JSON,
mesmo padrão mutável do `human_oversight`) + runbook declarativo de resposta
por severidade (`runbooks.yaml`).

Um "incidente" aqui é qualquer evento operacional negativo real do sistema de
governança (ex.: `red_team_lab` encontrou um gap de detecção explorável em
produção, `blockchain_audit_layer.verify_checkpoint_chain()` retornou
`False`, um vazamento de PII foi confirmado) — o registro liga o incidente a
`related_event_ids` da cadeia de auditoria real quando disponíveis.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import yaml

from shared.schemas import Incident, IncidentStatus, RiskLevel

DEFAULT_LOG_PATH = Path(__file__).parent / "data" / "incidents.json"
DEFAULT_RUNBOOKS_PATH = Path(__file__).parent / "runbooks.yaml"


def get_runbook(severity: RiskLevel, runbooks_path: str | Path | None = None) -> list[str]:
    """Retorna os passos declarativos do runbook para uma severidade.

    Levanta `KeyError` se a severidade não tiver runbook declarado.
    """
    path = Path(runbooks_path) if runbooks_path else DEFAULT_RUNBOOKS_PATH
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    runbooks = data.get("runbooks", {})
    key = severity.value if hasattr(severity, "value") else severity
    if key not in runbooks:
        raise KeyError(f"Nenhum runbook declarado para a severidade '{key}'.")
    return list(runbooks[key]["steps"])


class IncidentLog:
    """Registro real de incidentes, persistido em JSON (mutável — status
    evolui de `open` para `investigating`/`resolved`)."""

    def __init__(self, storage_path: str | Path | None = None) -> None:
        self.storage_path = Path(storage_path) if storage_path else DEFAULT_LOG_PATH

    def _read(self) -> list[Incident]:
        if not self.storage_path.exists():
            return []
        raw = json.loads(self.storage_path.read_text(encoding="utf-8"))
        return [Incident.model_validate(i) for i in raw]

    def _write(self, incidents: list[Incident]) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [json.loads(i.model_dump_json()) for i in incidents]
        self.storage_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def report_incident(
        self,
        title: str,
        description: str,
        severity: RiskLevel,
        related_event_ids: list[str] | None = None,
    ) -> Incident:
        incident = Incident(
            incident_id=str(uuid.uuid4()),
            created_at=datetime.now(timezone.utc),
            title=title,
            description=description,
            severity=severity,
            status=IncidentStatus.OPEN,
            related_event_ids=related_event_ids or [],
        )
        incidents = self._read()
        incidents.append(incident)
        self._write(incidents)
        return incident

    def list_incidents(self, status: IncidentStatus | None = None) -> list[Incident]:
        incidents = self._read()
        if status is None:
            return incidents
        return [i for i in incidents if i.status == status]

    def update_status(
        self,
        incident_id: str,
        status: IncidentStatus,
        resolution_notes: str | None = None,
    ) -> Incident:
        """Atualiza o status de um incidente. `RESOLVED` exige
        `resolution_notes` e registra `resolved_at`. Levanta `ValueError`
        para transições inválidas (não é possível "reabrir" um incidente já
        resolvido nesta versão) ou incidente inexistente.
        """
        incidents = self._read()
        for idx, incident in enumerate(incidents):
            if incident.incident_id != incident_id:
                continue
            if incident.status == IncidentStatus.RESOLVED:
                raise ValueError(f"Incidente '{incident_id}' já está resolvido e não pode ser reaberto.")
            if status == IncidentStatus.RESOLVED and not resolution_notes:
                raise ValueError("Resolver um incidente exige `resolution_notes`.")

            update = {"status": status}
            if status == IncidentStatus.RESOLVED:
                update["resolved_at"] = datetime.now(timezone.utc)
                update["resolution_notes"] = resolution_notes
            updated = incident.model_copy(update=update)
            incidents[idx] = updated
            self._write(incidents)
            return updated

        raise ValueError(f"Incidente '{incident_id}' não encontrado.")

    def get(self, incident_id: str) -> Incident:
        for incident in self._read():
            if incident.incident_id == incident_id:
                return incident
        raise ValueError(f"Incidente '{incident_id}' não encontrado.")
