"""AI Trust Score — agrega sinais de outros módulos V1 em um score único (0-100).

Este módulo é um AGREGADOR PURO: não importa `core.pii_detection`, `core.policy_engine`,
`core.prompt_security` nem `core.explainability`. Ele recebe os RESULTADOS já prontos
desses módulos (objetos Pydantic de `shared.schemas`) como parâmetros — injeção de
dependência. Isso evita acoplamento/race condition entre módulos desenvolvidos em
paralelo; a orquestração real (chamar cada módulo e passar os resultados aqui) é
responsabilidade do Governance Copilot (Onda 2).

FÓRMULA DE COMPOSIÇÃO
======================

Score começa em `BASE_SCORE = 100.0` e sofre penalidades aditivas de 4 fontes
independentes. Ao final, o resultado é limitado (clamp) em [0, 100]:

1. PII (`pii_result: PIIDetectionResult`)
   - Cada `PIIFinding` com `category == DataCategory.SENSITIVE` custa
     `PII_SENSITIVE_PENALTY_PER_FINDING` pontos (dado sensível, Art. 5º II LGPD,
     é estruturalmente mais grave que dado pessoal comum).
   - Cada finding com `category == DataCategory.PERSONAL` custa
     `PII_PERSONAL_PENALTY_PER_FINDING` pontos (menor, pois é o caso comum/esperado).
   - Findings `ANONYMIZED`/`NOT_PERSONAL` não penalizam.
   - Cada sub-total é limitado por um teto (`PII_SENSITIVE_PENALTY_CAP` /
     `PII_PERSONAL_PENALTY_CAP`) para que dezenas de findings do mesmo tipo não
     dominem o score de forma desproporcional a um único achado grave.

2. Políticas (`policy_decisions: list[PolicyDecision]`)
   - `DENY`: qualquer decisão com este status aciona um PISO (`POLICY_DENY_FLOOR`)
     — o score final nunca pode ultrapassar esse piso, não importa quão bem as
     outras dimensões estejam. Isso é uma veto: uma política negada é, por
     definição, uma reprovação da operação avaliada.
   - `REQUIRES_HUMAN_REVIEW`: cada ocorrência custa
     `POLICY_HUMAN_REVIEW_PENALTY` pontos (incerteza que exige supervisão humana
     é tratada como risco médio-alto).
   - `ALLOW_WITH_MITIGATION`: custa `POLICY_MITIGATION_PENALTY_PER_ITEM` pontos
     por item pendente em `decision.mitigations` (proporcional ao esforço de
     remediação ainda não comprovadamente aplicado).
   - `ALLOW`: não penaliza.

3. Segurança de prompt (`prompt_security: PromptSecurityResult | None`)
   - Se `None`, esta dimensão é ignorada (nenhuma penalidade, nenhum componente).
   - Caso contrário: penalidade contínua proporcional ao quão inseguro o prompt é,
     `(1 - prompt_security.score) * PROMPT_SECURITY_MAX_PENALTY`.
   - Se `prompt_security.is_safe is False`, soma-se ainda uma penalidade fixa
     `PROMPT_SECURITY_UNSAFE_FLAT_PENALTY` — o próprio módulo de prompt security
     pode classificar como inseguro mesmo com um `score` numérico moderado (ex.:
     um único padrão de jailbreak de alta confiança), e essa classificação binária
     é um sinal independente que merece peso próprio, não só o score contínuo.

4. Explicabilidade (`explanation: ExplainabilityResult | None`)
   - Não participa da fórmula numérica. É apenas repassada como veio — este
     módulo NUNCA gera sua própria narrativa/explicação; quem gera é
     `core.explainability`. Ver Onda 2 / Governance Copilot.

MAPEAMENTO SCORE -> RiskLevel
==============================
    score >= 80              -> LOW
    50 <= score < 80          -> MEDIUM
    20 <= score < 50          -> HIGH
    score < 20                -> CRITICAL

Observação: `POLICY_DENY_FLOOR = 5.0` é, por construção, sempre < 20, então uma
única política DENY já garante `RiskLevel.CRITICAL` através do mapeamento normal
— não é necessário nenhum caso especial na atribuição de `risk_level`.

`components` expõe a contribuição (delta, sempre <= 0 exceto `"base_score"`) de
cada fator, mais `"final_score"`. É pensado para ser passado adiante como
`factors` de um `ExplainabilityResult` por quem for gerar a explicação (o próprio
`core.explainability`, via Governance Copilot) — este módulo não interpreta essa
narrativa, apenas produz os números que a sustentam.
"""
from __future__ import annotations

from shared.schemas import (
    DataCategory,
    ExplainabilityResult,
    PIIDetectionResult,
    PolicyDecision,
    PolicyDecisionStatus,
    PromptSecurityResult,
    RiskLevel,
    TrustScoreResult,
)

# ---------------------------------------------------------------------------
# Constantes da fórmula (documentadas no docstring do módulo)
# ---------------------------------------------------------------------------

BASE_SCORE = 100.0

# PII
PII_SENSITIVE_PENALTY_PER_FINDING = 15.0
PII_SENSITIVE_PENALTY_CAP = 45.0
PII_PERSONAL_PENALTY_PER_FINDING = 4.0
PII_PERSONAL_PENALTY_CAP = 20.0

# Políticas
POLICY_DENY_FLOOR = 5.0
POLICY_HUMAN_REVIEW_PENALTY = 20.0
POLICY_MITIGATION_PENALTY_PER_ITEM = 5.0

# Segurança de prompt
PROMPT_SECURITY_MAX_PENALTY = 30.0
PROMPT_SECURITY_UNSAFE_FLAT_PENALTY = 15.0

# Mapeamento score -> RiskLevel (limites inferiores inclusivos)
RISK_THRESHOLD_LOW = 80.0
RISK_THRESHOLD_MEDIUM = 50.0
RISK_THRESHOLD_HIGH = 20.0


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _pii_penalty(pii_result: PIIDetectionResult) -> float:
    """Soma as penalidades de PII (sensível + pessoal comum), já com teto aplicado."""
    sensitive_count = sum(
        1 for f in pii_result.findings if f.category == DataCategory.SENSITIVE
    )
    personal_count = sum(
        1 for f in pii_result.findings if f.category == DataCategory.PERSONAL
    )
    sensitive_penalty = min(
        sensitive_count * PII_SENSITIVE_PENALTY_PER_FINDING, PII_SENSITIVE_PENALTY_CAP
    )
    personal_penalty = min(
        personal_count * PII_PERSONAL_PENALTY_PER_FINDING, PII_PERSONAL_PENALTY_CAP
    )
    return sensitive_penalty + personal_penalty


def _policy_penalties(policy_decisions: list[PolicyDecision]) -> tuple[float, float, bool]:
    """Retorna (penalidade de human_review, penalidade de mitigação, has_deny)."""
    human_review_penalty = 0.0
    mitigation_penalty = 0.0
    has_deny = False

    for decision in policy_decisions:
        if decision.status == PolicyDecisionStatus.DENY:
            has_deny = True
        elif decision.status == PolicyDecisionStatus.REQUIRES_HUMAN_REVIEW:
            human_review_penalty += POLICY_HUMAN_REVIEW_PENALTY
        elif decision.status == PolicyDecisionStatus.ALLOW_WITH_MITIGATION:
            mitigation_penalty += len(decision.mitigations) * POLICY_MITIGATION_PENALTY_PER_ITEM
        # ALLOW: sem penalidade.

    return human_review_penalty, mitigation_penalty, has_deny


def _prompt_security_penalty(prompt_security: PromptSecurityResult | None) -> float:
    if prompt_security is None:
        return 0.0
    penalty = (1.0 - prompt_security.score) * PROMPT_SECURITY_MAX_PENALTY
    if not prompt_security.is_safe:
        penalty += PROMPT_SECURITY_UNSAFE_FLAT_PENALTY
    return penalty


def _risk_level_for(score: float) -> RiskLevel:
    if score >= RISK_THRESHOLD_LOW:
        return RiskLevel.LOW
    if score >= RISK_THRESHOLD_MEDIUM:
        return RiskLevel.MEDIUM
    if score >= RISK_THRESHOLD_HIGH:
        return RiskLevel.HIGH
    return RiskLevel.CRITICAL


def compute_trust_score(
    pii_result: PIIDetectionResult,
    policy_decisions: list[PolicyDecision],
    prompt_security: PromptSecurityResult | None = None,
    explanation: ExplainabilityResult | None = None,
) -> TrustScoreResult:
    """Calcula o AI Trust Score agregando PII, políticas e (opcionalmente) segurança
    de prompt. Ver docstring do módulo para a fórmula completa e documentada.

    Args:
        pii_result: resultado já computado de `core.pii_detection` (injetado).
        policy_decisions: lista de `PolicyDecision` já computada por
            `core.policy_engine.evaluate` (injetado). Pode ser vazia.
        prompt_security: resultado já computado de `core.prompt_security` (injetado).
            Opcional — quando `None`, essa dimensão não participa do score.
        explanation: `ExplainabilityResult` já computado por `core.explainability`
            (injetado). Este módulo NUNCA gera sua própria explicação — apenas
            repassa o que foi recebido. Opcional.

    Returns:
        `TrustScoreResult` com `score` (0-100), `risk_level` derivado do score,
        `components` (contribuição de cada fator, ver docstring do módulo) e
        `explanation` (repassado sem modificação).
    """
    pii_penalty = _pii_penalty(pii_result)
    human_review_penalty, mitigation_penalty, has_deny = _policy_penalties(policy_decisions)
    prompt_penalty = _prompt_security_penalty(prompt_security)

    raw_score = BASE_SCORE - pii_penalty - human_review_penalty - mitigation_penalty - prompt_penalty
    pre_deny_score = _clamp(raw_score)

    final_score = min(pre_deny_score, POLICY_DENY_FLOOR) if has_deny else pre_deny_score
    final_score = _clamp(final_score)

    deny_penalty = (pre_deny_score - final_score) if has_deny else 0.0

    components: dict[str, float] = {
        "base_score": BASE_SCORE,
        "pii_penalty": -pii_penalty,
        "policy_human_review_penalty": -human_review_penalty,
        "policy_mitigation_penalty": -mitigation_penalty,
        "policy_deny_penalty": -deny_penalty,
        "prompt_security_penalty": -prompt_penalty,
        "final_score": final_score,
    }

    return TrustScoreResult(
        score=final_score,
        risk_level=_risk_level_for(final_score),
        components=components,
        explanation=explanation,
    )
