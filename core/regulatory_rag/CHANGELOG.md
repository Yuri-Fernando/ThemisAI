# Changelog — Regulatory RAG

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
versionamento [SemVer](https://semver.org/lang/pt-BR/).

## [0.1.0] - 2026-08-19

### Added

- Corpus local ilustrativo da LGPD (`core/regulatory_rag/corpus/*.txt`), 12
  arquivos cobrindo Art. 5º, 6º, 7º, 9º, 11º, 12º, 18º, 20º, 37º, 38º, 46º e
  48º. Todo arquivo é uma **paráfrase/resumo explicitamente identificado como
  tal** (cabeçalho padrão "Resumo ilustrativo... não substitui consulta ao
  texto oficial"), nunca uma transcrição literal da lei — ver seção
  "Decisões de design" no notebook de dev-log.
- `core/regulatory_rag/corpus_loader.py`: parsing determinístico do corpus
  (`load_corpus`, `parse_corpus_file`), sem dependência de
  sentence-transformers/chromadb — permite testar parsing isoladamente.
- `core/regulatory_rag/index.py`:
  - `build_index(persist_dir: str | None = None) -> int` — gera embeddings do
    corpus com `sentence-transformers` (modelo
    `paraphrase-multilingual-MiniLM-L12-v2`) e persiste em ChromaDB
    (`PersistentClient`, espaço de similaridade "cosine"), padrão
    `core/regulatory_rag/data/`.
  - `query(text: str, k: int = 3) -> RAGQueryResult` — busca semântica dos
    `k` chunks mais relevantes, retornando `shared.schemas.RAGQueryResult`
    (lista de `RegulatoryChunk` com score de similaridade).
  - `ModelUnavailableError` — erro dedicado para falha de carregamento/
    download do modelo de embeddings (ex.: sem rede), distinto de erros de
    uso indevido da API.
  - `_embedding_text()` — separa o texto usado para gerar o embedding (tema +
    corpo, sem a linha de disclaimer de paráfrase) do texto armazenado/
    retornado ao usuário (texto completo, sempre com o disclaimer). Corrige
    um problema real encontrado em desenvolvimento: como todo chunk começa
    com a mesma frase de disclaimer (quase idêntica entre os 12 arquivos),
    incluí-la no embedding dominava a similaridade de cosseno e degradava o
    ranking (ex.: "o que é dado sensível?" retornava artigos de segurança em
    vez de definição/bases legais). Ver notebook de dev-log para detalhes.
- Testes pytest (`core/regulatory_rag/tests/`):
  - `test_corpus_loader.py` — parsing/contagem de chunks, cobertura dos
    artigos obrigatórios, verificação de que todo chunk se identifica como
    paráfrase. Não depende de sentence-transformers/chromadb.
  - `test_index.py` — construção do índice e busca semântica, com 4 perguntas
    de teste verificando que o artigo correto aparece entre os top-k
    resultados. Marca os testes como `skipped` (não `failed`) via
    `ModelUnavailableError` caso o download do modelo falhe por falta de
    rede.
- `notebooks/regulatory_rag_dev_log.ipynb` — dev log com objetivo do módulo,
  decisões de design, execução real de indexação/queries e handoff summary.
- `status/regulatory_rag.json` — status consumido pelo dashboard agregado
  (`notebooks/00_master_pipeline.ipynb`).

### Notes

- Módulo 100% local: nenhuma chamada a API paga. Único ponto de rede é o
  download único do peso do modelo de embeddings pelo `sentence-transformers`
  (cacheado localmente após a primeira execução).
- Ver `status/regulatory_rag.json` para o status final de execução dos testes
  neste ambiente (inclui nota caso o download do modelo tenha sido
  bloqueado por falta de rede).
- Status final desta rodada: `done` — 14/14 testes passando, incluindo os 4
  que dependem do modelo real de embeddings (download concluído com sucesso).
