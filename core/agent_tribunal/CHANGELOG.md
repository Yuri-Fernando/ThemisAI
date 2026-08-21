# Changelog — Agent Tribunal

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Este módulo segue SemVer independente (`core/agent_tribunal/`).

## [0.1.0] - 2026-08-20

### Added

- `tribunal.py`: `adjudicate(decisions: list[PolicyDecision]) ->
  TribunalVerdict`. Regra determinística de precedência ("a decisão mais
  restritiva vence": `DENY` > `REQUIRES_HUMAN_REVIEW` >
  `ALLOW_WITH_MITIGATION` > `ALLOW`; empate de status desempatado por
  `risk_level`). Fecha um TODO real deixado explicitamente por
  `policy_engine/CHANGELOG.md` no V1 ("não faz agregação/priorização entre
  PolicyDecision concorrentes — delegado ao governance_copilot").
- Contrato novo em `shared/schemas.py` (`TribunalVerdict`).
- Suíte de testes pytest (`tests/test_tribunal.py`, 7 testes): `DENY` vence
  tudo; `REQUIRES_HUMAN_REVIEW` vence `ALLOW_WITH_MITIGATION`; decisão única
  passa direto; empate de status desempatado por risco; lista vazia levanta
  erro; rationale menciona todas as políticas consideradas; **decisões reais
  concorrentes produzidas por `policy_engine.evaluate()`** (não só fixtures
  sintéticas) adjudicadas corretamente.

### Notes

- Regra de precedência é fixa nesta versão (não configurável) — se um caso
  de uso futuro precisar de pesos por política em vez de precedência fixa
  por status, é uma extensão, não uma correção.
