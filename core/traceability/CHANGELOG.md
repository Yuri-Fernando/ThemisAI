# Changelog — Traceability

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Este módulo segue SemVer independente (`core/traceability/`).

## [0.1.0] - 2026-08-20

### Added

- `tracer.py`:
  - `trace_events(events, correlation_key, correlation_value) -> TraceLink`
    — agrupa eventos de auditoria cujo `payload[correlation_key]` bate com o
    valor informado, ordenados cronologicamente. Levanta `ValueError` se
    nenhum evento casar.
  - `trace_by_correlation_key(correlation_key, logger=None) -> list[TraceLink]`
    — constrói uma `TraceLink` por valor distinto de `correlation_key`
    encontrado na cadeia de auditoria real (via `audit_logs.read_events()`),
    na ordem de primeira ocorrência.
- Contrato novo em `shared/schemas.py` (`TraceLink`).
- Suíte de testes pytest (`tests/test_tracer.py`, 7 testes) sobre uma
  `AuditLogger` real isolada em arquivo temporário: agrupamento correto;
  erro sem match; resumo menciona contagem e tipos de evento; um trace por
  valor distinto; eventos sem a chave de correlação são ignorados (não
  geram trace); log vazio; ordenação cronológica.

### Notes

- **Escopo honesto**: correlação por chave de payload já existente (ex.
  `project_name`), não um "trace_id" distribuído estilo OpenTelemetry — não
  há propagação de contexto entre módulos nesta versão (nenhum módulo grava
  um `trace_id` compartilhado no payload automaticamente). Suficiente para
  responder "quais eventos pertencem à mesma operação de negócio?" quando os
  eventos já compartilham um identificador de negócio no payload — não
  substitui tracing distribuído de verdade.
- Não reimplementa nada de `audit_logs` — só lê `read_events()` e agrupa.
- TODO onda futura: gravação automática de um `trace_id` correlato pelo
  próprio `ripd_engine`/`governance_copilot` em todos os eventos de uma
  mesma operação, eliminando a dependência de o chamador escolher a chave de
  correlação certa manualmente.
