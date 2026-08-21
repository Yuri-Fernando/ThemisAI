# Changelog — Regulatory Sandbox

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Este módulo segue SemVer independente (`core/regulatory_sandbox/`).

## [0.1.0] - 2026-08-20

### Added

- `sandbox.py`:
  - `simulate(scenario: SandboxScenario) -> SandboxResult` — roda
    `policy_engine.evaluate` + `trust_score.compute_trust_score` reais em
    modo dry-run (NUNCA grava em `audit_logs` — diferença estrutural em
    relação ao `ripd_engine`, que sempre grava).
  - `compare_scenarios(scenario_a, scenario_b) -> SandboxComparison` — simula
    dois cenários e calcula `score_delta` + políticas que passam a se
    aplicar/deixam de se aplicar entre um cenário e outro.
- Contratos novos em `shared/schemas.py` (`SandboxScenario`, `SandboxResult`,
  `SandboxComparison`).
- Suíte de testes pytest (`tests/test_sandbox.py`, 7 testes): cenário de
  baixo risco; cenário de alto risco com `DENY` real; **prova explícita de
  ausência de efeito colateral** (contagem de eventos de `audit_logs` antes e
  depois de `simulate()` é idêntica); comparação mostra delta de score
  correto; decisões adicionadas/removidas; resumo menciona os nomes dos
  cenários; cenários idênticos têm delta zero.

### Notes

- Usa um `PIIDetectionResult` neutro fixo (nenhum PII avaliado) — o sandbox
  simula `data_categories`/`legal_basis`/`context` declarados, não escaneia
  texto de projeto (isso é responsabilidade do `pii_detection`/`ripd_engine`,
  fora de escopo de uma simulação puramente declarativa).
- Nenhuma lógica de política/score reimplementada — só orquestração real dos
  motores V1 em modo dry-run.
