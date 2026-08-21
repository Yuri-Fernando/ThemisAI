"""Testes do Sensitive Data Scanner — extração real de texto de documentos +
reuso real de `pii_detection.detect` (nenhum mock)."""
from __future__ import annotations

import pytest

from core.sensitive_data_scanner.scanner import SUPPORTED_EXTENSIONS, scan_document
from shared.schemas import DocumentScanResult


def test_scan_txt_finds_cpf(make_txt):
    path = make_txt("Contato: joao@example.com, CPF 111.444.777-35.")
    result = scan_document(path)
    assert isinstance(result, DocumentScanResult)
    assert result.file_type == "txt"
    assert result.pages_scanned is None
    assert any(f.entity_type == "CPF" for f in result.pii_result.findings)
    assert any(f.entity_type == "EMAIL" for f in result.pii_result.findings)


def test_scan_pdf_extracts_text_and_finds_cpf(make_pdf):
    path = make_pdf("CPF 111.444.777-35")
    result = scan_document(path)
    assert result.file_type == "pdf"
    assert result.pages_scanned == 1
    assert result.characters_extracted > 0
    assert any(f.entity_type == "CPF" for f in result.pii_result.findings)
    assert "pypdf" in result.extraction_notes


def test_scan_docx_extracts_paragraphs_and_finds_email(make_docx):
    path = make_docx(["Relatório interno.", "Contato: maria@empresa.com.br para dúvidas."])
    result = scan_document(path)
    assert result.file_type == "docx"
    assert result.pages_scanned is None
    assert any(f.entity_type == "EMAIL" for f in result.pii_result.findings)
    assert "python-docx" in result.extraction_notes


def test_scan_docx_with_table_content(make_docx):
    import docx

    document = docx.Document()
    table = document.add_table(rows=1, cols=1)
    table.rows[0].cells[0].text = "CPF: 111.444.777-35"
    path = make_docx([])
    document.save(str(path))

    result = scan_document(path)
    assert any(f.entity_type == "CPF" for f in result.pii_result.findings)


def test_scan_document_no_pii_found(make_txt):
    path = make_txt("Texto completamente neutro sem dado pessoal.")
    result = scan_document(path)
    assert result.pii_result.findings == []
    assert result.pii_result.has_sensitive_data is False


def test_scan_document_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        scan_document(tmp_path / "nao-existe.txt")


def test_scan_document_unsupported_extension(tmp_path):
    path = tmp_path / "arquivo.xlsx"
    path.write_text("qualquer coisa")
    with pytest.raises(ValueError):
        scan_document(path)


def test_supported_extensions_constant():
    assert SUPPORTED_EXTENSIONS == {".txt", ".pdf", ".docx"}


def test_scan_document_accepts_str_path(make_txt):
    path = make_txt("Sem PII aqui.")
    result = scan_document(str(path))
    assert result.file_name == path.name
