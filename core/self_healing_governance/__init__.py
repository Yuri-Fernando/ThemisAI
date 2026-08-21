"""Self-Healing Governance — detecção + abertura automática de incidente + sugestão de remediação (V2)."""
from __future__ import annotations

from core.self_healing_governance.healer import check_and_heal

__all__ = ["check_and_heal"]
