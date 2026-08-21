"""Testes do Multi-Agent Governance — registro declarativo real (agents.yaml)."""
from __future__ import annotations

from core.multi_agent_governance.registry import authorize, list_agents
from shared.schemas import AgentRole, AuthorizationResult, RiskLevel


def test_list_agents_returns_all_five():
    agents = list_agents()
    assert len(agents) == 5
    assert all(isinstance(a, AgentRole) for a in agents)


def test_authorize_allowed_action():
    result = authorize("auditor", "audit_logs.verify_chain")
    assert isinstance(result, AuthorizationResult)
    assert result.authorized is True


def test_authorize_disallowed_action():
    result = authorize("reviewer", "policy_engine.evaluate")
    assert result.authorized is False
    assert "NÃO está" in result.reason


def test_authorize_unknown_agent():
    result = authorize("agente-inexistente", "qualquer.acao")
    assert result.authorized is False
    assert "não está registrado" in result.reason


def test_red_teamer_can_run_suite_but_not_evaluate_policy():
    can_run = authorize("red_teamer", "red_team_lab.run_suite")
    cannot_evaluate = authorize("red_teamer", "policy_engine.evaluate")
    assert can_run.authorized is True
    assert cannot_evaluate.authorized is False


def test_custom_registry_path(tmp_path):
    custom = tmp_path / "custom_agents.yaml"
    custom.write_text(
        """
agents:
  - agent_id: "custom_agent"
    name: "Agente Customizado"
    allowed_actions:
      - "custom.action"
    risk_tier: low
""",
        encoding="utf-8",
    )
    agents = list_agents(registry_path=custom)
    assert len(agents) == 1
    assert agents[0].agent_id == "custom_agent"

    result = authorize("custom_agent", "custom.action", registry_path=custom)
    assert result.authorized is True


def test_risk_tier_is_risklevel_enum():
    agents = list_agents()
    red_teamer = next(a for a in agents if a.agent_id == "red_teamer")
    assert red_teamer.risk_tier == RiskLevel.HIGH
