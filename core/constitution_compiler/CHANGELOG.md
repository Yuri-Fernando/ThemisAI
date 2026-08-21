# Changelog — AI Constitution Compiler

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Este módulo segue SemVer independente (`core/constitution_compiler/`).

## [0.1.0] - 2026-08-21

### Added

- Extração real do item "AI Constitution Compiler" do V3.
- `compiler.py`: `compile_constitution(articles) -> ConstitutionCompileResult`
  — análise estática de artigos no formato de `constitutional_ai/constitution.yaml`,
  detectando 3 classes reais de conflito: `duplicate_condition` (condições
  idênticas), `subsumption` (uma condição é caso especial de outra —
  informativo, não bloqueante), `overlapping_condition_different_severity`
  (condições compatíveis com severidades diferentes — bloqueante).
- Contratos novos em `shared/schemas.py` (`ConstitutionConflict`,
  `ConstitutionCompileResult`).
- Suíte de testes pytest (`tests/test_compiler.py`, 10 testes), incluindo
  **análise estática real da constituição de produção**
  (`core/constitutional_ai/constitution.yaml`, 6 artigos reais).

### Notes — achado real na constituição de produção (histórico)

Rodando `compile_constitution()` contra os 6 artigos reais de
`constitutional_ai/constitution.yaml` na versão 0.1.0: **11 conflitos**
`overlapping_condition_different_severity` — bem mais do que o esperado
inicialmente. Causa raiz real: nenhum dos 6 artigos compartilha exatamente
as mesmas chaves de contexto duas a duas, então praticamente todo par tinha
interseção vazia de chaves — o que `_compatible()` considerava compatível
por vacuidade (nenhuma chave em comum para contradizer), inflando falsos
positivos. **Corrigido na versão 0.2.0 — ver seção abaixo.**

## [0.2.0] - 2026-08-21 — Distingue overlap real de overlap por vacuidade (V5, item 2)

### Changed
- `compile_constitution()`: overlaps com severidade diferente agora são
  classificados em dois tipos: `overlapping_condition_different_severity`
  (as duas condições compartilham ao menos uma chave de contexto — sinal
  real, **bloqueante**) e `vacuous_overlap_different_severity` (nenhuma
  chave em comum, compatibilidade só por vacuidade — sinal fraco,
  **informativo, não bloqueante**, mesmo tratamento que `subsumption`).
- Contrato `ConstitutionConflict.conflict_type` ganha o novo valor possível
  `"vacuous_overlap_different_severity"` (é um `str` livre em
  `shared/schemas.py`, não um enum — nenhuma migração de schema necessária).

### Notes — resultado real após o fix
Rodando contra a mesma constituição de produção (6 artigos): **2 conflitos
bloqueantes reais** (`CONST-01`↔`CONST-03`, ambos usando a chave
`automated_decision`; `CONST-05`↔`CONST-06`, ambos usando `in_production` —
exatamente o par citado na análise original da v0.1.0) + **9 informativos**
(`vacuous_overlap_different_severity`). O sinal de 11 falsos-positivos virou
2 achados acionáveis de verdade — a autoria da constituição real deveria
resolver explicitamente qual severidade prevalece nesses 2 pares.

- **Escopo honesto**: cobre 100% do espaço de conflitos possível no formato
  restrito de `constitutional_ai` (conjunções de igualdades) — comparação
  direta de dicionários já é suficiente. Um DSL mais expressivo (negações,
  disjunções) exigiria um solver de satisfatibilidade de verdade.
