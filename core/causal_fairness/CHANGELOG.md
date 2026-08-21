# Changelog — Causal Fairness

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Este módulo segue SemVer independente (`core/causal_fairness/`).

## [0.1.0] - 2026-08-21

### Added

- Extração real do item "Causal AI Governance" do V3.
- `stratified.py`: `stratified_fairness_audit(records, outcome_key,
  protected_attribute_key, confound_key, ...) -> StratifiedFairnessResult`
  — reusa `fairness_audit.audit_fairness()` (V2) real, agregado e por
  estrato de `confound_key`, e detecta **Paradoxo de Simpson** (veredito
  agregado diverge do veredito em algum estrato).
- Contratos novos em `shared/schemas.py` (`StratumResult`,
  `StratifiedFairnessResult`).
- Suíte de testes pytest (`tests/test_stratified.py`, 6 testes), incluindo
  o **exemplo clássico estilo Berkeley** (construído no teste): agregado
  mostra forte disparidade contra um grupo (~81% vs ~19%, reprovado na
  regra dos 80%), mas cada estrato individual mostra o grupo com taxa igual
  ou maior — paradoxo real e corretamente detectado.

### Notes

- **Escopo honesto**: isto é o PRIMEIRO sintoma que motivaria investigação
  causal mais profunda, não inferência causal completa. Um grafo causal
  (DAG) explícito, matching, ou variáveis instrumentais exigiriam modelar o
  domínio de negócio — fora de escopo desta extração. Ver
  `docs/architecture/v3-frontier-research.md`.
