"""Audit Logs — hash-chain local (estilo blockchain simplificado).

Cada evento registrado é encadeado ao anterior via SHA-256(prev_hash + dados
do evento atual), formando uma cadeia append-only persistida em um arquivo
`.jsonl` (uma linha JSON por evento). `verify_chain()` relê o arquivo do
início e recalcula a cadeia inteira para detectar adulteração.

IMPORTANTE (limitações de segurança): ver `core/audit_logs/CHANGELOG.md` e
`notebooks/audit_logs_dev_log.ipynb` para a discussão completa. Em resumo:
isto é integridade local (detecta erro/adulteração acidental ou por quem NÃO
controla o processo de verificação), não uma prova criptográfica contra um
atacante com acesso de escrita ao arquivo E capacidade de rodar
`verify_chain()` — esse atacante pode recalcular a cadeia inteira do zero.
Não há distribuição, consenso, nem ancoragem externa (ex. timestamping
notarial ou blockchain pública) nesta versão V1.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shared.schemas import AuditEvent, AuditEventType

# Hash gênese: usado como `prev_hash` do primeiro evento de uma cadeia.
# Convenção documentada: 64 caracteres "0" (mesmo tamanho de um SHA-256 hex).
GENESIS_HASH = "0" * 64

# Caminho padrão do arquivo de log (relativo à raiz do módulo audit_logs).
DEFAULT_LOG_PATH = Path(__file__).parent / "data" / "audit_log.jsonl"


def _compute_hash(
    prev_hash: str,
    event_type: str,
    actor: str,
    timestamp: str,
    payload: dict[str, Any],
) -> str:
    """Calcula o hash SHA-256 determinístico de um evento.

    A serialização do payload usa `json.dumps(..., sort_keys=True)` para
    garantir que o mesmo conteúdo lógico sempre produza o mesmo hash,
    independentemente da ordem de inserção das chaves em memória.
    """
    payload_serialized = json.dumps(payload, sort_keys=True, default=str)
    raw = prev_hash + event_type + actor + timestamp + payload_serialized
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class AuditLogger:
    """Logger de auditoria imutável com encadeamento de hashes (hash-chain).

    Parametrizável por caminho de arquivo (`log_path`) para permitir uso com
    arquivos temporários em testes, sem tocar no log real de produção.
    """

    def __init__(self, log_path: str | Path = DEFAULT_LOG_PATH) -> None:
        self.log_path = Path(log_path)

    # ------------------------------------------------------------------
    # Escrita
    # ------------------------------------------------------------------

    def _last_hash(self) -> str:
        """Retorna o hash do último evento gravado, ou o hash gênese."""
        if not self.log_path.exists():
            return GENESIS_HASH

        last_hash = GENESIS_HASH
        with self.log_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                last_hash = record["hash"]
        return last_hash

    def record_event(
        self,
        event_type: AuditEventType,
        actor: str,
        payload: dict[str, Any],
    ) -> AuditEvent:
        """Registra um novo evento de auditoria e o persiste em disco.

        Gera `event_id` (uuid4), timestamp UTC, e encadeia o `hash` deste
        evento ao `prev_hash` (hash do evento imediatamente anterior, ou o
        hash gênese se for o primeiro evento da cadeia).
        """
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        prev_hash = self._last_hash()
        event_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)
        timestamp_iso = timestamp.isoformat()
        event_type_value = event_type.value

        event_hash = _compute_hash(
            prev_hash=prev_hash,
            event_type=event_type_value,
            actor=actor,
            timestamp=timestamp_iso,
            payload=payload,
        )

        event = AuditEvent(
            event_id=event_id,
            event_type=event_type,
            timestamp=timestamp,
            actor=actor,
            payload=payload,
            prev_hash=prev_hash,
            hash=event_hash,
        )

        # IMPORTANTE: persistimos um dict construído manualmente (em vez de
        # `event.model_dump_json()`) para que o `timestamp` gravado seja
        # BYTE A BYTE o mesmo texto (`timestamp_iso`, formato
        # `datetime.isoformat()`) usado no cálculo de `event_hash` acima.
        # A serialização JSON do Pydantic v2 para datetimes usa sufixo "Z"
        # (ex. "...252733Z") em vez de "+00:00" — se persistíssemos via
        # `model_dump_json()`, `verify_chain()` recalcularia um hash
        # diferente do gravado mesmo para uma cadeia intacta.
        record = {
            "event_id": event_id,
            "event_type": event_type_value,
            "timestamp": timestamp_iso,
            "actor": actor,
            "payload": payload,
            "prev_hash": prev_hash,
            "hash": event_hash,
        }

        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        return event

    # ------------------------------------------------------------------
    # Verificação
    # ------------------------------------------------------------------

    def verify_chain(self) -> bool:
        """Relê o arquivo inteiro e recalcula a cadeia de hashes.

        Retorna True se:
          - o arquivo não existe ou está vazio (cadeia vazia é válida); e
          - para cada linha, o `prev_hash` bate com o hash da linha anterior
            (ou GENESIS_HASH na primeira linha); e
          - o `hash` gravado bate com o hash recalculado a partir dos dados
            daquela linha.

        Retorna False se qualquer linha foi adulterada (payload, actor,
        event_type, timestamp ou os próprios hashes) ou se a sequência de
        prev_hash está quebrada (ex. linhas reordenadas/removidas).
        """
        if not self.log_path.exists():
            return True

        expected_prev_hash = GENESIS_HASH
        with self.log_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    return False

                required_keys = {
                    "event_type",
                    "actor",
                    "timestamp",
                    "payload",
                    "prev_hash",
                    "hash",
                }
                if not required_keys.issubset(record.keys()):
                    return False

                if record["prev_hash"] != expected_prev_hash:
                    return False

                event_type_value = record["event_type"]
                if hasattr(event_type_value, "value"):
                    event_type_value = event_type_value.value

                recalculated_hash = _compute_hash(
                    prev_hash=record["prev_hash"],
                    event_type=event_type_value,
                    actor=record["actor"],
                    timestamp=record["timestamp"],
                    payload=record["payload"],
                )

                if recalculated_hash != record["hash"]:
                    return False

                expected_prev_hash = record["hash"]

        return True

    # ------------------------------------------------------------------
    # Leitura auxiliar
    # ------------------------------------------------------------------

    def read_events(self) -> list[AuditEvent]:
        """Retorna todos os eventos gravados, na ordem em que foram escritos."""
        if not self.log_path.exists():
            return []

        events: list[AuditEvent] = []
        with self.log_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                events.append(AuditEvent.model_validate_json(line))
        return events


def default_logger() -> AuditLogger:
    """Retorna um AuditLogger apontando para o log padrão do módulo.

    Função de conveniência para outros módulos que queiram registrar
    eventos de auditoria sem se preocupar com o caminho do arquivo.

    Exemplo:
        from core.audit_logs.logger import default_logger
        from shared.schemas import AuditEventType

        logger = default_logger()
        logger.record_event(
            AuditEventType.PII_SCAN,
            actor="pii_detection_module",
            payload={"findings_count": 3},
        )
    """
    return AuditLogger(DEFAULT_LOG_PATH)
