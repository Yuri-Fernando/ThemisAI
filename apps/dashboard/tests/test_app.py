"""Testes das funções puras de `apps/dashboard/app.py` (leitura de
`status/*.json` e formatação das respostas da API para a UI).

Deliberadamente NÃO testamos as funções `render_*`/`main` — elas chamam
`streamlit.*` e não rodam de forma significativa fora de `streamlit run`.
Toda a lógica de negócio não trivial que elas usam foi extraída para as
funções puras testadas aqui.
"""
from __future__ import annotations

import json
from datetime import datetime

import pytest

from apps.dashboard.app import (
    audit_events_to_rows,
    build_overview_rows,
    compute_v1_progress,
    describe_client_error,
    load_all_statuses,
    load_status_file,
    parse_multiline_categories,
    pii_findings_to_rows,
    policy_decisions_to_rows,
    prompt_security_findings_to_rows,
    ripd_report_summary,
    status_badge,
)
from apps.dashboard.client import (
    GovernanceCopilotConnectionError,
    GovernanceCopilotHTTPError,
)
from shared.schemas import (
    AuditEvent,
    AuditEventType,
    DataCategory,
    ExplainabilityResult,
    LegalBasis,
    PIIDetectionResult,
    PIIFinding,
    PolicyDecision,
    PolicyDecisionStatus,
    PromptSecurityFinding,
    PromptSecurityResult,
    RegulatoryChunk,
    RIPDReport,
    RiskLevel,
    TrustScoreResult,
)

TEST_MODULES = [
    {"key": "mod_a", "label": "Módulo A", "folder": "core/mod_a/"},
    {"key": "mod_b", "label": "Módulo B", "folder": "core/mod_b/"},
    {"key": "mod_c", "label": "Módulo C", "folder": "core/mod_c/"},
]


# ---------------------------------------------------------------------------
# load_status_file / load_all_statuses / compute_v1_progress
# ---------------------------------------------------------------------------

def test_load_status_file_returns_none_when_missing(tmp_path):
    assert load_status_file(tmp_path, "does_not_exist") is None


def test_load_status_file_returns_none_on_invalid_json(tmp_path):
    (tmp_path / "broken.json").write_text("{not valid json", encoding="utf-8")
    assert load_status_file(tmp_path, "broken") is None


def test_load_status_file_returns_none_when_json_is_not_an_object(tmp_path):
    (tmp_path / "list_module.json").write_text("[1, 2, 3]", encoding="utf-8")
    assert load_status_file(tmp_path, "list_module") is None


def test_load_status_file_returns_parsed_dict_when_valid(tmp_path):
    payload = {"module": "mod_a", "status": "done", "tests_total": 5, "tests_passed": 5}
    (tmp_path / "mod_a.json").write_text(json.dumps(payload), encoding="utf-8")
    assert load_status_file(tmp_path, "mod_a") == payload


def test_load_all_statuses_maps_every_module_key(tmp_path):
    payload = {"module": "mod_a", "status": "done"}
    (tmp_path / "mod_a.json").write_text(json.dumps(payload), encoding="utf-8")

    result = load_all_statuses(tmp_path, modules=TEST_MODULES)

    assert set(result.keys()) == {"mod_a", "mod_b", "mod_c"}
    assert result["mod_a"] == payload
    assert result["mod_b"] is None
    assert result["mod_c"] is None


def test_compute_v1_progress_counts_missing_modules_as_planned():
    statuses = {"mod_a": None, "mod_b": None, "mod_c": None}
    progress = compute_v1_progress(statuses)

    assert progress["total_modules"] == 3
    assert progress["counts"] == {"planned": 3, "in_progress": 0, "done": 0, "blocked": 0}
    assert progress["percent_done"] == 0.0
    assert progress["tests_passed_total"] == 0
    assert progress["tests_total_total"] == 0


def test_compute_v1_progress_aggregates_mixed_statuses():
    statuses = {
        "mod_a": {"status": "done", "tests_total": 25, "tests_passed": 25},
        "mod_b": {"status": "in_progress", "tests_total": 10, "tests_passed": 7},
        "mod_c": None,  # ainda sem status/*.json => planned
    }
    progress = compute_v1_progress(statuses)

    assert progress["total_modules"] == 3
    assert progress["counts"] == {"planned": 1, "in_progress": 1, "done": 1, "blocked": 0}
    assert progress["percent_done"] == pytest.approx(33.3)
    assert progress["tests_passed_total"] == 32
    assert progress["tests_total_total"] == 35


def test_compute_v1_progress_treats_unknown_status_value_as_planned():
    statuses = {"mod_a": {"status": "some_future_status"}}
    progress = compute_v1_progress(statuses)
    assert progress["counts"]["planned"] == 1


def test_compute_v1_progress_handles_empty_statuses_without_division_error():
    progress = compute_v1_progress({})
    assert progress["total_modules"] == 0
    assert progress["percent_done"] == 0.0


# ---------------------------------------------------------------------------
# status_badge / build_overview_rows
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "status,expected_substring",
    [
        ("done", "concluído"),
        ("in_progress", "andamento"),
        ("blocked", "bloqueado"),
        ("planned", "planejado"),
        (None, "planejado"),
        ("unrecognized", "planejado"),
    ],
)
def test_status_badge(status, expected_substring):
    assert expected_substring in status_badge(status)


def test_build_overview_rows_with_and_without_data():
    statuses = {
        "mod_a": {
            "status": "done",
            "tests_total": 25,
            "tests_passed": 25,
            "updated_at": "2026-08-19T00:00:00",
        },
        "mod_b": None,
        "mod_c": None,
    }
    rows = build_overview_rows(statuses, modules=TEST_MODULES)

    assert len(rows) == 3
    assert rows[0]["Capacidade"] == "Módulo A"
    assert rows[0]["Testes"] == "25/25"
    assert rows[0]["Atualizado em"] == "2026-08-19T00:00:00"
    assert rows[1]["Testes"] == "—"
    assert rows[1]["Atualizado em"] == "—"


# ---------------------------------------------------------------------------
# describe_client_error
# ---------------------------------------------------------------------------

def test_describe_client_error_for_connection_error():
    exc = GovernanceCopilotConnectionError("API fora do ar")
    message = describe_client_error(exc)
    assert "indisponível" in message
    assert "API fora do ar" in message


def test_describe_client_error_for_http_error():
    exc = GovernanceCopilotHTTPError(500, "internal error", "http://x/api")
    message = describe_client_error(exc)
    assert "500" in message
    assert "internal error" in message


def test_describe_client_error_for_generic_exception():
    exc = ValueError("algo inesperado")
    message = describe_client_error(exc)
    assert "inesperado" in message
    assert "algo inesperado" in message


# ---------------------------------------------------------------------------
# Formatação de respostas da API (linhas de tabela / resumos)
# ---------------------------------------------------------------------------

def test_pii_findings_to_rows():
    result = PIIDetectionResult(
        findings=[
            PIIFinding(
                entity_type="CPF",
                text_span="111.444.777-35",
                start=0,
                end=15,
                category=DataCategory.PERSONAL,
                confidence=0.98,
            )
        ],
        has_sensitive_data=False,
        summary="1 achado(s)",
    )
    rows = pii_findings_to_rows(result)
    assert rows == [
        {
            "Tipo": "CPF",
            "Trecho": "111.444.777-35",
            "Início": 0,
            "Fim": 15,
            "Categoria (LGPD Art. 5º)": "personal",
            "Confiança": 0.98,
        }
    ]


def test_prompt_security_findings_to_rows():
    result = PromptSecurityResult(
        findings=[
            PromptSecurityFinding(
                technique="jailbreak",
                matched_pattern="DAN mode",
                severity=RiskLevel.HIGH,
            )
        ],
        is_safe=False,
        score=0.1,
    )
    rows = prompt_security_findings_to_rows(result)
    assert rows == [
        {"Técnica": "jailbreak", "Padrão detectado": "DAN mode", "Severidade": "high"}
    ]


def test_policy_decisions_to_rows():
    decisions = [
        PolicyDecision(
            policy_id="POL-1",
            status=PolicyDecisionStatus.DENY,
            rationale="Base legal ausente",
            mitigations=[],
            risk_level=RiskLevel.CRITICAL,
        ),
        PolicyDecision(
            policy_id="POL-2",
            status=PolicyDecisionStatus.ALLOW_WITH_MITIGATION,
            rationale="Requer anonimização",
            mitigations=["Anonimizar", "Registrar consentimento"],
            risk_level=RiskLevel.MEDIUM,
        ),
    ]
    rows = policy_decisions_to_rows(decisions)
    assert rows[0]["Mitigações"] == "—"
    assert rows[1]["Mitigações"] == "Anonimizar; Registrar consentimento"
    assert rows[0]["Decisão"] == "deny"
    assert rows[1]["Risco"] == "medium"


def test_audit_events_to_rows():
    events = [
        AuditEvent(
            event_id="evt-1",
            event_type=AuditEventType.PII_SCAN,
            timestamp=datetime(2026, 8, 19, 10, 0, 0),
            actor="dashboard",
            payload={"found": 1},
            prev_hash="0" * 64,
            hash="a" * 64,
        )
    ]
    rows = audit_events_to_rows(events)
    assert rows[0]["ID"] == "evt-1"
    assert rows[0]["Tipo"] == "pii_scan"
    assert rows[0]["Timestamp"] == "2026-08-19T10:00:00"
    assert rows[0]["Ator"] == "dashboard"
    assert rows[0]["Hash"] == "a" * 64


def test_ripd_report_summary():
    report = RIPDReport(
        project_name="Projeto X",
        generated_at=datetime(2026, 8, 19, 12, 0, 0),
        data_categories=[DataCategory.PERSONAL, DataCategory.SENSITIVE],
        legal_basis=LegalBasis.CONSENT,
        pii_result=PIIDetectionResult(
            findings=[
                PIIFinding(
                    entity_type="CPF",
                    text_span="x",
                    start=0,
                    end=1,
                    category=DataCategory.PERSONAL,
                    confidence=0.9,
                )
            ],
            has_sensitive_data=True,
            summary="1 achado",
        ),
        policy_decisions=[
            PolicyDecision(
                policy_id="POL-1",
                status=PolicyDecisionStatus.DENY,
                rationale="r",
                mitigations=[],
                risk_level=RiskLevel.HIGH,
            ),
            PolicyDecision(
                policy_id="POL-2",
                status=PolicyDecisionStatus.ALLOW,
                rationale="r2",
                mitigations=[],
                risk_level=RiskLevel.LOW,
            ),
        ],
        prompt_security=None,
        trust_score=TrustScoreResult(
            score=42.0,
            risk_level=RiskLevel.HIGH,
            components={"a": 1.0},
            explanation=ExplainabilityResult(subject="trust_score", factors={}, narrative="n"),
        ),
        regulatory_context=[
            RegulatoryChunk(source="LGPD", article="Art. 5º", text="...", score=0.8)
        ],
        mitigations=["Mitigação 1"],
        executive_summary="Resumo executivo do projeto X.",
    )

    summary = ripd_report_summary(report)

    assert summary["project_name"] == "Projeto X"
    assert summary["generated_at"] == "2026-08-19T12:00:00"
    assert summary["legal_basis"] == "consent"
    assert summary["data_categories"] == ["personal", "sensitive"]
    assert summary["trust_score"] == 42.0
    assert summary["trust_risk_level"] == "high"
    assert summary["pii_findings_count"] == 1
    assert summary["has_sensitive_data"] is True
    assert summary["policy_decisions_count"] == 2
    assert summary["denied_policies_count"] == 1
    assert summary["mitigations_count"] == 1
    assert summary["regulatory_context_count"] == 1
    assert summary["executive_summary"] == "Resumo executivo do projeto X."


# ---------------------------------------------------------------------------
# parse_multiline_categories
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("", []),
        (None, []),
        ("personal", ["personal"]),
        ("personal, sensitive", ["personal", "sensitive"]),
        ("personal\nsensitive\n", ["personal", "sensitive"]),
        ("personal,, sensitive,   ", ["personal", "sensitive"]),
    ],
)
def test_parse_multiline_categories(raw, expected):
    assert parse_multiline_categories(raw) == expected
