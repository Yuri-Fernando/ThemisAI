"""Regulatory Knowledge Graph (GraphRAG) — grafo de conhecimento sobre o
corpus regulatório do `regulatory_rag` (V2)."""
from __future__ import annotations

from core.regulatory_knowledge_graph.graph import build_graph, find_related, shortest_path, to_result

__all__ = ["build_graph", "find_related", "shortest_path", "to_result"]
