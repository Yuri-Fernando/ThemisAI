"""Regulatory RAG — base de conhecimento regulatório local (LGPD) do Themis AI.

Uso:
    from core.regulatory_rag import build_index, query

    build_index()
    result = query("o que é dado sensível?", k=3)

Ver `core/regulatory_rag/index.py` para detalhes de implementação e
`core/regulatory_rag/corpus/` para o corpus (paráfrases ilustrativas da LGPD,
Lei 13.709/2018 — não é o texto oficial; ver cabeçalho de cada arquivo).
"""
from core.regulatory_rag.corpus_loader import load_corpus, parse_corpus_file
from core.regulatory_rag.index import ModelUnavailableError, build_index, query

__all__ = [
    "build_index",
    "query",
    "load_corpus",
    "parse_corpus_file",
    "ModelUnavailableError",
]
