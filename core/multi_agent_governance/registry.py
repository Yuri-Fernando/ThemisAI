"""Multi-Agent Governance — registro declarativo (`agents.yaml`) de quais
agentes existem no Themis AI e quais ações cada um está autorizado a
executar. `authorize()` é a função central: um orquestrador (ex.
`governance_copilot`) chama isso antes de repassar uma ação a um agente, e
decide o que fazer com o resultado (bloquear ou prosseguir) — este módulo
não intercepta chamadas de verdade (não há reflexão amarrando isso a funções
Python reais), é uma checagem declarativa explícita, do mesmo estilo de
`policy_engine`.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from shared.schemas import AgentRole, AuthorizationResult, RiskLevel

_DEFAULT_REGISTRY_PATH = Path(__file__).parent / "agents.yaml"


def _load_agents(registry_path: Path | str | None = None) -> list[dict]:
    path = Path(registry_path) if registry_path else _DEFAULT_REGISTRY_PATH
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not data:
        return []
    return data.get("agents", [])


def list_agents(registry_path: Path | str | None = None) -> list[AgentRole]:
    """Lista todos os agentes declarados no registro."""
    return [
        AgentRole(
            agent_id=a["agent_id"],
            name=a["name"],
            allowed_actions=list(a.get("allowed_actions", [])),
            risk_tier=RiskLevel(a["risk_tier"]),
        )
        for a in _load_agents(registry_path)
    ]


def authorize(agent_id: str, action: str, registry_path: Path | str | None = None) -> AuthorizationResult:
    """Verifica se `agent_id` está autorizado a executar `action`.

    Returns:
        `AuthorizationResult.authorized = True` se `action` está na lista
        `allowed_actions` do agente; `False` caso contrário — inclusive se
        `agent_id` não existir no registro (com `reason` explicando o
        motivo em cada caso).
    """
    agents = {a.agent_id: a for a in list_agents(registry_path)}

    if agent_id not in agents:
        return AuthorizationResult(
            agent_id=agent_id,
            action=action,
            authorized=False,
            reason=f"Agente '{agent_id}' não está registrado em agents.yaml.",
        )

    agent = agents[agent_id]
    if action in agent.allowed_actions:
        return AuthorizationResult(
            agent_id=agent_id,
            action=action,
            authorized=True,
            reason=f"Ação '{action}' está na lista de ações permitidas do agente '{agent.name}'.",
        )

    return AuthorizationResult(
        agent_id=agent_id,
        action=action,
        authorized=False,
        reason=f"Ação '{action}' NÃO está na lista de ações permitidas do agente '{agent.name}'.",
    )
