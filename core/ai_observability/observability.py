"""AI Observability — instrumentação determinística das chamadas aos módulos
do Themis AI: latência real (medida com `time.perf_counter`), contagem e
status (ok/erro), exportáveis em formato de texto compatível com o padrão de
exposição do Prometheus.

Escopo honesto desta versão: não sobe um coletor/exporter de verdade (não há
dependência de rede nem de um agente OpenTelemetry rodando) — o que existe é
o registro determinístico das métricas em memória (`ObservabilityRecorder`) e
a serialização no formato de texto que um scraper Prometheus entende. Ligar
isso a um coletor real (`opentelemetry-sdk`, endpoint `/metrics` via
`governance_copilot`) é um TODO explícito de onda futura — ver
`CHANGELOG.md` deste módulo.
"""
from __future__ import annotations

import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator

from shared.schemas import ModuleCallMetric, ObservabilitySnapshot


class ObservabilityRecorder:
    """Registro em memória de métricas de chamadas a módulos.

    Cada instância é independente (nenhum estado global compartilhado) —
    quem orquestra (ex. `governance_copilot`) decide o ciclo de vida do
    recorder (por request, por processo, etc.).
    """

    def __init__(self) -> None:
        self._metrics: list[ModuleCallMetric] = []

    def record(
        self,
        module: str,
        function: str,
        duration_ms: float,
        status: str,
        error_message: str | None = None,
    ) -> ModuleCallMetric:
        metric = ModuleCallMetric(
            module=module,
            function=function,
            started_at=datetime.now(timezone.utc),
            duration_ms=duration_ms,
            status=status,
            error_message=error_message,
        )
        self._metrics.append(metric)
        return metric

    def snapshot(self) -> ObservabilitySnapshot:
        total = len(self._metrics)
        errors = sum(1 for m in self._metrics if m.status == "error")
        avg_duration = (sum(m.duration_ms for m in self._metrics) / total) if total else 0.0
        by_module: dict[str, int] = {}
        for m in self._metrics:
            by_module[m.module] = by_module.get(m.module, 0) + 1

        return ObservabilitySnapshot(
            metrics=list(self._metrics),
            total_calls=total,
            error_count=errors,
            avg_duration_ms=round(avg_duration, 4),
            by_module=by_module,
        )

    def reset(self) -> None:
        self._metrics.clear()


@contextmanager
def traced(recorder: ObservabilityRecorder, module: str, function: str) -> Iterator[None]:
    """Context manager que mede a duração real de um bloco e registra a
    métrica no `recorder`, inclusive em caso de exceção (status="error",
    `error_message` preenchido, e a exceção original é relançada — este
    módulo nunca engole erros de outros módulos).

    Exemplo:
        recorder = ObservabilityRecorder()
        with traced(recorder, module="pii_detection", function="detect"):
            result = detect(texto)
    """
    start = time.perf_counter()
    try:
        yield
    except Exception as exc:
        duration_ms = (time.perf_counter() - start) * 1000.0
        recorder.record(module, function, duration_ms, status="error", error_message=str(exc))
        raise
    else:
        duration_ms = (time.perf_counter() - start) * 1000.0
        recorder.record(module, function, duration_ms, status="ok")


def export_prometheus_text(snapshot: ObservabilitySnapshot) -> str:
    """Serializa um `ObservabilitySnapshot` no formato de exposição de texto
    do Prometheus (`# HELP` / `# TYPE` + séries `nome{labels} valor`).

    Formato real e válido (pode ser servido diretamente por um endpoint
    `/metrics` e ser raspado por um Prometheus real) — só não há, nesta
    versão, um servidor HTTP dedicado servindo isso automaticamente.
    """
    lines = [
        "# HELP themis_module_calls_total Total de chamadas registradas por módulo.",
        "# TYPE themis_module_calls_total counter",
    ]
    for module, count in sorted(snapshot.by_module.items()):
        lines.append(f'themis_module_calls_total{{module="{module}"}} {count}')

    lines += [
        "# HELP themis_module_call_errors_total Total de chamadas com erro.",
        "# TYPE themis_module_call_errors_total counter",
        f"themis_module_call_errors_total {snapshot.error_count}",
        "# HELP themis_module_call_duration_ms_avg Duração média (ms) das chamadas registradas.",
        "# TYPE themis_module_call_duration_ms_avg gauge",
        f"themis_module_call_duration_ms_avg {snapshot.avg_duration_ms}",
    ]
    return "\n".join(lines) + "\n"
