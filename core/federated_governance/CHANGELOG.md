# Changelog — Federated Governance

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Este módulo segue SemVer independente (`core/federated_governance/`).

## [0.1.0] - 2026-08-20

### Added

- `federation.py`:
  - `build_node_report(node_id, trust_scores) -> NodeReport` — agrega uma
    lista de `TrustScoreResult` (produzidos localmente dentro de um "nó")
    num resumo (`avg_trust_score`, `deny_count`, `risk_level_counts`). É o
    único artefato que sai do nó — nenhum `TrustScoreResult` individual
    cruza a fronteira.
  - `aggregate_federation(node_reports) -> FederatedSummary` — combina
    `NodeReport`s já agregados numa visão global (média ponderada pelo
    volume de cada nó, total de `DENY`, nó com melhor/pior score médio).
- Contratos novos em `shared/schemas.py` (`NodeReport`, `FederatedSummary`).
- Suíte de testes pytest (`tests/test_federation.py`, 8 testes): agregação
  correta por nó; nó vazio levanta erro; **`NodeReport` construído a partir
  de um `TrustScoreResult` REAL** (via `policy_engine.evaluate` +
  `trust_score.compute_trust_score`, não só fixture sintética); média
  ponderada correta entre nós de tamanhos diferentes; totais corretos;
  federação vazia levanta erro; resumo menciona nó melhor/pior; federação de
  um único nó.

### Notes

- Padrão real de "governança federada": a organização central nunca vê os
  scores individuais de decisão de cada filial/subsidiária, só os agregados
  que cada nó decidiu expor — compatível com cenários de jurisdições/bases
  legais diferentes por unidade, sem compartilhar dado granular.
- `deny_count` usa o piso documentado de `trust_score` (`score <= 5.0` ==
  veto de política `DENY`) como proxy — não reimporta `PolicyDecisionStatus`
  diretamente porque `NodeReport` só recebe `TrustScoreResult` (o contrato
  deliberadamente mínimo que cruza a fronteira do nó).
