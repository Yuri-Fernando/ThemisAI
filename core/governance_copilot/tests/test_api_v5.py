"""Testes dos itens do plano de melhorias (V5) integrados na API real do
Governance Copilot — autenticação, CORS, enforcement, observabilidade,
trilha de auditoria por trace_id, persistência de RIPD, checagem de saúde
sob demanda. Mesmo padrão dos demais testes deste módulo: TestClient real,
sem mocks.
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import pytest
from fastapi.testclient import TestClient

from core.governance_copilot.api import app
from core.governance_copilot.auth import ENV_VAR_API_KEY
from core.regulatory_rag.index import DEFAULT_DATA_DIR, build_index


@pytest.fixture(scope="session", autouse=True)
def _ensure_regulatory_index_built() -> None:
    has_index = DEFAULT_DATA_DIR.exists() and any(DEFAULT_DATA_DIR.glob("*.sqlite3"))
    if not has_index:
        build_index()
    from core.regulatory_rag.index import query as _warmup_query

    _warmup_query("aquecimento", k=1)


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


# ---------------------------------------------------------------------------
# Item 3 — autenticação por API key (desabilitada por padrão)
# ---------------------------------------------------------------------------

def test_no_api_key_required_by_default(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_VAR_API_KEY, raising=False)
    response = client.get("/api/v1/audit/verify")
    assert response.status_code == 200


def test_api_key_enforced_when_env_var_set(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_VAR_API_KEY, "segredo-de-teste")
    response = client.get("/api/v1/audit/verify")
    assert response.status_code == 401

    response_ok = client.get("/api/v1/audit/verify", headers={"X-API-Key": "segredo-de-teste"})
    assert response_ok.status_code == 200


def test_wrong_api_key_rejected(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_VAR_API_KEY, "segredo-certo")
    response = client.get("/api/v1/audit/verify", headers={"X-API-Key": "segredo-errado"})
    assert response.status_code == 401


def test_health_never_requires_api_key(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_VAR_API_KEY, "segredo-de-teste")
    response = client.get("/health")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Item 3 — CORS
# ---------------------------------------------------------------------------

def test_cors_header_present(client: TestClient) -> None:
    response = client.get("/health", headers={"Origin": "https://example.test"})
    assert response.headers.get("access-control-allow-origin") == "*"


# ---------------------------------------------------------------------------
# Item 7 — enforcement real via @enforce
# ---------------------------------------------------------------------------

def test_all_endpoints_still_authorized_by_default_agents(client: TestClient) -> None:
    # Os agent_id usados nos handlers (ripd_generator, auditor) já estão
    # todos autorizados em agents.yaml para as ações que cada endpoint usa
    # -- prova de que a autorização real não quebrou nenhum fluxo existente.
    assert client.get("/api/v1/audit/verify").status_code == 200
    assert client.post("/api/v1/pii/detect", json={"text": "oi"}).status_code == 200
    assert client.post("/api/v1/prompt-security/scan", json={"prompt": "oi"}).status_code == 200
    assert client.post(
        "/api/v1/policy/evaluate", json={"data_categories": ["not_personal"], "legal_basis": "not_determined"}
    ).status_code == 200


# ---------------------------------------------------------------------------
# Item 8 — GET /metrics real
# ---------------------------------------------------------------------------

def test_metrics_endpoint_reflects_real_calls(client: TestClient) -> None:
    client.post("/api/v1/pii/detect", json={"text": "sem PII aqui"})
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "themis_module_calls_total" in response.text
    assert 'module="pii_detection"' in response.text


# ---------------------------------------------------------------------------
# Item 6 — trilha de auditoria por trace_id
# ---------------------------------------------------------------------------

def test_pii_detect_generates_traceable_event(client: TestClient) -> None:
    from core.audit_logs.logger import default_logger

    events_before = len(default_logger().read_events())
    response = client.post("/api/v1/pii/detect", json={"text": "CPF 111.444.777-35"})
    assert response.status_code == 200

    events_after = default_logger().read_events()
    assert len(events_after) == events_before + 1
    trace_id = events_after[-1].payload["trace_id"]

    trace_response = client.get(f"/api/v1/audit/trace/{trace_id}")
    assert trace_response.status_code == 200
    trace = trace_response.json()
    assert len(trace["event_ids"]) == 1


def test_prompt_security_scan_generates_traceable_event(client: TestClient) -> None:
    from core.audit_logs.logger import default_logger

    events_before = len(default_logger().read_events())
    client.post("/api/v1/prompt-security/scan", json={"prompt": "oi"})
    events_after = default_logger().read_events()
    assert len(events_after) == events_before + 1
    assert events_after[-1].event_type.value == "prompt_security_scan"


def test_policy_evaluate_generates_traceable_event(client: TestClient) -> None:
    from core.audit_logs.logger import default_logger

    events_before = len(default_logger().read_events())
    client.post("/api/v1/policy/evaluate", json={"data_categories": ["not_personal"], "legal_basis": "not_determined"})
    events_after = default_logger().read_events()
    assert len(events_after) == events_before + 1
    assert events_after[-1].event_type.value == "policy_evaluation"


def test_unknown_trace_id_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/audit/trace/id-que-nunca-existiu")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Item 4 — fila de revisão humana alimentada automaticamente
# ---------------------------------------------------------------------------

def test_ripd_generate_auto_enqueues_human_review(client: TestClient) -> None:
    response = client.post(
        "/api/v1/ripd/generate",
        json={
            "project_name": "Score de crédito automatizado sem revisão",
            "project_description": "Decide crédito automaticamente.",
            "data_categories": ["sensitive"],
            "legal_basis": "not_determined",
            "context": {"data_subtype": "biometric", "automated_decision": True, "human_review": False},
        },
    )
    assert response.status_code == 200
    item_ids_header = response.headers.get("X-Human-Review-Item-Ids")
    assert item_ids_header  # ao menos um item enfileirado (POL-008 exige revisão)

    from core.governance_copilot import api as api_module

    all_ids = {item.item_id for item in api_module._oversight_queue.list_items()}
    for item_id in item_ids_header.split(","):
        assert item_id in all_ids


def test_ripd_generate_low_risk_does_not_enqueue(client: TestClient) -> None:
    response = client.post(
        "/api/v1/ripd/generate",
        json={
            "project_name": "Chatbot de baixo risco V5",
            "project_description": "Responde perguntas simples.",
            "data_categories": ["personal"],
            "legal_basis": "legitimate_interest",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("X-Human-Review-Item-Ids") is None


# ---------------------------------------------------------------------------
# Item 14 — RIPD persistido e consultável
# ---------------------------------------------------------------------------

def test_ripd_generate_persists_and_is_retrievable(client: TestClient) -> None:
    response = client.post(
        "/api/v1/ripd/generate",
        json={
            "project_name": "Projeto persistido V5",
            "project_description": "Descrição neutra.",
            "data_categories": ["not_personal"],
            "legal_basis": "not_determined",
        },
    )
    assert response.status_code == 200
    ripd_id = response.headers["X-RIPD-Id"]

    get_response = client.get(f"/api/v1/ripd/{ripd_id}")
    assert get_response.status_code == 200
    assert get_response.json()["project_name"] == "Projeto persistido V5"


def test_ripd_list_includes_generated_summary(client: TestClient) -> None:
    response = client.post(
        "/api/v1/ripd/generate",
        json={
            "project_name": "Projeto listado V5",
            "project_description": "Descrição neutra.",
            "data_categories": ["not_personal"],
            "legal_basis": "not_determined",
        },
    )
    ripd_id = response.headers["X-RIPD-Id"]

    list_response = client.get("/api/v1/ripd")
    assert list_response.status_code == 200
    ids = {item["ripd_id"] for item in list_response.json()}
    assert ripd_id in ids


def test_get_unknown_ripd_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/ripd/id-que-nunca-existiu")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Item 5 — checagem de saúde sob demanda
# ---------------------------------------------------------------------------

def test_health_check_run_real_check(client: TestClient) -> None:
    from core.audit_logs.logger import default_logger

    healthy = default_logger().verify_chain()
    response = client.post("/api/v1/health-check/run", json={"checks": {"audit_chain_integrity": healthy}})
    assert response.status_code == 200
    actions = response.json()
    assert actions[0]["healthy"] == healthy
