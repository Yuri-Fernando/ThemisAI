# Changelog — Multi-Agent Governance

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Este módulo segue SemVer independente (`core/multi_agent_governance/`).

## [0.1.1] - 2026-08-21 — Integração real via governance_copilot (V5, item 7)

### Changed
- `agents.yaml`: `ripd_generator` ganhou as ações `ripd_engine.generate_ripd`
  e `governance_copilot.ripd_store`; `auditor` ganhou
  `ai_observability.export` e `self_healing_governance.check_and_heal` —
  necessárias para o `core/governance_copilot/api.py` decorar todos os seus
  endpoints com `@enforce` (`runtime_policy_enforcement`, V3) sem quebrar
  nenhum fluxo existente.

### Notes
- O TODO "integração automática via decorator" da v0.1.0 foi resolvido —
  ver `core/runtime_policy_enforcement` (extração real de V3) e
  `core/governance_copilot/CHANGELOG.md` `[0.2.0]` para o uso real em
  produção (todo endpoint da API agora passa por `authorize()` de verdade,
  não mais só consultivo).

## [0.1.0] - 2026-08-20

### Added

- `agents.yaml`: registro declarativo de 5 agentes lógicos do Themis AI
  (`ripd_generator`, `auditor`, `red_teamer`, `reviewer`, `sandbox_explorer`)
  e as ações que cada um pode executar.
- `registry.py`: `authorize(agent_id, action) -> AuthorizationResult` e
  `list_agents() -> list[AgentRole]`.
- Contratos novos em `shared/schemas.py` (`AgentRole`, `AuthorizationResult`).
- Suíte de testes pytest (`tests/test_registry.py`, 7 testes): listagem;
  ação permitida/negada; agente desconhecido; registro customizado; enum de
  `risk_tier`.

### Notes

- **Escopo honesto**: `authorize()` é uma checagem declarativa explícita, não
  um interceptor real de chamadas Python (sem reflexão/decorators amarrando
  isso a funções de outros módulos automaticamente) — quem orquestra (ex.
  `governance_copilot`) decide chamar `authorize()` antes de agir e o que
  fazer com o resultado. TODO onda futura: integração automática via
  decorator.
