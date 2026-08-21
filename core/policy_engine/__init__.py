"""Policy Engine — motor de políticas LGPD do Themis AI.

Uso:
    from core.policy_engine.engine import evaluate
    from shared.schemas import DataCategory, LegalBasis

    decisions = evaluate(
        data_categories=[DataCategory.SENSITIVE],
        legal_basis=LegalBasis.CONSENT,
        context={"data_subtype": "health", "ripd_conducted": True},
    )
"""
from core.policy_engine.engine import evaluate

__all__ = ["evaluate"]
