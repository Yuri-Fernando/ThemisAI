"""Regulatory Auto-Update — versionamento e detecção de mudança do corpus
local do `regulatory_rag` (`core/regulatory_rag/corpus/*.txt`).

**Escopo honesto**: este módulo NÃO busca automaticamente atualizações do
texto oficial da LGPD em nenhuma fonte externa (ex. planalto.gov.br) — isso
exigiria scraping de uma fonte legal oficial e validação jurídica humana do
conteúdo antes de qualquer substituição automática no corpus, o que está
fora de escopo desta versão (e é um risco real: um "auto-update" ingênuo de
texto jurídico sem revisão humana é o tipo de coisa que pode introduzir erro
regulatório grave). O que este módulo entrega de real é o **pré-requisito
técnico** para isso: detecção determinística de mudança local (hash de
conteúdo por arquivo), para que um processo de atualização — manual ou
futuro-automatizado — saiba exatamente o que mudou desde o último snapshot
antes de reindexar (`regulatory_rag.build_index`).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from core.regulatory_rag.corpus_loader import load_corpus
from shared.schemas import CorpusDiff, CorpusFileSnapshot, CorpusManifest

DEFAULT_CORPUS_DIR = Path(__file__).resolve().parents[1] / "regulatory_rag" / "corpus"
DEFAULT_MANIFEST_PATH = Path(__file__).parent / "data" / "corpus_manifest.json"


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_manifest(corpus_dir: Path | str | None = None) -> CorpusManifest:
    """Constrói um manifesto (snapshot) do estado atual do corpus: um hash
    de conteúdo por arquivo, mais os metadados (`article`, `tema`)."""
    chunks = load_corpus(corpus_dir or DEFAULT_CORPUS_DIR)
    files = [
        CorpusFileSnapshot(
            filename=chunk["source"],
            content_hash=_hash_text(chunk["text"]),
            article=chunk["article"],
            tema=chunk["tema"],
        )
        for chunk in chunks
    ]
    return CorpusManifest(generated_at=datetime.now(timezone.utc), files=files)


def save_manifest(manifest: CorpusManifest, manifest_path: str | Path | None = None) -> None:
    path = Path(manifest_path) if manifest_path else DEFAULT_MANIFEST_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")


def load_manifest(manifest_path: str | Path | None = None) -> CorpusManifest | None:
    path = Path(manifest_path) if manifest_path else DEFAULT_MANIFEST_PATH
    if not path.exists():
        return None
    return CorpusManifest.model_validate_json(path.read_text(encoding="utf-8"))


def diff_against_manifest(
    manifest: CorpusManifest,
    corpus_dir: Path | str | None = None,
) -> CorpusDiff:
    """Compara o corpus atual em disco contra um `manifest` anterior e
    classifica cada arquivo em `added`, `removed`, `modified` ou `unchanged`.
    """
    current = build_manifest(corpus_dir)
    current_by_name = {f.filename: f for f in current.files}
    previous_by_name = {f.filename: f for f in manifest.files}

    added = sorted(set(current_by_name) - set(previous_by_name))
    removed = sorted(set(previous_by_name) - set(current_by_name))
    modified = sorted(
        name
        for name in (set(current_by_name) & set(previous_by_name))
        if current_by_name[name].content_hash != previous_by_name[name].content_hash
    )
    unchanged = sorted(
        name
        for name in (set(current_by_name) & set(previous_by_name))
        if current_by_name[name].content_hash == previous_by_name[name].content_hash
    )

    if not added and not removed and not modified:
        summary = f"Nenhuma mudança detectada no corpus ({len(unchanged)} arquivo(s) inalterado(s))."
    else:
        parts = []
        if added:
            parts.append(f"{len(added)} adicionado(s)")
        if removed:
            parts.append(f"{len(removed)} removido(s)")
        if modified:
            parts.append(f"{len(modified)} modificado(s)")
        summary = f"Mudanças detectadas no corpus: {', '.join(parts)}. {len(unchanged)} inalterado(s)."

    return CorpusDiff(added=added, removed=removed, modified=modified, unchanged=unchanged, summary=summary)
