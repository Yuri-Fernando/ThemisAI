"""Fairness Audit — métricas de equidade determinísticas (V2)."""
from __future__ import annotations

from core.fairness_audit.engine import audit_fairness
from core.fairness_audit.significance import chi_square_significance

__all__ = ["audit_fairness", "chi_square_significance"]
