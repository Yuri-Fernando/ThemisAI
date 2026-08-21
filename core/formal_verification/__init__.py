"""Formal Verification (extração real do V3) — model checking por enumeração exaustiva."""
from __future__ import annotations

from core.formal_verification.checker import verify_invariant
from core.formal_verification.tribunal_properties import verify_tribunal_deny_precedence

__all__ = ["verify_invariant", "verify_tribunal_deny_precedence"]
