"""Regulatory Knowledge Graph (GraphRAG) — evolução do `core/regulatory_rag`
de busca por similaridade pura para um grafo de conhecimento navegável.

Consolida duas linhas do ROADMAP original ("GraphRAG" e "Regulatory
Knowledge Graph") num único módulo, por serem, na prática, a mesma
capacidade: um grafo sobre o corpus regulatório do `regulatory_rag`.

**Nenhuma referência é inventada.** As arestas do grafo (`relation="menciona"`)
vêm de menções textuais reais a outros artigos, extraídas por regex do
próprio corpo dos arquivos de `core/regulatory_rag/corpus/*.txt` (reusa
`corpus_loader.load_corpus`, não duplica o parsing). Exemplo real: o arquivo
`art_38_ripd.txt` menciona "Art. 11º" e "Art. 20º" no corpo do texto — essas
viram arestas reais `art_38 -> art_11` e `art_38 -> art_20`, não relações
fabricadas.

Isso permite perguntas que a busca por similaridade pura do `regulatory_rag`
não responde bem: "quais artigos referenciam o Art. 20º (decisões
automatizadas)?", "qual o caminho de dependência regulatória entre o Art. 38º
(RIPD) e o Art. 9º (transparência)?".
"""
from __future__ import annotations

import re
from pathlib import Path

import networkx as nx

from core.regulatory_rag.corpus_loader import load_corpus
from shared.schemas import KnowledgeGraphEdge, KnowledgeGraphNode, RegulatoryKnowledgeGraphResult

DEFAULT_CORPUS_DIR = Path(__file__).resolve().parents[1] / "regulatory_rag" / "corpus"

_ARTICLE_MENTION_RE = re.compile(r"[Aa]rt\.?\s*(\d+)\s*º?")


def _normalize_article_number(article: str | None) -> str | None:
    if not article:
        return None
    match = re.search(r"\d+", article)
    return match.group(0) if match else None


def _node_id(number: str) -> str:
    return f"art_{number}"


def _extract_mentions(text: str) -> set[str]:
    return {m for m in _ARTICLE_MENTION_RE.findall(text)}


def build_graph(corpus_dir: Path | str | None = None) -> nx.DiGraph:
    """Constrói o grafo dirigido de artigos da LGPD a partir do corpus real.

    Nós: um por artigo presente no corpus (`article`, `tema`, `source` como
    atributos). Arestas: `relation="menciona"`, direcionadas do artigo que
    contém a menção para o artigo mencionado — extraídas por regex real do
    corpo do texto, nunca inventadas. Auto-referências (um artigo mencionando
    a si mesmo, comum no próprio cabeçalho/resumo) são ignoradas.
    """
    chunks = load_corpus(corpus_dir or DEFAULT_CORPUS_DIR)

    graph = nx.DiGraph()
    number_to_node: dict[str, str] = {}
    for chunk in chunks:
        number = _normalize_article_number(chunk["article"])
        if number is None:
            continue
        node_id = _node_id(number)
        graph.add_node(node_id, article=chunk["article"], tema=chunk["tema"], source=chunk["source"])
        number_to_node[number] = node_id

    for chunk in chunks:
        number = _normalize_article_number(chunk["article"])
        if number is None:
            continue
        src_node = _node_id(number)
        for mentioned_number in _extract_mentions(chunk["text"]):
            if mentioned_number == number:
                continue  # auto-referência, não é uma aresta real de relação
            target_node = number_to_node.get(mentioned_number)
            if target_node is None:
                continue  # artigo mencionado não está no corpus local
            graph.add_edge(src_node, target_node, relation="menciona")

    return graph


def to_result(graph: nx.DiGraph) -> RegulatoryKnowledgeGraphResult:
    """Serializa um `networkx.DiGraph` (construído por `build_graph`) para o
    contrato Pydantic `RegulatoryKnowledgeGraphResult`."""
    nodes = [
        KnowledgeGraphNode(id=node_id, **attrs) for node_id, attrs in graph.nodes(data=True)
    ]
    edges = [
        KnowledgeGraphEdge(source=u, target=v, relation=attrs.get("relation", "menciona"))
        for u, v, attrs in graph.edges(data=True)
    ]
    return RegulatoryKnowledgeGraphResult(
        nodes=nodes,
        edges=edges,
        node_count=graph.number_of_nodes(),
        edge_count=graph.number_of_edges(),
    )


def find_related(graph: nx.DiGraph, article_number: str, max_hops: int = 1) -> list[dict]:
    """Retorna os artigos alcançáveis a partir de `article_number` em até
    `max_hops` saltos no grafo (considera arestas em ambas as direções —
    "quem este artigo menciona" e "quem menciona este artigo").

    Args:
        graph: grafo construído por `build_graph()`.
        article_number: número do artigo de origem (ex. `"38"` para Art. 38º).
        max_hops: profundidade máxima de busca (BFS).

    Returns:
        Lista de dicts `{"id", "article", "tema", "distance"}`, ordenada por
        distância crescente. Lista vazia se o artigo não existir no grafo ou
        não tiver nenhum artigo relacionado dentro de `max_hops`.
    """
    node_id = _node_id(article_number)
    if node_id not in graph:
        return []

    undirected = graph.to_undirected(as_view=True)
    distances = nx.single_source_shortest_path_length(undirected, node_id, cutoff=max_hops)

    related = []
    for related_id, distance in sorted(distances.items(), key=lambda kv: kv[1]):
        if related_id == node_id:
            continue
        attrs = graph.nodes[related_id]
        related.append(
            {
                "id": related_id,
                "article": attrs.get("article"),
                "tema": attrs.get("tema"),
                "distance": distance,
            }
        )
    return related


def shortest_path(graph: nx.DiGraph, from_article: str, to_article: str) -> list[str] | None:
    """Caminho mais curto (direcionado) entre dois artigos, em número de
    saltos de "menciona". Retorna `None` se não houver caminho.
    """
    src, dst = _node_id(from_article), _node_id(to_article)
    if src not in graph or dst not in graph:
        return None
    try:
        return nx.shortest_path(graph, source=src, target=dst)
    except nx.NetworkXNoPath:
        return None
