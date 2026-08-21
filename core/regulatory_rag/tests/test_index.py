"""Testes de indexação e busca semântica (build_index / query).

Estes testes DEPENDEM do download do peso do modelo de embeddings
("paraphrase-multilingual-MiniLM-L12-v2") pelo sentence-transformers na
primeira execução. Se isso falhar por falta de rede/timeout, os testes são
marcados como `skipped` (não `failed`) via `ModelUnavailableError` — ver
`core/regulatory_rag/CHANGELOG.md` e `status/regulatory_rag.json` para o
registro desse eventual bloqueio.

Execução (a partir da raiz do repo):
    .venv/Scripts/python.exe -m pytest core/regulatory_rag/tests -v
"""
from __future__ import annotations

import pytest

from core.regulatory_rag.corpus_loader import load_corpus
from core.regulatory_rag.index import CORPUS_DIR, ModelUnavailableError, build_index, query


@pytest.fixture(scope="module")
def indexed_count(tmp_path_factory):
    """Constrói o índice uma vez para todo o módulo de teste, em um
    diretório temporário isolado (não polui `core/regulatory_rag/data/`
    nem depende de estado de execuções anteriores)."""
    persist_dir = tmp_path_factory.mktemp("regulatory_rag_index")
    try:
        n = build_index(persist_dir=str(persist_dir))
    except ModelUnavailableError as exc:
        pytest.skip(f"Modelo de embeddings indisponível (sem rede para download?): {exc}")
    return n, persist_dir


def test_build_index_indexes_every_corpus_chunk(indexed_count):
    n_indexed, _ = indexed_count
    n_corpus = len(load_corpus(CORPUS_DIR))
    assert n_indexed == n_corpus
    assert n_indexed >= 10


def test_build_index_creates_persist_dir(indexed_count):
    _, persist_dir = indexed_count
    assert persist_dir.exists()
    assert any(persist_dir.iterdir()), "diretório de persistência do Chroma está vazio"


@pytest.mark.parametrize(
    "question,expected_article",
    [
        ("O que é considerado dado pessoal sensível segundo a lei?", "5º"),
        ("Uma decisão automatizada sobre uma pessoa pode ser revisada por um humano?", "20º"),
        ("Quando uma empresa precisa fazer um relatório de impacto (RIPD)?", "38º"),
        ("Quais são os direitos que o titular dos dados pode exercer?", "18º"),
    ],
)
def test_query_returns_relevant_article_in_top_k(indexed_count, question, expected_article, monkeypatch):
    _, persist_dir = indexed_count
    # `query()` usa o diretório padrão de dados do módulo; apontamos o padrão
    # para o índice temporário criado por este teste.
    import core.regulatory_rag.index as index_module

    monkeypatch.setattr(index_module, "DEFAULT_DATA_DIR", persist_dir)

    result = query(question, k=3)
    assert result.query == question
    assert len(result.chunks) > 0

    articles = [c.article for c in result.chunks]
    assert expected_article in articles, (
        f"esperava o Art. {expected_article} entre os top-{len(result.chunks)} "
        f"resultados para {question!r}, obtive {articles}"
    )
    # scores devem estar ordenados do mais relevante para o menos relevante
    scores = [c.score for c in result.chunks]
    assert scores == sorted(scores, reverse=True)


def test_query_without_index_raises_clear_error(tmp_path, monkeypatch):
    import core.regulatory_rag.index as index_module

    monkeypatch.setattr(index_module, "DEFAULT_DATA_DIR", tmp_path / "empty")
    with pytest.raises((RuntimeError, ModelUnavailableError)):
        query("qualquer pergunta", k=3)
