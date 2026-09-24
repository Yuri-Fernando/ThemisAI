# Changelog — Legal Change Intelligence

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Este módulo segue SemVer independente (`core/legal_change_intelligence/`).

## [0.1.0] - 2026-09-23

### Added

- `structure.py` — parser estrutural determinístico de texto normativo
  brasileiro (LC 95/1998, art. 10): artigo › parágrafo (incl. "Parágrafo
  único") › inciso › alínea › item, com ids endereçáveis
  (`art-20.par-1.inc-II.ali-a`), agrupamento por PARTE/LIVRO/TÍTULO/
  CAPÍTULO/SEÇÃO, dispositivos intercalados (`Art. 5º-A`, `I-A`),
  namespace `adct.` para o ADCT da CF, extração de anotações editoriais do
  Planalto ("(Redação dada pela Lei nº ...)", "(VETADO)", "(Revogado)",
  "Vigência") e dos atos alteradores citados nelas (`amended_by`).
  `parse_legal_text_with_coverage` devolve a cobertura estrutural (0–1).
- `source.py` — adaptador HTML compilado do Planalto → texto: remove redação
  tachada (`<strike>`, `<s>`, `<del>`, `line-through`), trata a quebra de
  linha do código-fonte como espaço (o HTML real quebra "Art.\n41."),
  decodifica windows-1252.
- `diff.py` — `structural_diff` por dispositivo (added/removed/modified/
  revoked/annotation_only), removidos intercalados na posição original;
  `textual_change_score` lexical por tokens.
- `signals.py` — sinais determinísticos de materialidade com evidência
  (prazo, valor/pena, obrigação reforçada/atenuada, polaridade, escopo,
  salvaguarda de revisão humana, revogação, dispositivo novo) + taxonomia de
  13 temas jurídicos com casamento por início de palavra.
- `impact.py` — `match_clients` (vínculo `strong` só quando um documento do
  cliente cita o dispositivo alterado DESTA norma; citação em texto livre só
  vale se o documento nomeia a norma ou o cliente a monitora) e
  `assess_impact` com a tabela de regras R0–R8.
- `analyzer.py` — `analyze_legal_change(previous_text, current_text,
  metadata=None, client_context=None, oversight_queue=None, analyzed_at=None)
  -> LegalChangeAnalysis`; enfileira em `human_oversight.OversightQueue`
  quando a revisão é obrigatória.
- Contratos em `shared/schemas.py` (`SCHEMA_VERSION` 0.4.0 → 0.5.0, aditivo):
  `LegalUnitType`, `LegalUnit`, `LegalChangeType`, `LegalSignal`,
  `LegalUnitChange`, `ClientDocument`, `ClientContext`, `RelatedClient`,
  `LegalImpactLevel`, `LegalRuleFiring`, `LegalChangeAnalysis`.
- `fixtures/cases/*.json` — 9 casos de referência (1 real: LGPD Art. 20,
  retirada da revisão "por pessoa natural" pela Lei 13.853/2019; 8
  sintéticos cobrindo cada regra). Os mesmos arquivos rodam na
  implementação TypeScript do Conecta AI (`Direito/core`).
- 31 testes pytest (`tests/`).

### Verified (fora da suíte, contra texto oficial baixado do Planalto)

- Parser rodado sobre 12 normas reais (CF, CC, CPC, CLT, CDC, CTN, CP, CPP,
  LGPD, Estatuto da OAB, LEF, Marco Civil): cobertura estrutural 95,7%–99,2%;
  CF com os 250 artigos do corpo permanente + 148 unidades de artigo no ADCT,
  nenhum artigo faltando.

### Notes

- **Escopo honesto**: sinais são heurísticas lexicais de alta precisão e
  recall limitado — uma reescrita completa de sentido sem nenhuma
  palavra-gatilho só aparece pelo score textual (R5). Por isso o nível
  final é conservador e a interpretação jurídica é SEMPRE do revisor humano.
- `confidence` é confiança ESTRUTURAL (cobertura do parser), não confiança
  na interpretação jurídica.
- Nenhum LLM participa da decisão (`impact_level`, `risk_level`,
  `requires_human_review`). Um LLM pode redigir resumo a jusante, sem
  sobrescrever esses campos.
- Não busca a lei na internet: recebe as duas versões prontas. A coleta
  periódica e o versionamento ficam no orquestrador (no Conecta AI: n8n +
  Supabase), mantendo este motor 100% local e reprodutível.
