"""Testes de parsing/carregamento do corpus — NÃO dependem de sentence-transformers
nem de chromadb, portanto rodam mesmo se o download do modelo de embeddings
falhar por falta de rede (ver test_index.py para os testes que dependem do
modelo).

Execução (a partir da raiz do repo):
    .venv/Scripts/python.exe -m pytest core/regulatory_rag/tests -v
"""
from __future__ import annotations

from core.regulatory_rag.corpus_loader import load_corpus, parse_corpus_file
from core.regulatory_rag.index import CORPUS_DIR

REQUIRED_ARTICLES = {"5º", "6º", "7º", "9º", "11º", "18º", "20º", "38º", "46º", "48º"}


def test_corpus_has_between_10_and_15_files():
    chunks = load_corpus(CORPUS_DIR)
    assert 10 <= len(chunks) <= 15, f"esperava entre 10 e 15 arquivos, obtive {len(chunks)}"


def test_corpus_covers_all_required_articles():
    chunks = load_corpus(CORPUS_DIR)
    articles = {c["article"] for c in chunks}
    missing = REQUIRED_ARTICLES - articles
    assert not missing, f"artigos obrigatórios ausentes do corpus: {missing}"


def test_every_chunk_has_source_article_and_nonempty_text():
    chunks = load_corpus(CORPUS_DIR)
    for chunk in chunks:
        assert chunk["source"].endswith(".txt")
        assert chunk["article"], f"chunk sem artigo: {chunk['source']}"
        assert len(chunk["text"]) > 100, f"chunk com texto suspeito curto: {chunk['source']}"


def test_every_chunk_is_explicitly_labeled_as_paraphrase():
    """Regra de 'sem invenção': todo chunk precisa se identificar como
    paráfrase/resumo ilustrativo, nunca como transcrição oficial da lei."""
    chunks = load_corpus(CORPUS_DIR)
    for chunk in chunks:
        text_lower = chunk["text"].lower()
        assert "resumo ilustrativo" in text_lower, (
            f"{chunk['source']} não contém o cabeçalho padrão de paráfrase"
        )
        assert "não substitui consulta ao texto oficial" in text_lower, (
            f"{chunk['source']} não deixa claro que não é o texto oficial"
        )


def test_parse_corpus_file_extracts_metadata(tmp_path):
    sample = tmp_path / "art_99_exemplo.txt"
    sample.write_text(
        "Artigo: 99º\nTema: Exemplo de teste\nFonte: LGPD (Lei 13.709/2018)\n\n"
        "# Resumo ilustrativo do Art. 99º da LGPD — paráfrase de teste.\n\n"
        "Corpo do resumo de teste.",
        encoding="utf-8",
    )
    chunk = parse_corpus_file(sample)
    assert chunk["source"] == "art_99_exemplo.txt"
    assert chunk["article"] == "99º"
    assert chunk["tema"] == "Exemplo de teste"
    assert "Corpo do resumo de teste." in chunk["text"]


def test_load_corpus_is_deterministically_ordered():
    chunks_a = load_corpus(CORPUS_DIR)
    chunks_b = load_corpus(CORPUS_DIR)
    assert [c["source"] for c in chunks_a] == [c["source"] for c in chunks_b]


def test_load_corpus_returns_empty_list_for_missing_dir(tmp_path):
    assert load_corpus(tmp_path / "does_not_exist") == []
