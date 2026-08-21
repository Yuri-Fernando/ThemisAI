"""Traceability — agrupa eventos de auditoria já gravados em `core/audit_logs`
numa cadeia de proveniência consultável (`TraceLink`), sem reimplementar
nada do `audit_logs` (só lê `read_events()` e agrupa).

**Correlação por chave de payload, não por infraestrutura nova.** Este
módulo não inventa um "trace_id" distribuído (ex. estilo OpenTelemetry
trace context) — não existe propagação de contexto entre módulos nesta
versão. O que existe de real é a correlação de eventos que já compartilham
um valor de payload em comum (ex. `project_name` num conjunto de eventos
`RIPD_GENERATED`/`PII_SCAN`/`POLICY_EVALUATION` do mesmo projeto) — suficiente
para responder "quais eventos de auditoria pertencem à mesma operação de
negócio?", sem fingir uma infraestrutura de tracing distribuído que não
existe.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from core.audit_logs.logger import AuditLogger, default_logger
from shared.schemas import AuditEvent, TraceLink


def trace_events(events: list[AuditEvent], correlation_key: str, correlation_value: Any) -> TraceLink:
    """Agrupa os eventos cujo `payload[correlation_key] == correlation_value`
    numa única `TraceLink`.

    Levanta `ValueError` se nenhum evento casar.
    """
    matched = [e for e in events if e.payload.get(correlation_key) == correlation_value]
    if not matched:
        raise ValueError(
            f"Nenhum evento com payload['{correlation_key}'] == {correlation_value!r} encontrado."
        )

    matched.sort(key=lambda e: e.timestamp)
    event_types = ", ".join(dict.fromkeys(e.event_type.value for e in matched))
    summary = (
        f"{len(matched)} evento(s) correlacionado(s) por '{correlation_key}'={correlation_value!r} "
        f"({event_types}), entre {matched[0].timestamp.isoformat()} e {matched[-1].timestamp.isoformat()}."
    )

    return TraceLink(
        trace_id=str(uuid.uuid4()),
        event_ids=[e.event_id for e in matched],
        created_at=datetime.now(timezone.utc),
        summary=summary,
    )


def trace_by_correlation_key(
    correlation_key: str,
    logger: AuditLogger | None = None,
) -> list[TraceLink]:
    """Constrói uma `TraceLink` para cada valor distinto de
    `payload[correlation_key]` encontrado na cadeia de auditoria, na ordem
    em que o valor apareceu pela primeira vez.

    Eventos cujo payload não tem `correlation_key` são ignorados (não geram
    trace) — sem chave de correlação, não há como agrupá-los de forma real.
    """
    logger = logger or default_logger()
    events = logger.read_events()

    seen_values: list[Any] = []
    for event in events:
        if correlation_key in event.payload and event.payload[correlation_key] not in seen_values:
            seen_values.append(event.payload[correlation_key])

    return [trace_events(events, correlation_key, value) for value in seen_values]
