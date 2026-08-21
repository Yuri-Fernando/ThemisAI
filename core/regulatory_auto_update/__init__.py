"""Regulatory Auto-Update — versionamento/diff do corpus regulatório local (V2)."""
from __future__ import annotations

from core.regulatory_auto_update.manifest import build_manifest, diff_against_manifest, load_manifest, save_manifest

__all__ = ["build_manifest", "diff_against_manifest", "load_manifest", "save_manifest"]
