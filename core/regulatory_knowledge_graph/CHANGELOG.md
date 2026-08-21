# Changelog — Regulatory Knowledge Graph (GraphRAG)

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Este módulo segue SemVer independente (`core/regulatory_knowledge_graph/`).

Consolida duas linhas do ROADMAP V2 original ("GraphRAG" e "Regulatory
Knowledge Graph") — na prática a mesma capacidade (grafo de conhecimento
sobre o corpus regulatório).

## [0.1.0] - 2026-08-20

### Added

- `graph.py`:
  - `build_graph(corpus_dir=None) -> networkx.DiGraph` — constrói o grafo
    dirigido dos 12 artigos do corpus de `regulatory_rag` (reusa
    `corpus_loader.load_corpus`, não duplica parsing). Arestas
    `relation="menciona"` extraídas por regex REAL do corpo do texto de cada
    artigo (ex.: `art_38_ripd.txt` menciona textualmente "Art. 11º" e "Art.
    20º" — essas viram as arestas `art_38 -> art_11` e `art_38 -> art_20`).
    Auto-referências são descartadas.
  - `to_result(graph) -> RegulatoryKnowledgeGraphResult` — serializa para o
    contrato Pydantic.
  - `find_related(graph, article_number, max_hops=1) -> list[dict]` — BFS
    não-direcionado (considera "menciona" e "é mencionado por") até
    `max_hops`, ordenado por distância.
  - `shortest_path(graph, from_article, to_article) -> list[str] | None` —
    caminho dirigido mais curto entre dois artigos.
- Contratos novos em `shared/schemas.py` (`KnowledgeGraphNode`,
  `KnowledgeGraphEdge`, `RegulatoryKnowledgeGraphResult`, `RelatedArticle`).
- Nova dependência: `networkx` (já usada por outras partes do ecossistema
  Python instalado; adicionada explicitamente a `requirements-heavy.txt`).
- Suíte de testes pytest (`tests/test_graph.py`, 12 testes) contra o corpus
  **real** de `core/regulatory_rag/corpus/` (nenhum corpus fake nos testes):
  12 nós esperados; arestas reais conhecidas (`art_38 -> art_11`,
  `art_38 -> art_20`); ausência de self-loops; atributos de nó corretos;
  `to_result` consistente com o grafo; `find_related` em 1 e 2 saltos;
  artigo desconhecido retorna vazio; caminho direto, multi-hop e inexistente;
  grafo é dirigido.

### Notes

- **Nenhuma aresta é inventada** — só relações textualmente presentes no
  corpus real. Isso significa que o grafo é tão rico quanto o corpus: hoje
  10 arestas entre 12 artigos (alguns artigos, como Art. 48º, não mencionam
  nem são mencionados por nenhum outro artigo do corpus atual — nó isolado,
  não um bug).
- GraphRAG "completo" (recuperação híbrida grafo+embeddings, não só grafo
  puro) fica para uma evolução futura que combine este módulo com
  `regulatory_rag.query()` — TODO explícito, não implementado nesta versão.
