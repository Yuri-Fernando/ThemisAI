"""Testes do AI Trust Score — cobrem a fórmula de composição descrita em
`core/trust_score/scorer.py`: caso ótimo, DENY (veto), REQUIRES_HUMAN_REVIEW,
ALLOW_WITH_MITIGATION, dado sensível vs pessoal comum, prompt inseguro,
`explanation` repassado vs ausente, e o contrato de `components`.

Execução (a partir da raiz do repo):
    .venv/Scripts/python.exe -m pytest core/trust_score/tests -v
"""
from __future__ import annotations

import pytest

from core.trust_score.scorer import (
    POLICY_DENY_FLOOR,
    RISK_THRESHOLD_HIGH,
    RISK_THRESHOLD_LOW,
    RISK_THRESHOLD_MEDIUM,
    compute_trust_score,
)
from shared.schemas import (
    DataCategory,
    ExplainabilityResult,
    PIIDetectionResult,
    PIIFinding,
    PolicyDecision,
    PolicyDecisionStatus,
    PromptSecurityFinding,
    PromptSecurityResult,
    RiskLevel,
)


# ---------------------------------------------------------------------------
# Builders / fixtures auxiliares
# ---------------------------------------------------------------------------

def _pii(*categories: DataCategory) -> PIIDetectionResult:
    findings = [
        PIIFinding(
            entity_type="test_entity",
            text_span="xxx",
            start=0,
            end=3,
            category=cat,
            confidence=0.9,
        )
        for cat in categories
    ]
    return PIIDetectionResult(
        findings=findings,
        has_sensitive_data=any(c == DataCategory.SENSITIVE for c in categories),
        summary="teste",
    )


def _no_pii() -> PIIDetectionResult:
    return PIIDetectionResult(findings=[], has_sensitive_data=False, summary="sem achados")


def _policy(
    status: PolicyDecisionStatus,
    mitigations: list[str] | None = None,
    risk_level: RiskLevel = RiskLevel.LOW,
    policy_id: str = "POL-TEST",
) -> PolicyDecision:
    return PolicyDecision(
        policy_id=policy_id,
        status=status,
        rationale="rationale de teste",
        mitigations=mitigations or [],
        risk_level=risk_level,
    )


def _prompt_security(score: float, is_safe: bool, findings: list | None = None) -> PromptSecurityResult:
    return PromptSecurityResult(findings=findings or [], is_safe=is_safe, score=score)


# ---------------------------------------------------------------------------
# Caso ótimo — sem PII, política ALLOW, prompt seguro
# ---------------------------------------------------------------------------

def test_optimal_case_yields_high_score_and_low_risk():
    result = compute_trust_score(
        pii_result=_no_pii(),
        policy_decisions=[_policy(PolicyDecisionStatus.ALLOW)],
        prompt_security=_prompt_security(score=1.0, is_safe=True),
    )
    assert result.score == 100.0
    assert result.risk_level == RiskLevel.LOW
    assert result.score >= RISK_THRESHOLD_LOW


def test_optimal_case_with_empty_policy_decisions_is_also_high_score():
    result = compute_trust_score(pii_result=_no_pii(), policy_decisions=[])
    assert result.score == 100.0
    assert result.risk_level == RiskLevel.LOW


# ---------------------------------------------------------------------------
# DENY — veto, score mínimo/CRITICAL independente de outros fatores
# ---------------------------------------------------------------------------

def test_deny_forces_score_to_floor_and_critical_risk():
    result = compute_trust_score(
        pii_result=_no_pii(),
        policy_decisions=[_policy(PolicyDecisionStatus.DENY, risk_level=RiskLevel.CRITICAL)],
        prompt_security=_prompt_security(score=1.0, is_safe=True),
    )
    assert result.score <= POLICY_DENY_FLOOR
    assert result.risk_level == RiskLevel.CRITICAL


def test_deny_vetoes_even_when_combined_with_good_signals_elsewhere():
    # Mesmo com PII limpo e prompt seguro, um único DENY deve dominar.
    result = compute_trust_score(
        pii_result=_no_pii(),
        policy_decisions=[
            _policy(PolicyDecisionStatus.ALLOW, policy_id="POL-A"),
            _policy(PolicyDecisionStatus.DENY, policy_id="POL-B", risk_level=RiskLevel.CRITICAL),
        ],
        prompt_security=_prompt_security(score=1.0, is_safe=True),
    )
    assert result.score <= POLICY_DENY_FLOOR
    assert result.risk_level == RiskLevel.CRITICAL
    assert result.components["policy_deny_penalty"] < 0


# ---------------------------------------------------------------------------
# REQUIRES_HUMAN_REVIEW — reduz score, sem zerar
# ---------------------------------------------------------------------------

def test_requires_human_review_reduces_score_but_does_not_zero_it():
    optimal = compute_trust_score(pii_result=_no_pii(), policy_decisions=[])
    result = compute_trust_score(
        pii_result=_no_pii(),
        policy_decisions=[_policy(PolicyDecisionStatus.REQUIRES_HUMAN_REVIEW, risk_level=RiskLevel.MEDIUM)],
    )
    assert result.score < optimal.score
    assert result.score > 0.0
    assert result.components["policy_human_review_penalty"] < 0


def test_multiple_human_review_decisions_compound_penalty():
    one = compute_trust_score(
        pii_result=_no_pii(),
        policy_decisions=[_policy(PolicyDecisionStatus.REQUIRES_HUMAN_REVIEW, policy_id="P1")],
    )
    two = compute_trust_score(
        pii_result=_no_pii(),
        policy_decisions=[
            _policy(PolicyDecisionStatus.REQUIRES_HUMAN_REVIEW, policy_id="P1"),
            _policy(PolicyDecisionStatus.REQUIRES_HUMAN_REVIEW, policy_id="P2"),
        ],
    )
    assert two.score < one.score


# ---------------------------------------------------------------------------
# ALLOW_WITH_MITIGATION — proporcional ao nº de mitigações pendentes
# ---------------------------------------------------------------------------

def test_allow_with_mitigation_penalizes_proportionally_to_pending_items():
    few = compute_trust_score(
        pii_result=_no_pii(),
        policy_decisions=[_policy(PolicyDecisionStatus.ALLOW_WITH_MITIGATION, mitigations=["m1"])],
    )
    many = compute_trust_score(
        pii_result=_no_pii(),
        policy_decisions=[
            _policy(PolicyDecisionStatus.ALLOW_WITH_MITIGATION, mitigations=["m1", "m2", "m3"])
        ],
    )
    assert many.score < few.score
    assert few.score < 100.0


# ---------------------------------------------------------------------------
# Dado sensível — penaliza mais que dado pessoal comum
# ---------------------------------------------------------------------------

def test_sensitive_pii_penalizes_more_than_personal_pii():
    sensitive = compute_trust_score(pii_result=_pii(DataCategory.SENSITIVE), policy_decisions=[])
    personal = compute_trust_score(pii_result=_pii(DataCategory.PERSONAL), policy_decisions=[])
    clean = compute_trust_score(pii_result=_no_pii(), policy_decisions=[])

    assert sensitive.score < personal.score < clean.score
    assert sensitive.components["pii_penalty"] < personal.components["pii_penalty"]


def test_anonymized_and_not_personal_pii_do_not_penalize():
    result = compute_trust_score(
        pii_result=_pii(DataCategory.ANONYMIZED, DataCategory.NOT_PERSONAL),
        policy_decisions=[],
    )
    assert result.score == 100.0
    assert result.components["pii_penalty"] == 0.0


def test_pii_sensitive_penalty_is_capped():
    result = compute_trust_score(
        pii_result=_pii(*([DataCategory.SENSITIVE] * 10)),
        policy_decisions=[],
    )
    assert result.components["pii_penalty"] == pytest.approx(-45.0)


# ---------------------------------------------------------------------------
# Prompt security inseguro — penaliza e pode afetar risk_level
# ---------------------------------------------------------------------------

def test_unsafe_prompt_security_reduces_score():
    safe = compute_trust_score(
        pii_result=_no_pii(),
        policy_decisions=[],
        prompt_security=_prompt_security(score=1.0, is_safe=True),
    )
    unsafe = compute_trust_score(
        pii_result=_no_pii(),
        policy_decisions=[],
        prompt_security=_prompt_security(
            score=0.2,
            is_safe=False,
            findings=[
                PromptSecurityFinding(
                    technique="prompt_injection",
                    matched_pattern="ignore previous instructions",
                    severity=RiskLevel.HIGH,
                )
            ],
        ),
    )
    assert unsafe.score < safe.score
    assert unsafe.components["prompt_security_penalty"] < 0


def test_prompt_security_none_is_ignored_and_does_not_error():
    result = compute_trust_score(pii_result=_no_pii(), policy_decisions=[], prompt_security=None)
    assert result.components["prompt_security_penalty"] == 0.0
    assert result.score == 100.0


def test_unsafe_flag_adds_flat_penalty_beyond_continuous_score():
    # Dois cenários com o mesmo score contínuo moderado, um marcado inseguro.
    moderate_safe = compute_trust_score(
        pii_result=_no_pii(),
        policy_decisions=[],
        prompt_security=_prompt_security(score=0.5, is_safe=True),
    )
    moderate_unsafe = compute_trust_score(
        pii_result=_no_pii(),
        policy_decisions=[],
        prompt_security=_prompt_security(score=0.5, is_safe=False),
    )
    assert moderate_unsafe.score < moderate_safe.score


# ---------------------------------------------------------------------------
# explanation — repassado como veio, nunca gerado internamente
# ---------------------------------------------------------------------------

def test_explanation_defaults_to_none_when_not_provided():
    result = compute_trust_score(pii_result=_no_pii(), policy_decisions=[])
    assert result.explanation is None


def test_explanation_is_passed_through_unchanged_when_provided():
    explanation = ExplainabilityResult(
        subject="trust_score",
        factors={"pii_penalty": -15.0},
        narrative="Explicação gerada por core.explainability (mock de teste).",
    )
    result = compute_trust_score(
        pii_result=_no_pii(),
        policy_decisions=[],
        explanation=explanation,
    )
    assert result.explanation is explanation
    assert result.explanation.narrative == explanation.narrative


# ---------------------------------------------------------------------------
# Mapeamento score -> RiskLevel e contrato de components
# ---------------------------------------------------------------------------

def test_risk_level_mapping_at_thresholds():
    assert compute_trust_score(pii_result=_no_pii(), policy_decisions=[]).risk_level == RiskLevel.LOW

    # Um REQUIRES_HUMAN_REVIEW (-20) leva a 80 -> ainda LOW (>= 80).
    at_medium_boundary = compute_trust_score(
        pii_result=_no_pii(),
        policy_decisions=[
            _policy(PolicyDecisionStatus.REQUIRES_HUMAN_REVIEW, policy_id="P1"),
            _policy(PolicyDecisionStatus.REQUIRES_HUMAN_REVIEW, policy_id="P2"),
        ],
    )
    assert at_medium_boundary.score == pytest.approx(60.0)
    assert at_medium_boundary.risk_level == RiskLevel.MEDIUM
    assert RISK_THRESHOLD_MEDIUM <= at_medium_boundary.score < RISK_THRESHOLD_LOW


def test_high_risk_band_between_20_and_50():
    # 2 findings sensíveis (2 * 15 = 30) + 2 REQUIRES_HUMAN_REVIEW (2 * 20 = 40)
    # = 70 de penalidade -> score 30, dentro da faixa HIGH [20, 50).
    result = compute_trust_score(
        pii_result=_pii(DataCategory.SENSITIVE, DataCategory.SENSITIVE),
        policy_decisions=[
            _policy(PolicyDecisionStatus.REQUIRES_HUMAN_REVIEW, policy_id="P1"),
            _policy(PolicyDecisionStatus.REQUIRES_HUMAN_REVIEW, policy_id="P2"),
        ],
    )
    assert result.score == pytest.approx(30.0)
    assert RISK_THRESHOLD_HIGH <= result.score < RISK_THRESHOLD_MEDIUM
    assert result.risk_level == RiskLevel.HIGH


def test_components_contract_has_expected_keys_and_sums_reasonably():
    result = compute_trust_score(
        pii_result=_pii(DataCategory.SENSITIVE),
        policy_decisions=[_policy(PolicyDecisionStatus.ALLOW_WITH_MITIGATION, mitigations=["m1", "m2"])],
        prompt_security=_prompt_security(score=0.8, is_safe=True),
    )
    expected_keys = {
        "base_score",
        "pii_penalty",
        "policy_human_review_penalty",
        "policy_mitigation_penalty",
        "policy_deny_penalty",
        "prompt_security_penalty",
        "final_score",
    }
    assert set(result.components.keys()) == expected_keys
    assert result.components["final_score"] == result.score
    assert result.components["base_score"] == 100.0


def test_score_is_never_negative_even_with_extreme_penalties():
    result = compute_trust_score(
        pii_result=_pii(*([DataCategory.SENSITIVE] * 20)),
        policy_decisions=[
            _policy(PolicyDecisionStatus.REQUIRES_HUMAN_REVIEW, policy_id=f"P{i}") for i in range(10)
        ],
        prompt_security=_prompt_security(score=0.0, is_safe=False),
    )
    assert 0.0 <= result.score <= 100.0


def test_result_is_trust_score_result_instance():
    from shared.schemas import TrustScoreResult

    result = compute_trust_score(pii_result=_no_pii(), policy_decisions=[])
    assert isinstance(result, TrustScoreResult)
