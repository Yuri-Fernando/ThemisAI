# Changelog — Regulatory Auto-Update

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Este módulo segue SemVer independente (`core/regulatory_auto_update/`).

## [0.1.0] - 2026-08-20

### Added

- `manifest.py`:
  - `build_manifest(corpus_dir=None) -> CorpusManifest` — snapshot
    determinístico do corpus real de `regulatory_rag` (hash SHA-256 de
    conteúdo por arquivo + metadados).
  - `save_manifest` / `load_manifest` — persistência do manifesto em JSON.
  - `diff_against_manifest(manifest, corpus_dir=None) -> CorpusDiff` —
    classifica cada arquivo do corpus atual como `added`/`removed`/
    `modified`/`unchanged` em relação a um manifesto anterior.
- Contratos novos em `shared/schemas.py` (`CorpusFileSnapshot`,
  `CorpusManifest`, `CorpusDiff`).
- Suíte de testes pytest (`tests/test_manifest.py`, 9 testes): manifesto
  cobre os 12 artigos reais; determinístico; roundtrip save/load; diff sem
  mudanças; diff detecta arquivo modificado/adicionado/removido — os 3
  últimos testes copiam o corpus real para um diretório temporário
  (`shutil.copytree`) e editam SÓ a cópia, nunca tocando o corpus real do
  projeto.

### Notes

- **Escopo honesto**: NÃO busca atualizações do texto oficial da LGPD em
  nenhuma fonte externa (planalto.gov.br ou qualquer outra) — isso exigiria
  scraping de fonte legal oficial + validação jurídica humana antes de
  qualquer substituição automática, fora de escopo desta versão (risco real:
  "auto-update" ingênuo de texto jurídico sem revisão humana pode introduzir
  erro regulatório grave). O que existe é o pré-requisito técnico:
  detecção determinística de mudança local, para que um processo de
  atualização (manual ou futuro-automatizado) saiba o que mudou antes de
  reindexar (`regulatory_rag.build_index`).
