# Changelog — AI Observability

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Este módulo segue SemVer independente (`core/ai_observability/`).

## [0.1.0] - 2026-08-20

### Added

- `observability.py`:
  - `ObservabilityRecorder` — registro em memória de métricas de chamadas
    (`record`, `snapshot`, `reset`), sem estado global compartilhado.
  - `traced(recorder, module, function)` — context manager que mede duração
    real com `time.perf_counter()`, registra status `ok`/`error` (relançando
    qualquer exceção original — nunca a engole) e `error_message`.
  - `export_prometheus_text(snapshot) -> str` — serializa um
    `ObservabilitySnapshot` no formato de exposição de texto do Prometheus
    (`# HELP`/`# TYPE` + séries), válido para ser servido por um endpoint
    `/metrics` real.
- Contratos novos em `shared/schemas.py` (`ModuleCallMetric`,
  `ObservabilitySnapshot`).
- Suíte de testes pytest (`tests/test_observability.py`, 7 testes): chamada
  real a `pii_detection.detect()` registrada com sucesso; exceção real
  registrada como erro e relançada; média de duração e contagem por módulo
  corretas com sleeps reais; snapshot vazio; reset; formato de exportação
  Prometheus (inclusive snapshot vazio).

### Notes

- **Escopo honesto**: não sobe um coletor/exporter de verdade nem depende de
  rede — o registro é em memória, por instância de `ObservabilityRecorder`
  (quem orquestra decide o ciclo de vida: por request, por processo, etc.).
  Ligar isso a `opentelemetry-sdk` e/ou a um endpoint `/metrics` real em
  `core/governance_copilot` é TODO explícito de onda futura, documentado
  aqui — não fingido como já pronto.
- Duração medida é da execução real do bloco `with traced(...)`, nunca
  simulada/mockada — os testes usam `time.sleep()` real para gerar durações
  não-triviais quando necessário.
