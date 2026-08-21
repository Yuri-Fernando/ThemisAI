"""Testes do Runtime Policy Enforcement — decorator real contra o registro
real de multi_agent_governance (V2), sem mock."""
from __future__ import annotations

import pytest

from core.runtime_policy_enforcement.enforcement import EnforcementError, enforce


def test_authorized_call_runs_normally():
    calls = []

    @enforce(agent_id="auditor", action="audit_logs.verify_chain")
    def do_verify():
        calls.append("ran")
        return "ok"

    result = do_verify()
    assert result == "ok"
    assert calls == ["ran"]


def test_unauthorized_call_raises_and_never_runs_body():
    calls = []

    @enforce(agent_id="reviewer", action="policy_engine.evaluate")
    def do_evaluate():
        calls.append("ran")  # NÃO deveria ser alcançado
        return "should not happen"

    with pytest.raises(EnforcementError):
        do_evaluate()
    assert calls == []  # prova real de que o corpo nunca executou


def test_enforcement_error_is_permission_error():
    @enforce(agent_id="agente-inexistente", action="qualquer.acao")
    def fn():
        return None

    with pytest.raises(PermissionError):  # captura genérica também funciona
        fn()


def test_enforcement_error_carries_context():
    @enforce(agent_id="reviewer", action="policy_engine.evaluate")
    def fn():
        return None

    with pytest.raises(EnforcementError) as exc_info:
        fn()
    assert exc_info.value.agent_id == "reviewer"
    assert exc_info.value.action == "policy_engine.evaluate"
    assert "NÃO está" in exc_info.value.reason


def test_decorator_preserves_function_metadata():
    @enforce(agent_id="auditor", action="audit_logs.verify_chain")
    def minha_funcao_com_docstring():
        """Docstring original."""
        return None

    assert minha_funcao_com_docstring.__name__ == "minha_funcao_com_docstring"
    assert minha_funcao_com_docstring.__doc__ == "Docstring original."


def test_decorator_passes_args_and_kwargs_through():
    @enforce(agent_id="auditor", action="audit_logs.verify_chain")
    def soma(a, b, fator=1):
        return (a + b) * fator

    assert soma(2, 3, fator=10) == 50


def test_custom_registry_path(tmp_path):
    custom = tmp_path / "agents.yaml"
    custom.write_text(
        """
agents:
  - agent_id: "custom"
    name: "Agente Customizado"
    allowed_actions: ["custom.action"]
    risk_tier: low
""",
        encoding="utf-8",
    )

    @enforce(agent_id="custom", action="custom.action", registry_path=custom)
    def fn():
        return "ok"

    assert fn() == "ok"

    @enforce(agent_id="custom", action="acao.nao.permitida", registry_path=custom)
    def fn2():
        return "ok"

    with pytest.raises(EnforcementError):
        fn2()
