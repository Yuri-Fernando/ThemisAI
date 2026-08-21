"""API FastAPI do Governance Copilot — contrato consumido por
`apps/dashboard/client.py` (`GovernanceCopilotClient`).

Cada endpoint é uma casca HTTP fininha em cima de uma função pública já
existente em outro módulo — nenhuma lógica de domínio é reimplementada
aqui, só validação de request/response (Pydantic), tradução de exceções de
domínio para HTTP, e a orquestração de cross-cutting concerns reais (auth,
autorização, observabilidade, auditoria, persistência) descritos abaixo.

**V5 (2026-08-21) fechou os itens de prioridade Alta/Média do plano de
melhorias** (`docs/architecture/future-improvements.md`) que bloqueavam
deploy real:
- **Autenticação** (item 3): `X-API-Key` opcional, ver `auth.py` — desabilitada
  por padrão (uso local), ativa quando `THEMIS_API_KEY` está definida.
- **CORS** (item 3): configurável via `THEMIS_CORS_ORIGINS` (CSV), `*` por
  padrão.
- **Fila de revisão humana alimentada automaticamente** (item 4): todo
  `PolicyDecision` com `REQUIRES_HUMAN_REVIEW` num RIPD gerado vira um item
  real em `human_oversight` sozinho.
- **Enforcement real** (item 7): cada endpoint é decorado com
  `@enforce(agent_id, action)` (`runtime_policy_enforcement`, V3) — a
  autorização declarada em `multi_agent_governance/agents.yaml` deixa de
  ser só consultiva.
- **Observabilidade real** (item 8): `GET /metrics` expõe
  `ai_observability.export_prometheus_text()` sobre as chamadas reais dos
  outros endpoints.
- **Trilha de auditoria para endpoints que antes não geravam nenhuma**
  (item 6): `pii/detect`, `prompt-security/scan` e `policy/evaluate` agora
  registram um evento real de auditoria por chamada, correlacionável via
  `GET /api/v1/audit/trace/{trace_id}` (`traceability`, V2).
- **RIPDs persistidos e consultáveis** (item 14): `ripd_store.py`.
- **Checagem de saúde sob demanda** (item 5, versão honesta): endpoint que
  roda os checks e aciona `self_healing_governance` — não há scheduler/cron
  real embutido (isso continua exigindo um disparador externo periódico,
  documentado como tal).

Endpoints:
    GET  /health
    GET  /metrics
    POST /api/v1/pii/detect
    POST /api/v1/prompt-security/scan
    POST /api/v1/policy/evaluate
    POST /api/v1/ripd/generate
    GET  /api/v1/ripd
    GET  /api/v1/ripd/{ripd_id}
    GET  /api/v1/audit/verify
    GET  /api/v1/audit/events
    GET  /api/v1/audit/trace/{trace_id}
    POST /api/v1/health-check/run
"""
from __future__ import annotations

import os
import uuid
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.ai_observability.observability import ObservabilityRecorder, export_prometheus_text, traced
from core.audit_logs.logger import default_logger
from core.human_oversight.queue import OversightQueue
from core.pii_detection.detector import detect
from core.policy_engine.engine import evaluate
from core.prompt_security.scanner import scan
from core.ripd_engine.generator import generate_ripd
from core.runtime_policy_enforcement.enforcement import enforce
from core.self_healing_governance.healer import check_and_heal
from core.traceability.tracer import trace_events
from core.governance_copilot.auth import require_api_key
from core.governance_copilot.ripd_store import RIPDStore
from shared.schemas import (
    AuditEvent,
    AuditEventType,
    DataCategory,
    HealingAction,
    LegalBasis,
    PIIDetectionResult,
    PolicyDecision,
    PolicyDecisionStatus,
    PromptSecurityResult,
    RIPDReport,
    SCHEMA_VERSION,
    TraceLink,
)

app = FastAPI(
    title="Themis AI — Governance Copilot",
    description=(
        "API de orquestração dos módulos de governança de IA/LGPD do "
        "Themis AI. Motor 100% local e determinístico — nenhuma "
        "chamada a LLM em nenhum endpoint."
    ),
    version=SCHEMA_VERSION,
)

_CORS_ENV_VAR = "THEMIS_CORS_ORIGINS"
_cors_origins = [o.strip() for o in os.environ.get(_CORS_ENV_VAR, "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Estado do processo (não persistido entre restarts) — mesmo padrão de
# ObservabilityRecorder documentado em core/ai_observability: quem orquestra
# decide o ciclo de vida; aqui é o processo da API inteiro.
_recorder = ObservabilityRecorder()
_ripd_store = RIPDStore()
_oversight_queue = OversightQueue()


# ---------------------------------------------------------------------------
# Request bodies (não existem em shared/schemas.py — são só "formulários de
# entrada" HTTP, não resultados de domínio)
# ---------------------------------------------------------------------------

class PIIDetectRequest(BaseModel):
    text: str


class PromptSecurityScanRequest(BaseModel):
    prompt: str


class PolicyEvaluateRequest(BaseModel):
    data_categories: list[DataCategory]
    legal_basis: LegalBasis
    context: dict[str, Any] | None = None


class RIPDGenerateRequest(BaseModel):
    project_name: str
    project_description: str
    data_categories: list[DataCategory]
    legal_basis: LegalBasis
    context: dict[str, Any] | None = None


class HealthCheckRunRequest(BaseModel):
    checks: dict[str, bool]


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _log_trace_event(event_type: AuditEventType, payload: dict[str, Any]) -> str:
    """Registra um evento de auditoria real com um `trace_id` novo no
    payload, e retorna o `trace_id` — para endpoints que antes (V1/V2) não
    geravam NENHUM evento de auditoria (`pii/detect`, `prompt-security/scan`,
    `policy/evaluate`). Correlacionável depois via
    `GET /api/v1/audit/trace/{trace_id}`.
    """
    trace_id = str(uuid.uuid4())
    default_logger().record_event(event_type, actor="governance_copilot", payload={**payload, "trace_id": trace_id})
    return trace_id


def _auto_enqueue_human_review(project_name: str, decisions: list[PolicyDecision]) -> list[str]:
    """Enfileira automaticamente em `human_oversight` toda `PolicyDecision`
    com `REQUIRES_HUMAN_REVIEW` — fecha o item 4 do plano de melhorias
    (antes, `enqueue()` precisava ser chamado manualmente)."""
    item_ids = []
    for decision in decisions:
        if decision.status != PolicyDecisionStatus.REQUIRES_HUMAN_REVIEW:
            continue
        item = _oversight_queue.enqueue(
            subject=f"{project_name} — política {decision.policy_id}",
            reason=decision.rationale,
            risk_level=decision.risk_level,
        )
        item_ids.append(item.item_id)
    return item_ids


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> dict[str, str]:
    """Healthcheck simples — sem autenticação/autorização, para load
    balancers e orquestradores de container conseguirem checar sem credencial."""
    return {"status": "ok"}


@app.get("/metrics", dependencies=[Depends(require_api_key)])
@enforce(agent_id="auditor", action="ai_observability.export")
def metrics() -> Response:
    """Métricas reais das chamadas registradas neste processo, em formato
    de exposição do Prometheus (`ai_observability`, V2)."""
    text = export_prometheus_text(_recorder.snapshot())
    return Response(content=text, media_type="text/plain; version=0.0.4")


@app.post("/api/v1/pii/detect", response_model=PIIDetectionResult, dependencies=[Depends(require_api_key)])
@enforce(agent_id="ripd_generator", action="pii_detection.detect")
def pii_detect(body: PIIDetectRequest) -> PIIDetectionResult:
    with traced(_recorder, module="pii_detection", function="detect"):
        result = detect(body.text)
    _log_trace_event(
        AuditEventType.PII_SCAN,
        {"has_sensitive_data": result.has_sensitive_data, "findings_count": len(result.findings)},
    )
    return result


@app.post("/api/v1/prompt-security/scan", response_model=PromptSecurityResult, dependencies=[Depends(require_api_key)])
@enforce(agent_id="ripd_generator", action="prompt_security.scan")
def prompt_security_scan(body: PromptSecurityScanRequest) -> PromptSecurityResult:
    with traced(_recorder, module="prompt_security", function="scan"):
        result = scan(body.prompt)
    _log_trace_event(
        AuditEventType.PROMPT_SECURITY_SCAN,
        {"is_safe": result.is_safe, "score": result.score},
    )
    return result


@app.post("/api/v1/policy/evaluate", response_model=list[PolicyDecision], dependencies=[Depends(require_api_key)])
@enforce(agent_id="ripd_generator", action="policy_engine.evaluate")
def policy_evaluate(body: PolicyEvaluateRequest) -> list[PolicyDecision]:
    with traced(_recorder, module="policy_engine", function="evaluate"):
        decisions = evaluate(
            data_categories=body.data_categories,
            legal_basis=body.legal_basis,
            context=body.context,
        )
    _log_trace_event(
        AuditEventType.POLICY_EVALUATION,
        {"decision_count": len(decisions), "statuses": [d.status.value for d in decisions]},
    )
    return decisions


@app.post("/api/v1/ripd/generate", response_model=RIPDReport, dependencies=[Depends(require_api_key)])
@enforce(agent_id="ripd_generator", action="ripd_engine.generate_ripd")
def ripd_generate(body: RIPDGenerateRequest, response: Response) -> RIPDReport:
    try:
        with traced(_recorder, module="ripd_engine", function="generate_ripd"):
            report = generate_ripd(
                project_name=body.project_name,
                project_description=body.project_description,
                data_categories=body.data_categories,
                legal_basis=body.legal_basis,
                context=body.context,
            )
    except Exception as exc:  # pragma: no cover — defensivo, ver notebook de dev-log
        # generate_ripd() já é 100% determinístico/local (sem I/O de rede);
        # a única falha plausível em produção é o índice do Regulatory RAG
        # ainda não ter sido construído (`core/regulatory_rag/data/` vazio).
        raise HTTPException(
            status_code=500,
            detail=f"Falha ao gerar RIPD: {exc}",
        ) from exc

    ripd_id = _ripd_store.save(report)
    response.headers["X-RIPD-Id"] = ripd_id

    enqueued = _auto_enqueue_human_review(report.project_name, report.policy_decisions)
    if enqueued:
        response.headers["X-Human-Review-Item-Ids"] = ",".join(enqueued)

    return report


@app.get("/api/v1/ripd", dependencies=[Depends(require_api_key)])
@enforce(agent_id="ripd_generator", action="governance_copilot.ripd_store")
def ripd_list() -> list[dict[str, str]]:
    """Lista resumida de todos os RIPDs já gerados e persistidos (item 14)."""
    return _ripd_store.list_summaries()


@app.get("/api/v1/ripd/{ripd_id}", response_model=RIPDReport, dependencies=[Depends(require_api_key)])
@enforce(agent_id="ripd_generator", action="governance_copilot.ripd_store")
def ripd_get(ripd_id: str) -> RIPDReport:
    try:
        return _ripd_store.get(ripd_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/audit/verify", dependencies=[Depends(require_api_key)])
@enforce(agent_id="auditor", action="audit_logs.verify_chain")
def audit_verify() -> dict[str, bool]:
    return {"valid": default_logger().verify_chain()}


@app.get("/api/v1/audit/events", response_model=list[AuditEvent], dependencies=[Depends(require_api_key)])
@enforce(agent_id="auditor", action="audit_logs.read_events")
def audit_events(limit: int = Query(default=50, ge=1, le=1000)) -> list[AuditEvent]:
    events = default_logger().read_events()
    if limit >= len(events):
        return events
    return events[-limit:]


@app.get("/api/v1/audit/trace/{trace_id}", response_model=TraceLink, dependencies=[Depends(require_api_key)])
@enforce(agent_id="auditor", action="traceability.trace_by_correlation_key")
def audit_trace(trace_id: str) -> TraceLink:
    """Correlaciona todos os eventos de auditoria com esse `trace_id` no
    payload (gerados por `pii/detect`, `prompt-security/scan`,
    `policy/evaluate` — ver `_log_trace_event`). Item 6 do plano de melhorias."""
    events = default_logger().read_events()
    try:
        return trace_events(events, correlation_key="trace_id", correlation_value=trace_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/v1/health-check/run", response_model=list[HealingAction], dependencies=[Depends(require_api_key)])
@enforce(agent_id="auditor", action="self_healing_governance.check_and_heal")
def health_check_run(body: HealthCheckRunRequest) -> list[HealingAction]:
    """Roda `self_healing_governance.check_and_heal()` sobre os checks
    informados pelo chamador. **Não há scheduler/cron embutido** (item 5,
    versão honesta) — um disparador externo (cron, GitHub Actions agendado,
    etc.) precisa chamar este endpoint periodicamente para virar automação
    de verdade; documentado, não fingido como já automático."""
    return check_and_heal(body.checks)
