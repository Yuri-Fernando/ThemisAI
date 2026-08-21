"""AI Trust Score — agregador de sinais de governança do Themis AI.

Uso:
    from core.trust_score.scorer import compute_trust_score
    from shared.schemas import PIIDetectionResult, PolicyDecision

    result = compute_trust_score(
        pii_result=pii_result,
        policy_decisions=policy_decisions,
        prompt_security=prompt_security_result,  # opcional
        explanation=explainability_result,        # opcional
    )
"""
from core.trust_score.scorer import compute_trust_score

__all__ = ["compute_trust_score"]
