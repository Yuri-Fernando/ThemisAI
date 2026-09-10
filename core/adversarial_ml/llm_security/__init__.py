"""Seção de segurança de LLM do relatório de segurança do modelo — compõe
`core/prompt_security` e `core/red_team_lab`."""
from __future__ import annotations

from core.adversarial_ml.llm_security.assessor import assess_llm_security

__all__ = ["assess_llm_security"]
