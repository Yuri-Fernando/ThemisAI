"""Parsing do corpus regulatório local (arquivos .txt em `corpus/`).

Cada arquivo do corpus segue um formato simples de "front-matter" + corpo:

    Artigo: 5º
    Tema: Definições (...)
    Fonte: LGPD (Lei 13.709/2018)

    # Resumo ilustrativo do Art. 5º ...

    <corpo do resumo, em parágrafos>

Este módulo é deliberadamente livre de dependências pesadas (sem
sentence-transformers/chromadb) para que o parsing do corpus possa ser testado
de forma isolada e rápida, mesmo se o download do modelo de embeddings falhar.
"""
from __future__ import annotations

from pathlib import Path
from typing import TypedDict


class CorpusChunk(TypedDict):
    """Um chunk de corpus já parseado, pronto para indexação."""

    source: str
    article: str | None
    tema: str | None
    text: str


def parse_corpus_file(path: Path) -> CorpusChunk:
    """Parseia um único arquivo .txt do corpus em um :class:`CorpusChunk`.

    O cabeçalho (linhas `Chave: valor` antes da primeira linha em branco) é
    lido para metadados (`Artigo`, `Tema`, `Fonte`); o restante do arquivo,
    após a primeira linha em branco, vira o texto do chunk (inclui o
    cabeçalho de paráfrase "# Resumo ilustrativo...").
    """
    raw = path.read_text(encoding="utf-8")
    header, _, body = raw.partition("\n\n")

    meta: dict[str, str] = {}
    for line in header.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip().lower()] = value.strip()

    text = body.strip()
    if not text:
        # Arquivo sem separação clara de header/body: usa o conteúdo inteiro.
        text = raw.strip()

    return CorpusChunk(
        source=path.name,
        article=meta.get("artigo") or None,
        tema=meta.get("tema") or None,
        text=text,
    )


def load_corpus(corpus_dir: Path | str) -> list[CorpusChunk]:
    """Carrega e parseia todos os arquivos `.txt` de `corpus_dir`.

    Retorna a lista de chunks em ordem alfabética de nome de arquivo
    (determinístico), o que mantém os `ids` do índice estáveis entre builds.
    """
    corpus_path = Path(corpus_dir)
    if not corpus_path.is_dir():
        return []
    files = sorted(corpus_path.glob("*.txt"))
    return [parse_corpus_file(f) for f in files]
