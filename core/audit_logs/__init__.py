"""Audit Logs — hash-chain de auditoria imutável (Themis AI)."""
from core.audit_logs.logger import (
    DEFAULT_LOG_PATH,
    GENESIS_HASH,
    AuditLogger,
    default_logger,
)

__all__ = [
    "AuditLogger",
    "default_logger",
    "GENESIS_HASH",
    "DEFAULT_LOG_PATH",
]
