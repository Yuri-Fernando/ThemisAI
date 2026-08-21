"""Testes do Regulatory Auto-Update — manifesto real do corpus de
`regulatory_rag` + diff contra um corpus temporário modificado de verdade."""
from __future__ import annotations

import shutil

import pytest

from core.regulatory_auto_update.manifest import (
    DEFAULT_CORPUS_DIR,
    build_manifest,
    diff_against_manifest,
    load_manifest,
    save_manifest,
)
from shared.schemas import CorpusDiff, CorpusManifest


def test_build_manifest_covers_real_corpus():
    manifest = build_manifest()
    assert isinstance(manifest, CorpusManifest)
    assert len(manifest.files) == 12  # mesmo corpus real de 12 artigos do regulatory_rag
    assert all(f.content_hash for f in manifest.files)


def test_build_manifest_is_deterministic():
    m1 = build_manifest()
    m2 = build_manifest()
    hashes1 = {f.filename: f.content_hash for f in m1.files}
    hashes2 = {f.filename: f.content_hash for f in m2.files}
    assert hashes1 == hashes2


def test_save_and_load_manifest_roundtrip(tmp_path):
    manifest = build_manifest()
    path = tmp_path / "manifest.json"
    save_manifest(manifest, manifest_path=path)
    loaded = load_manifest(manifest_path=path)
    assert loaded is not None
    assert len(loaded.files) == len(manifest.files)


def test_load_manifest_missing_file_returns_none(tmp_path):
    assert load_manifest(manifest_path=tmp_path / "nao-existe.json") is None


def test_diff_no_changes_when_corpus_unchanged():
    manifest = build_manifest()
    diff = diff_against_manifest(manifest)
    assert isinstance(diff, CorpusDiff)
    assert diff.added == []
    assert diff.removed == []
    assert diff.modified == []
    assert len(diff.unchanged) == 12


@pytest.fixture()
def temp_corpus(tmp_path):
    """Copia o corpus real para um diretório temporário editável -- os testes
    de diff modificam ESSA cópia, nunca o corpus real do projeto."""
    corpus_copy = tmp_path / "corpus"
    shutil.copytree(DEFAULT_CORPUS_DIR, corpus_copy)
    return corpus_copy


def test_diff_detects_modified_file(temp_corpus):
    manifest = build_manifest(corpus_dir=temp_corpus)

    target = temp_corpus / "art_7_bases_legais_gerais.txt"
    target.write_text(target.read_text(encoding="utf-8") + "\n\nTexto adicionado para o teste.", encoding="utf-8")

    diff = diff_against_manifest(manifest, corpus_dir=temp_corpus)
    assert "art_7_bases_legais_gerais.txt" in diff.modified
    assert "art_7_bases_legais_gerais.txt" not in diff.unchanged


def test_diff_detects_added_file(temp_corpus):
    manifest = build_manifest(corpus_dir=temp_corpus)

    new_file = temp_corpus / "art_99_novo.txt"
    new_file.write_text("Artigo: 99º\nTema: Artigo de teste\nFonte: teste\n\nTexto novo de teste.", encoding="utf-8")

    diff = diff_against_manifest(manifest, corpus_dir=temp_corpus)
    assert "art_99_novo.txt" in diff.added


def test_diff_detects_removed_file(temp_corpus):
    manifest = build_manifest(corpus_dir=temp_corpus)

    (temp_corpus / "art_48_comunicacao_incidente.txt").unlink()

    diff = diff_against_manifest(manifest, corpus_dir=temp_corpus)
    assert "art_48_comunicacao_incidente.txt" in diff.removed


def test_diff_summary_mentions_counts(temp_corpus):
    manifest = build_manifest(corpus_dir=temp_corpus)
    (temp_corpus / "art_48_comunicacao_incidente.txt").unlink()
    diff = diff_against_manifest(manifest, corpus_dir=temp_corpus)
    assert "removido" in diff.summary
