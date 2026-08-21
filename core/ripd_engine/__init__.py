"""RIPD Engine — orquestração real dos 7 módulos da Onda 1 do Themis AI
para gerar um Relatório de Impacto à Proteção de Dados Pessoais (RIPD)
determinístico e ponta a ponta, sem nenhuma chamada a LLM.

Uso:
    from core.ripd_engine import generate_ripd
    from shared.schemas import DataCategory, LegalBasis

    report = generate_ripd(
        project_name="Recomendador de produtos",
        project_description="Sistema de recomendação baseado no histórico de compras.",
        data_categories=[DataCategory.PERSONAL],
        legal_basis=LegalBasis.CONSENT,
        context={"purpose_specified": True},
    )
    report.executive_summary
"""
from core.ripd_engine.generator import generate_ripd

__all__ = ["generate_ripd"]

__version__ = "0.1.0"
