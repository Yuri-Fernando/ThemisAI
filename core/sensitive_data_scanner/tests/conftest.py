"""Fixtures de documento real para os testes do Sensitive Data Scanner.

Gera arquivos `.pdf`/`.docx` de verdade em disco (não mocka `pypdf`/`python-docx`
nem o conteúdo extraído) — um gerador mínimo de PDF válido (sem depender de
nenhuma lib de geração de PDF, que não está nas dependências do projeto) e o
próprio `python-docx` (já é dependência de leitura E escrita) para o `.docx`.
"""
from __future__ import annotations

from pathlib import Path

import pytest


def _build_minimal_pdf(text: str) -> bytes:
    """Monta um PDF 1.4 minimamente válido, de um objeto de texto só, com
    tabela xref e offsets corretos — suficiente para `pypdf` ler sem
    precisar do modo de recuperação de arquivo malformado.
    """
    objs = [
        b"<</Type/Catalog/Pages 2 0 R>>",
        b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        b"<</Type/Page/Parent 2 0 R/Resources<</Font<</F1 4 0 R>>>>/MediaBox[0 0 300 144]/Contents 5 0 R>>",
        b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    ]
    stream_content = f"BT /F1 12 Tf 10 100 Td ({text}) Tj ET".encode("latin-1")
    objs.append(
        b"<</Length " + str(len(stream_content)).encode() + b">>\nstream\n" + stream_content + b"\nendstream"
    )

    out = bytearray()
    out += b"%PDF-1.4\n"
    offsets = [0]
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj".encode() + body + b"endobj\n"
    xref_offset = len(out)
    n = len(objs) + 1
    out += f"xref\n0 {n}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer<</Size {n}/Root 1 0 R>>\nstartxref\n{xref_offset}\n%%EOF".encode()
    return bytes(out)


@pytest.fixture()
def make_pdf(tmp_path: Path):
    def _make(text: str, filename: str = "documento.pdf") -> Path:
        path = tmp_path / filename
        path.write_bytes(_build_minimal_pdf(text))
        return path

    return _make


@pytest.fixture()
def make_docx(tmp_path: Path):
    def _make(paragraphs: list[str], filename: str = "documento.docx") -> Path:
        import docx

        document = docx.Document()
        for p in paragraphs:
            document.add_paragraph(p)
        path = tmp_path / filename
        document.save(str(path))
        return path

    return _make


@pytest.fixture()
def make_txt(tmp_path: Path):
    def _make(text: str, filename: str = "documento.txt") -> Path:
        path = tmp_path / filename
        path.write_text(text, encoding="utf-8")
        return path

    return _make
