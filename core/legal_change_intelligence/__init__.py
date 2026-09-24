"""Legal Change Intelligence — detecção e análise determinística de alteração normativa (V7)."""
from __future__ import annotations

from core.legal_change_intelligence.analyzer import ENGINE_VERSION, analyze_legal_change, content_hash
from core.legal_change_intelligence.diff import structural_diff, textual_change_score
from core.legal_change_intelligence.impact import assess_impact, match_clients
from core.legal_change_intelligence.signals import classify_topics, detect_signals
from core.legal_change_intelligence.source import decode_planalto_bytes, html_to_legal_text
from core.legal_change_intelligence.structure import parse_legal_text, parse_legal_text_with_coverage

__all__ = [
    "ENGINE_VERSION",
    "analyze_legal_change",
    "assess_impact",
    "classify_topics",
    "content_hash",
    "decode_planalto_bytes",
    "detect_signals",
    "html_to_legal_text",
    "match_clients",
    "parse_legal_text",
    "parse_legal_text_with_coverage",
    "structural_diff",
    "textual_change_score",
]
