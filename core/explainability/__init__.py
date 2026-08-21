"""Explainability — utilitário genérico e determinístico de explicabilidade.

Módulo standalone: não importa nenhum outro módulo do projeto além de
`shared.schemas`. É consumido por injeção de dependência (outros módulos
chamam `explain()` diretamente); nunca o contrário. Ver `engine.py` para
detalhes.
"""
from __future__ import annotations

from core.explainability.engine import explain

__all__ = ["explain"]
