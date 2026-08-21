# Changelog — Policy Engine

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Este módulo segue SemVer independente (`core/policy_engine/`).

## [0.1.0] - 2026-08-19

### Added

- `policies.yaml`: base declarativa com 9 políticas LGPD para IA, cada uma com
  `trigger` (condições de aplicabilidade) e `outcomes` ordenados (branching real por
  base legal e sinais de contexto), cobrindo:
  - POL-001: dado de saúde exige consentimento explícito + RIPD.
  - POL-002: dado biométrico é alto risco (decisão automatizada sem revisão humana é vedada).
  - POL-003: dado de menor de idade exige consentimento do responsável legal (Art. 14).
  - POL-004: transferência internacional sem cláusula de adequação exige revisão humana (Art. 33).
  - POL-005: dado anonimizado é liberado (Art. 12).
  - POL-006: decisão totalmente automatizada com efeito jurídico exige explicabilidade (Art. 20).
  - POL-007: finalidade não especificada é negada (Art. 6º, I).
  - POL-008: base legal não determinada exige revisão humana.
  - POL-009: dado pessoal comum com base legal e finalidade definidas é liberado (baseline).
- `engine.py`: função pública `evaluate(data_categories, legal_basis, context=None,
  policies_path=None) -> list[PolicyDecision]`. Carrega `policies.yaml`, casa cada
  política contra o cenário informado e retorna todas as decisões aplicáveis (mais de
  uma política pode disparar para o mesmo cenário, ex. menor + dado de saúde).
- `__init__.py`: torna `core/policy_engine` um pacote Python válido e reexporta `evaluate`.
- Suíte de testes pytest (`tests/test_engine.py`) cobrindo: cada uma das 9 políticas,
  os 4 valores de `PolicyDecisionStatus`, decisões simultâneas de múltiplas políticas,
  o caso de borda "nenhuma política aplicável", robustez de contrato (`context=None`,
  Enums vs. strings cruas) e um caminho de `policies.yaml` customizado via `tmp_path`.

### Notes

- Tipos consumidos diretamente de `shared/schemas.py` (`PolicyDecision`,
  `PolicyDecisionStatus`, `DataCategory`, `LegalBasis`, `RiskLevel`) — nenhum tipo
  redefinido neste módulo, conforme regra de contrato compartilhado do projeto.
- `context` é um dicionário livre; o vocabulário de chaves reconhecidas pelas 9
  políticas atuais está documentado no cabeçalho de `policies.yaml`.
- TODO (V2): motor de política atual é puramente declarativo/determinístico (sem
  aprendizado, sem priorização por severidade entre decisões concorrentes). Agregação
  final de múltiplas `PolicyDecision` (ex.: "qual status vence quando há DENY e
  ALLOW_WITH_MITIGATION simultâneos") é responsabilidade do `governance_copilot`, não
  deste módulo — este módulo apenas relata todas as decisões aplicáveis.
