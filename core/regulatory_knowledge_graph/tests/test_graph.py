"""Testes do Regulatory Knowledge Graph — grafo construído a partir do corpus
REAL de `core/regulatory_rag/corpus/*.txt` (nenhuma aresta fabricada)."""
from __future__ import annotations

import networkx as nx
import pytest

from core.regulatory_knowledge_graph.graph import build_graph, find_related, shortest_path, to_result
from shared.schemas import RegulatoryKnowledgeGraphResult


@pytest.fixture(scope="module")
def graph():
    return build_graph()


def test_build_graph_has_all_12_articles(graph):
    assert graph.number_of_nodes() == 12


def test_build_graph_has_real_edges_from_corpus(graph):
    # Art. 38º (RIPD) menciona Art. 11º e Art. 20º no corpo real do texto.
    assert graph.has_edge("art_38", "art_11")
    assert graph.has_edge("art_38", "art_20")


def test_no_self_loops(graph):
    for node in graph.nodes:
        assert not graph.has_edge(node, node)


def test_node_attributes_populated(graph):
    attrs = graph.nodes["art_7"]
    assert attrs["article"] == "7º"
    assert "bases legais" in attrs["tema"].lower()
    assert attrs["source"] == "art_7_bases_legais_gerais.txt"


def test_to_result_matches_graph(graph):
    result = to_result(graph)
    assert isinstance(result, RegulatoryKnowledgeGraphResult)
    assert result.node_count == graph.number_of_nodes()
    assert result.edge_count == graph.number_of_edges()
    assert len(result.nodes) == result.node_count
    assert len(result.edges) == result.edge_count


def test_find_related_one_hop(graph):
    related = find_related(graph, "38", max_hops=1)
    related_ids = {r["id"] for r in related}
    assert "art_11" in related_ids
    assert "art_20" in related_ids
    assert all(r["distance"] == 1 for r in related)


def test_find_related_two_hops_includes_further_articles(graph):
    related_1hop = {r["id"] for r in find_related(graph, "38", max_hops=1)}
    related_2hop = {r["id"] for r in find_related(graph, "38", max_hops=2)}
    assert related_1hop.issubset(related_2hop)
    assert len(related_2hop) >= len(related_1hop)


def test_find_related_unknown_article_returns_empty(graph):
    assert find_related(graph, "999", max_hops=1) == []


def test_shortest_path_direct_edge(graph):
    path = shortest_path(graph, "38", "11")
    assert path == ["art_38", "art_11"]


def test_shortest_path_multi_hop(graph):
    # Art. 38º -> Art. 20º -> Art. 9º (Art. 20º menciona Art. 9º no corpus real).
    path = shortest_path(graph, "38", "9")
    assert path is not None
    assert path[0] == "art_38"
    assert path[-1] == "art_9"


def test_shortest_path_no_path_returns_none(graph):
    # Art. 48º (comunicação de incidente) não tem caminho direcionado até
    # Art. 12º (anonimização) no grafo real do corpus atual.
    path = shortest_path(graph, "48", "12")
    assert path is None


def test_shortest_path_unknown_article_returns_none(graph):
    assert shortest_path(graph, "999", "5") is None


def test_build_graph_is_directed():
    graph = build_graph()
    assert isinstance(graph, nx.DiGraph)
