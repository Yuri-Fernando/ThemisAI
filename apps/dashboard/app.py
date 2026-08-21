"""Dashboard Streamlit do Themis AI.

Consome o backend (`core/governance_copilot`, API FastAPI) exclusivamente via
HTTP através de `GovernanceCopilotClient` (`apps/dashboard/client.py`) —
nunca por import direto. Isso desacopla este módulo do ciclo de vida do
backend: o dashboard pode ser desenvolvido, testado e até demonstrado (com a
seção "Visão geral", que lê `status/*.json` direto do disco) mesmo antes do
backend existir ou enquanto ele está fora do ar.

Este arquivo separa deliberadamente:
    - Funções PURAS de leitura/formatação (topo do arquivo) — sem nenhuma
      chamada a `streamlit`, testáveis via pytest comum.
    - Funções de renderização Streamlit (`render_*`) — chamam `st.*`, não são
      exercitadas pela suíte de testes (Streamlit não roda de forma simples
      fora do `streamlit run`); toda a lógica de negócio não-trivial que elas
      usam foi extraída para as funções puras acima.

Rodar: `streamlit run apps/dashboard/app.py` a partir da raiz do repo.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Garante que `shared` e `apps.dashboard.client` são importáveis mesmo quando
# o Streamlit executa este arquivo diretamente (sys.path[0] vira o diretório
# do script, não a raiz do repo).
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from apps.dashboard.client import (  # noqa: E402
    GovernanceCopilotClient,
    GovernanceCopilotConnectionError,
    GovernanceCopilotHTTPError,
)
from shared.schemas import (  # noqa: E402
    AuditEvent,
    PIIDetectionResult,
    PolicyDecision,
    PromptSecurityResult,
    RIPDReport,
)

# ---------------------------------------------------------------------------
# Constantes de domínio (espelham ROADMAP.md — V1, 10 capacidades)
# ---------------------------------------------------------------------------

V1_ROADMAP_MODULES: list[dict[str, str]] = [
    {"key": "policy_engine", "label": "Policy Engine", "folder": "core/policy_engine/"},
    {"key": "pii_detection", "label": "PII Detection", "folder": "core/pii_detection/"},
    {"key": "prompt_security", "label": "Prompt Security (injection/jailbreak)", "folder": "core/prompt_security/"},
    {"key": "explainability", "label": "Explainability", "folder": "core/explainability/"},
    {"key": "trust_score", "label": "AI Trust Score", "folder": "core/trust_score/"},
    {"key": "audit_logs", "label": "Audit Logs (hash-chain)", "folder": "core/audit_logs/"},
    {"key": "regulatory_rag", "label": "Regulatory RAG (base local LGPD)", "folder": "core/regulatory_rag/"},
    {"key": "ripd_engine", "label": "RIPD Engine (gerador automático)", "folder": "core/ripd_engine/"},
    {"key": "governance_copilot", "label": "Governance Copilot (orquestrador + API)", "folder": "core/governance_copilot/"},
    {"key": "dashboard", "label": "Dashboard", "folder": "apps/dashboard/"},
]

DATA_CATEGORY_OPTIONS = ["personal", "sensitive", "anonymized", "not_personal"]
LEGAL_BASIS_OPTIONS = [
    "consent",
    "legitimate_interest",
    "legal_obligation",
    "contract_execution",
    "research",
    "not_determined",
]

_KNOWN_STATUS_VALUES = {"planned", "in_progress", "done", "blocked"}


# ---------------------------------------------------------------------------
# Funções puras — Visão geral (lê status/*.json direto do disco)
# ---------------------------------------------------------------------------

def get_repo_root() -> Path:
    """Raiz do repo, a partir da localização deste arquivo
    (apps/dashboard/app.py -> parents[2])."""
    return Path(__file__).resolve().parents[2]


def load_status_file(status_dir: Path, module_key: str) -> dict[str, Any] | None:
    """Lê `status/<module_key>.json`. Retorna `None` se o arquivo não existe
    ou não é um JSON válido — tolerante, nunca levanta exceção (a Visão geral
    não pode quebrar por causa de um módulo ainda não iniciado)."""
    path = status_dir / f"{module_key}.json"
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def load_all_statuses(
    status_dir: Path, modules: list[dict[str, str]] | None = None
) -> dict[str, dict[str, Any] | None]:
    """Mapa `module_key -> status dict (ou None)` para todos os módulos do V1."""
    modules = modules if modules is not None else V1_ROADMAP_MODULES
    return {m["key"]: load_status_file(status_dir, m["key"]) for m in modules}


def compute_v1_progress(statuses: dict[str, dict[str, Any] | None]) -> dict[str, Any]:
    """Agrega os status individuais num resumo de progresso do V1.

    Um módulo sem `status/<key>.json` ainda é contado, com status "planned"
    (ainda não iniciado) — mantém o total sempre igual ao nº de capacidades
    V1 do ROADMAP, mesmo antes de qualquer módulo escrever seu status.
    """
    counts = {"planned": 0, "in_progress": 0, "done": 0, "blocked": 0}
    tests_passed_total = 0
    tests_total_total = 0

    for data in statuses.values():
        if data is None:
            counts["planned"] += 1
            continue
        status = data.get("status")
        if status not in _KNOWN_STATUS_VALUES:
            status = "planned"
        counts[status] += 1
        tests_passed_total += int(data.get("tests_passed") or 0)
        tests_total_total += int(data.get("tests_total") or 0)

    total = len(statuses)
    done = counts["done"]
    percent_done = round((done / total) * 100, 1) if total else 0.0

    return {
        "total_modules": total,
        "counts": counts,
        "percent_done": percent_done,
        "tests_passed_total": tests_passed_total,
        "tests_total_total": tests_total_total,
    }


def status_badge(status: str | None) -> str:
    """Emoji + rótulo legível para um valor de `status`, seguindo a legenda
    do ROADMAP.md (⏳ planejado · 🔄 em andamento · ✅ concluído · ⚠️ bloqueado)."""
    mapping = {
        "planned": "⏳ planejado",
        "in_progress": "🔄 em andamento",
        "done": "✅ concluído",
        "blocked": "⚠️ bloqueado",
    }
    return mapping.get(status or "planned", "⏳ planejado")


def build_overview_rows(
    statuses: dict[str, dict[str, Any] | None],
    modules: list[dict[str, str]] | None = None,
) -> list[dict[str, Any]]:
    """Monta as linhas (uma por módulo V1) prontas para uma tabela na UI."""
    modules = modules if modules is not None else V1_ROADMAP_MODULES
    rows = []
    for m in modules:
        data = statuses.get(m["key"])
        status = (data or {}).get("status", "planned")
        rows.append(
            {
                "Capacidade": m["label"],
                "Pasta": m["folder"],
                "Status": status_badge(status),
                "Testes": (
                    f"{data.get('tests_passed', 0)}/{data.get('tests_total', 0)}"
                    if data
                    else "—"
                ),
                "Atualizado em": (data or {}).get("updated_at", "—"),
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Funções puras — formatação das respostas da API para exibição
# ---------------------------------------------------------------------------

def describe_client_error(exc: Exception) -> str:
    """Mensagem clara e amigável para exceções do `GovernanceCopilotClient`,
    usada na UI para não deixar o app quebrar quando a API está fora do ar."""
    if isinstance(exc, GovernanceCopilotConnectionError):
        return f"API do Governance Copilot indisponível. Detalhe: {exc}"
    if isinstance(exc, GovernanceCopilotHTTPError):
        return f"A API respondeu com erro HTTP {exc.status_code}: {exc.detail}"
    return f"Erro inesperado ao chamar a API: {exc}"


def pii_findings_to_rows(result: PIIDetectionResult) -> list[dict[str, Any]]:
    """`PIIDetectionResult.findings` -> linhas de tabela."""
    return [
        {
            "Tipo": f.entity_type,
            "Trecho": f.text_span,
            "Início": f.start,
            "Fim": f.end,
            "Categoria (LGPD Art. 5º)": f.category.value
            if hasattr(f.category, "value")
            else f.category,
            "Confiança": f.confidence,
        }
        for f in result.findings
    ]


def prompt_security_findings_to_rows(result: PromptSecurityResult) -> list[dict[str, Any]]:
    """`PromptSecurityResult.findings` -> linhas de tabela."""
    return [
        {
            "Técnica": f.technique,
            "Padrão detectado": f.matched_pattern,
            "Severidade": f.severity.value if hasattr(f.severity, "value") else f.severity,
        }
        for f in result.findings
    ]


def policy_decisions_to_rows(decisions: list[PolicyDecision]) -> list[dict[str, Any]]:
    """`list[PolicyDecision]` -> linhas de tabela."""
    return [
        {
            "Política": d.policy_id,
            "Decisão": d.status.value if hasattr(d.status, "value") else d.status,
            "Risco": d.risk_level.value if hasattr(d.risk_level, "value") else d.risk_level,
            "Justificativa": d.rationale,
            "Mitigações": "; ".join(d.mitigations) if d.mitigations else "—",
        }
        for d in decisions
    ]


def audit_events_to_rows(events: list[AuditEvent]) -> list[dict[str, Any]]:
    """`list[AuditEvent]` -> linhas de tabela."""
    return [
        {
            "ID": e.event_id,
            "Tipo": e.event_type.value if hasattr(e.event_type, "value") else e.event_type,
            "Timestamp": e.timestamp.isoformat() if hasattr(e.timestamp, "isoformat") else e.timestamp,
            "Ator": e.actor,
            "Hash": e.hash,
            "Hash anterior": e.prev_hash,
        }
        for e in events
    ]


def ripd_report_summary(report: RIPDReport) -> dict[str, Any]:
    """Resumo achatado de um `RIPDReport`, pronto para métricas/cards na UI."""
    return {
        "project_name": report.project_name,
        "generated_at": report.generated_at.isoformat()
        if hasattr(report.generated_at, "isoformat")
        else report.generated_at,
        "legal_basis": report.legal_basis.value
        if hasattr(report.legal_basis, "value")
        else report.legal_basis,
        "data_categories": [
            c.value if hasattr(c, "value") else c for c in report.data_categories
        ],
        "trust_score": report.trust_score.score,
        "trust_risk_level": report.trust_score.risk_level.value
        if hasattr(report.trust_score.risk_level, "value")
        else report.trust_score.risk_level,
        "pii_findings_count": len(report.pii_result.findings),
        "has_sensitive_data": report.pii_result.has_sensitive_data,
        "policy_decisions_count": len(report.policy_decisions),
        "denied_policies_count": sum(
            1
            for d in report.policy_decisions
            if (d.status.value if hasattr(d.status, "value") else d.status) == "deny"
        ),
        "mitigations_count": len(report.mitigations),
        "regulatory_context_count": len(report.regulatory_context),
        "executive_summary": report.executive_summary,
    }


def parse_multiline_categories(raw: str) -> list[str]:
    """Aceita um texto com categorias separadas por vírgula ou quebra de
    linha (fallback textual, caso a UI use um `text_area` em vez de
    `multiselect`) e devolve a lista limpa, sem itens vazios."""
    if not raw:
        return []
    parts = raw.replace("\n", ",").split(",")
    return [p.strip() for p in parts if p.strip()]


# ---------------------------------------------------------------------------
# Renderização Streamlit (não coberta por pytest — ver docstring do módulo)
# ---------------------------------------------------------------------------

def _get_client() -> "GovernanceCopilotClient":
    import streamlit as st

    base_url = st.session_state.get("api_base_url") or None
    return GovernanceCopilotClient(base_url=base_url)


def render_overview() -> None:
    import streamlit as st

    st.header("Visão geral — Progresso do Themis AI (ROADMAP V1)")
    st.caption(
        "Lida diretamente de `status/*.json` na raiz do repo — não depende "
        "da API do Governance Copilot estar no ar."
    )

    status_dir = get_repo_root() / "status"
    statuses = load_all_statuses(status_dir)
    progress = compute_v1_progress(statuses)

    col1, col2, col3 = st.columns(3)
    col1.metric("Capacidades V1 concluídas", f"{progress['counts']['done']}/{progress['total_modules']}")
    col2.metric("Progresso V1", f"{progress['percent_done']}%")
    col3.metric(
        "Testes verdes (agregado)",
        f"{progress['tests_passed_total']}/{progress['tests_total_total']}",
    )

    st.progress(progress["percent_done"] / 100)

    rows = build_overview_rows(statuses)
    st.table(rows)

    with st.expander("Notas por módulo"):
        for m in V1_ROADMAP_MODULES:
            data = statuses.get(m["key"])
            if data and data.get("notes"):
                st.markdown(f"**{m['label']}**: {data['notes']}")


def render_ripd_generator() -> None:
    import streamlit as st

    st.header("Gerador de RIPD")
    st.caption("Chama POST /api/v1/ripd/generate no Governance Copilot.")

    with st.form("ripd_form"):
        project_name = st.text_input("Nome do projeto")
        project_description = st.text_area("Descrição do projeto")
        data_categories = st.multiselect("Categorias de dado", DATA_CATEGORY_OPTIONS)
        legal_basis = st.selectbox("Base legal", LEGAL_BASIS_OPTIONS)
        submitted = st.form_submit_button("Gerar RIPD")

    if not submitted:
        return

    client = _get_client()
    try:
        report = client.generate_ripd(
            project_name=project_name,
            project_description=project_description,
            data_categories=data_categories,
            legal_basis=legal_basis,
        )
    except Exception as exc:  # GovernanceCopilotError e subclasses
        st.error(describe_client_error(exc))
        return

    summary = ripd_report_summary(report)
    st.success("RIPD gerado com sucesso.")
    col1, col2, col3 = st.columns(3)
    col1.metric("Trust Score", summary["trust_score"])
    col2.metric("Nível de risco", summary["trust_risk_level"])
    col3.metric("Achados de PII", summary["pii_findings_count"])

    st.subheader("Resumo executivo")
    st.write(summary["executive_summary"])

    st.subheader("Decisões de política")
    st.table(policy_decisions_to_rows(report.policy_decisions))

    st.subheader("Mitigações recomendadas")
    for m in report.mitigations:
        st.markdown(f"- {m}")

    st.subheader("JSON completo")
    st.json(report.model_dump(mode="json"))


def render_pii_scanner() -> None:
    import streamlit as st

    st.header("Scanner de PII")
    st.caption("Chama POST /api/v1/pii/detect no Governance Copilot.")

    text = st.text_area("Texto a analisar", key="pii_text")
    if not st.button("Detectar PII"):
        return

    client = _get_client()
    try:
        result = client.detect_pii(text)
    except Exception as exc:
        st.error(describe_client_error(exc))
        return

    if result.has_sensitive_data:
        st.warning(result.summary)
    else:
        st.info(result.summary)
    st.table(pii_findings_to_rows(result))


def render_prompt_security_scanner() -> None:
    import streamlit as st

    st.header("Scanner de Prompt Security")
    st.caption("Chama POST /api/v1/prompt-security/scan no Governance Copilot.")

    prompt = st.text_area("Prompt a analisar", key="prompt_security_text")
    if not st.button("Escanear prompt"):
        return

    client = _get_client()
    try:
        result = client.scan_prompt_security(prompt)
    except Exception as exc:
        st.error(describe_client_error(exc))
        return

    if result.is_safe:
        st.success(f"Prompt considerado seguro (score={result.score}).")
    else:
        st.error(f"Prompt considerado suspeito (score={result.score}).")
    st.table(prompt_security_findings_to_rows(result))


def render_audit() -> None:
    import streamlit as st

    st.header("Auditoria")
    st.caption(
        "Chama GET /api/v1/audit/verify e GET /api/v1/audit/events no "
        "Governance Copilot."
    )

    client = _get_client()

    try:
        verification = client.verify_audit()
    except Exception as exc:
        st.error(describe_client_error(exc))
        return

    if verification.get("valid"):
        st.success("Cadeia de auditoria (hash-chain) íntegra.")
    else:
        st.error("Cadeia de auditoria (hash-chain) INVÁLIDA — investigar.")

    limit = st.number_input("Nº de eventos", min_value=1, max_value=500, value=50)
    if not st.button("Carregar eventos"):
        return

    try:
        events = client.get_audit_events(limit=int(limit))
    except Exception as exc:
        st.error(describe_client_error(exc))
        return

    st.table(audit_events_to_rows(events))


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="Themis AI — Dashboard", layout="wide")
    st.sidebar.title("Themis AI")
    st.sidebar.text_input(
        "URL da API (Governance Copilot)",
        value="",
        placeholder="http://localhost:8000 (padrão)",
        key="api_base_url",
        help="Deixe em branco para usar THEMIS_API_URL ou o padrão.",
    )

    section = st.sidebar.radio(
        "Seção",
        [
            "Visão geral",
            "Gerador de RIPD",
            "Scanner de PII",
            "Scanner de Prompt Security",
            "Auditoria",
        ],
    )

    if section == "Visão geral":
        render_overview()
    elif section == "Gerador de RIPD":
        render_ripd_generator()
    elif section == "Scanner de PII":
        render_pii_scanner()
    elif section == "Scanner de Prompt Security":
        render_prompt_security_scanner()
    elif section == "Auditoria":
        render_audit()


if __name__ == "__main__":
    main()
