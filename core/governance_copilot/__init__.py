"""Governance Copilot — orquestrador + API FastAPI do Themis AI.

Este módulo NÃO reimplementa nenhuma lógica de domínio: é a camada HTTP fina
que expõe os módulos da Onda 1 (`pii_detection`, `prompt_security`,
`policy_engine`, `ripd_engine`, `audit_logs`) ao mundo externo — inclusive ao
`apps/dashboard`, que consome exclusivamente este contrato de API (nunca
importa `core/*` diretamente).

Reexporta `app` (instância FastAPI) para `uvicorn core.governance_copilot:app`.
"""
from __future__ import annotations

from core.governance_copilot.api import app

__all__ = ["app"]
