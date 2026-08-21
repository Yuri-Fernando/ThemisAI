"""Runtime Policy Enforcement (extração real do V3) — enforcement em nível de aplicação."""
from __future__ import annotations

from core.runtime_policy_enforcement.enforcement import EnforcementError, enforce

__all__ = ["EnforcementError", "enforce"]
