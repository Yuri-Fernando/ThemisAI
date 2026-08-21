"""RIPD Engine — orquestra de verdade os 7 módulos da Onda 1 do Themis AI
para gerar um Relatório de Impacto à Proteção de Dados Pessoais (RIPD),
ponta a ponta, sem NENHUMA chamada a LLM (motor 100% determinístico e local,
conforme decisão de arquitetura do projeto — ver ROADMAP.md/CHANGELOG.md
raiz).

Este módulo NÃO reimplementa nenhuma lógica dos módulos que compõe — ele
apenas os importa e encadeia, seguindo o contrato de `shared/schemas.py`.
É o primeiro módulo do projeto a provar, com testes reais (sem mock), que a
composição dos 7 módulos da Onda 1 funciona de ponta a ponta.

Pipeline (ver `generate_ripd`):
    1. `pii_detection.detect(project_description)` — PII vazada na própria
       descrição do projeto.
    2. `policy_engine.evaluate(data_categories, legal_basis, context)` —
       decisões de política LGPD aplicáveis.
    3. `prompt_security.scan(context["sample_prompt"])` — opcional, só roda
       se `context` trouxer essa chave.
    4. `regulatory_rag.query(...)` — contexto regulatório mais relevante
       (query composta a partir da descrição do projeto + categorias de
       dado + base legal, para melhorar a recuperação semântica).
    5. `trust_score.compute_trust_score` chamado DUAS vezes: a primeira para
       obter `components`, que alimentam `explainability.explain(...)`; a
       segunda já com a `ExplainabilityResult` pronta, fechando o ciclo de
       injeção de dependência documentado pelos módulos da Onda 1
       (`trust_score` nunca gera sua própria explicação; `explainability`
       nunca conhece `trust_score`).
    6. Agregação de todas as `mitigations` das `PolicyDecision` aplicáveis.
    7. Resumo executivo determinístico em português (template +
       interpolação de dados reais — não é geração livre/LLM).
    8. Registro de um evento `AuditEventType.RIPD_GENERATED` via
       `audit_logs.default_logger()`.
    9. Montagem do `RIPDReport` (shared/schemas.py) totalmente preenchido.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from core.audit_logs.logger import default_logger
from core.explainability.engine import explain
from core.pii_detection.detector import detect
from core.policy_engine.engine import evaluate
from core.prompt_security.scanner import scan
from core.regulatory_rag.index import query
from core.trust_score.scorer import compute_trust_score
from shared.schemas import (
    AuditEventType,
    DataCategory,
    LegalBasis,
    PIIDetectionResult,
    PolicyDecision,
    PolicyDecisionStatus,
    PromptSecurityResult,
    RAGQueryResult,
    RIPDReport,
    RiskLevel,
    TrustScoreResult,
)

# ---------------------------------------------------------------------------
# Vocabulário PT-BR usado no resumo executivo determinístico
# ---------------------------------------------------------------------------

RISK_LABEL_PT: dict[RiskLevel, str] = {
    RiskLevel.LOW: "baixo",
    RiskLevel.MEDIUM: "médio",
    RiskLevel.HIGH: "alto",
    RiskLevel.CRITICAL: "crítico",
}

_STATUS_LABEL_PT: dict[PolicyDecisionStatus, str] = {
    PolicyDecisionStatus.DENY: "NEGADA",
    PolicyDecisionStatus.REQUIRES_HUMAN_REVIEW: "REQUER REVISÃO HUMANA",
    PolicyDecisionStatus.ALLOW_WITH_MITIGATION: "PERMITIDA COM MITIGAÇÃO",
    PolicyDecisionStatus.ALLOW: "PERMITIDA",
}

# Ordem de severidade usada para destacar as decisões "mais críticas" no
# resumo executivo (menor índice = mais crítico/prioritário).
_STATUS_SEVERITY_ORDER: dict[PolicyDecisionStatus, int] = {
    PolicyDecisionStatus.DENY: 0,
    PolicyDecisionStatus.REQUIRES_HUMAN_REVIEW: 1,
    PolicyDecisionStatus.ALLOW_WITH_MITIGATION: 2,
    PolicyDecisionStatus.ALLOW: 3,
}

_DATA_CATEGORY_LABEL_PT: dict[DataCategory, str] = {
    DataCategory.PERSONAL: "pessoal",
    DataCategory.SENSITIVE: "sensível",
    DataCategory.ANONYMIZED: "anonimizado",
    DataCategory.NOT_PERSONAL: "não pessoal",
}

_LEGAL_BASIS_LABEL_PT: dict[LegalBasis, str] = {
    LegalBasis.CONSENT: "consentimento",
    LegalBasis.LEGITIMATE_INTEREST: "legítimo interesse",
    LegalBasis.LEGAL_OBLIGATION: "obrigação legal",
    LegalBasis.CONTRACT_EXECUTION: "execução de contrato",
    LegalBasis.RESEARCH: "pesquisa",
    LegalBasis.NOT_DETERMINED: "não determinada",
}

_MAX_CRITICAL_POLICIES_IN_SUMMARY = 3
_MAX_REGULATORY_REFS_IN_SUMMARY = 3

# Chave reconhecida em `context` para acionar o scan opcional de prompt
# security (passo 3 do pipeline). Não é repassada ao policy_engine como um
# sinal de política — o policy_engine simplesmente ignora chaves que não
# reconhece em `context`, então mantê-la no dicionário é inofensivo.
SAMPLE_PROMPT_CONTEXT_KEY = "sample_prompt"


# ---------------------------------------------------------------------------
# Passo 6 — agregação de mitigações
# ---------------------------------------------------------------------------


def _aggregate_mitigations(policy_decisions: list[PolicyDecision]) -> list[str]:
    """Agrega as mitigações de todas as PolicyDecision, deduplicando e
    preservando a ordem de primeira ocorrência (política a política, na
    ordem retornada por `policy_engine.evaluate`)."""
    seen: set[str] = set()
    mitigations: list[str] = []
    for decision in policy_decisions:
        for mitigation in decision.mitigations:
            if mitigation not in seen:
                seen.add(mitigation)
                mitigations.append(mitigation)
    return mitigations


# ---------------------------------------------------------------------------
# Passo 4 — query composta para o Regulatory RAG
# ---------------------------------------------------------------------------


def _build_regulatory_query(
    project_description: str,
    data_categories: list[DataCategory],
    legal_basis: LegalBasis,
) -> str:
    """Compõe a query semântica enviada ao índice regulatório a partir da
    descrição do projeto enriquecida com as categorias de dado e a base
    legal — mais discriminativo para o RAG do que a descrição sozinha
    quando ela é curta ou genérica."""
    categories_txt = ", ".join(
        _DATA_CATEGORY_LABEL_PT.get(cat, cat.value) for cat in data_categories
    ) or "não especificada"
    legal_basis_txt = _LEGAL_BASIS_LABEL_PT.get(legal_basis, legal_basis.value)
    return (
        f"{project_description} "
        f"Categorias de dado envolvidas: {categories_txt}. "
        f"Base legal declarada: {legal_basis_txt}."
    ).strip()


# ---------------------------------------------------------------------------
# Passo 7 — resumo executivo determinístico (template + interpolação)
# ---------------------------------------------------------------------------


def _build_executive_summary(
    project_name: str,
    trust_score_result: TrustScoreResult,
    policy_decisions: list[PolicyDecision],
    pii_result: PIIDetectionResult,
    rag_result: RAGQueryResult,
    prompt_security_result: PromptSecurityResult | None,
) -> str:
    """Monta o resumo executivo do RIPD em português, 100% determinístico
    (template fixo + interpolação de dados já calculados pelo pipeline).
    Não há geração livre de texto: cada frase é montada a partir de campos
    concretos dos resultados dos módulos da Onda 1."""
    risk_label = RISK_LABEL_PT.get(trust_score_result.risk_level, trust_score_result.risk_level.value)
    parts: list[str] = []

    parts.append(
        f"RIPD do projeto '{project_name}': nível de risco final classificado como "
        f"{risk_label.upper()} ({trust_score_result.risk_level.value}), "
        f"AI Trust Score {trust_score_result.score:.1f}/100."
    )

    if policy_decisions:
        ordered = sorted(
            policy_decisions,
            key=lambda d: _STATUS_SEVERITY_ORDER.get(d.status, 99),
        )
        top = ordered[:_MAX_CRITICAL_POLICIES_IN_SUMMARY]
        decisions_txt = "; ".join(
            f"{d.policy_id} — {_STATUS_LABEL_PT.get(d.status, d.status.value)} "
            f"(risco {RISK_LABEL_PT.get(d.risk_level, d.risk_level.value)})"
            for d in top
        )
        remaining = len(policy_decisions) - len(top)
        suffix = f"; e mais {remaining} decisão(ões) de política aplicável(is)" if remaining > 0 else ""
        parts.append(f"Decisões de política mais críticas: {decisions_txt}{suffix}.")
    else:
        parts.append(
            "Nenhuma política de LGPD foi acionada para as categorias de dado e a "
            "base legal informadas."
        )

    if pii_result.findings:
        sensitive_note = " (inclui dado sensível, LGPD Art. 5º, II)" if pii_result.has_sensitive_data else ""
        parts.append(
            f"A descrição do projeto submetida a este RIPD contém "
            f"{len(pii_result.findings)} achado(s) de dado pessoal/sensível{sensitive_note} "
            f"({pii_result.summary}) — recomenda-se revisar e anonimizar a descrição antes de "
            f"qualquer compartilhamento externo deste relatório."
        )
    else:
        parts.append(
            "Nenhum dado pessoal ou sensível foi identificado na descrição do projeto "
            "submetida a este RIPD."
        )

    if prompt_security_result is not None:
        safety_txt = "SEGURO" if prompt_security_result.is_safe else "INSEGURO"
        parts.append(
            f"O prompt de amostra analisado (context.sample_prompt) foi classificado como "
            f"{safety_txt} (score {prompt_security_result.score:.2f}, "
            f"{len(prompt_security_result.findings)} achado(s) de segurança de prompt)."
        )

    if rag_result.chunks:
        refs = ", ".join(
            (chunk.article or chunk.source)
            for chunk in rag_result.chunks[:_MAX_REGULATORY_REFS_IN_SUMMARY]
        )
        parts.append(f"Contexto regulatório da LGPD consultado para este RIPD: {refs}.")
    else:
        parts.append(
            "Nenhum trecho regulatório correspondente foi encontrado no índice local da LGPD "
            "para esta descrição de projeto."
        )

    return " ".join(parts)


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------


def generate_ripd(
    project_name: str,
    project_description: str,
    data_categories: list[DataCategory],
    legal_basis: LegalBasis,
    context: dict[str, Any] | None = None,
) -> RIPDReport:
    """Gera um Relatório de Impacto à Proteção de Dados Pessoais (RIPD)
    compondo, de ponta a ponta e sem nenhuma chamada a LLM, os 7 módulos da
    Onda 1 do Themis AI.

    Args:
        project_name: nome do projeto de IA avaliado.
        project_description: descrição livre do projeto — também escaneada
            por PII (passo 1 do pipeline), pois descrições de projeto
            frequentemente vazam dado pessoal real sem que o autor perceba.
        data_categories: categorias de dado envolvidas (LGPD Art. 5º),
            repassadas a `policy_engine.evaluate`.
        legal_basis: base legal declarada para o tratamento, repassada a
            `policy_engine.evaluate`.
        context: sinais operacionais adicionais repassados a
            `policy_engine.evaluate` (ver vocabulário em
            `core/policy_engine/policies.yaml`). Se contiver a chave
            `"sample_prompt"`, esse texto é adicionalmente escaneado por
            `prompt_security.scan`. `None` equivale a `{}`.

    Returns:
        `RIPDReport` (shared/schemas.py) totalmente preenchido, com todos os
        campos coerentes entre si (ex.: `trust_score.risk_level` sempre
        refletido em `executive_summary`).
    """
    context = context or {}

    # 1. PII na própria descrição do projeto.
    pii_result = detect(project_description)

    # 2. Decisões de política LGPD aplicáveis ao cenário.
    policy_decisions = evaluate(data_categories, legal_basis, context)

    # 3. Segurança de prompt — opcional, só roda se houver amostra.
    sample_prompt = context.get(SAMPLE_PROMPT_CONTEXT_KEY)
    prompt_security_result: PromptSecurityResult | None = (
        scan(sample_prompt) if sample_prompt else None
    )

    # 4. Contexto regulatório mais relevante para este cenário.
    regulatory_query_text = _build_regulatory_query(project_description, data_categories, legal_basis)
    rag_result = query(regulatory_query_text, k=3)

    # 5. Trust score + explicabilidade — ciclo de injeção de dependência:
    #    calcula uma primeira vez para obter os `components`, gera a
    #    explicação a partir deles, e recalcula já com a explicação pronta.
    preliminary_trust_score = compute_trust_score(
        pii_result=pii_result,
        policy_decisions=policy_decisions,
        prompt_security=prompt_security_result,
    )
    explanation = explain(
        preliminary_trust_score.components,
        subject="ripd_trust_score",
    )
    trust_score_result = compute_trust_score(
        pii_result=pii_result,
        policy_decisions=policy_decisions,
        prompt_security=prompt_security_result,
        explanation=explanation,
    )

    # 6. Mitigações agregadas de todas as decisões de política.
    mitigations = _aggregate_mitigations(policy_decisions)

    # 7. Resumo executivo determinístico.
    executive_summary = _build_executive_summary(
        project_name=project_name,
        trust_score_result=trust_score_result,
        policy_decisions=policy_decisions,
        pii_result=pii_result,
        rag_result=rag_result,
        prompt_security_result=prompt_security_result,
    )

    # 8. Evento de auditoria (payload 100% serializável em JSON).
    default_logger().record_event(
        AuditEventType.RIPD_GENERATED,
        actor="ripd_engine",
        payload={
            "project_name": project_name,
            "data_categories": [cat.value for cat in data_categories],
            "legal_basis": legal_basis.value,
            "trust_score": trust_score_result.score,
            "risk_level": trust_score_result.risk_level.value,
            "pii_findings_count": len(pii_result.findings),
            "pii_has_sensitive_data": pii_result.has_sensitive_data,
            "policy_decisions": [
                {
                    "policy_id": decision.policy_id,
                    "status": decision.status.value,
                    "risk_level": decision.risk_level.value,
                }
                for decision in policy_decisions
            ],
            "mitigations_count": len(mitigations),
            "regulatory_sources": [chunk.source for chunk in rag_result.chunks],
            "prompt_security_is_safe": (
                prompt_security_result.is_safe if prompt_security_result is not None else None
            ),
        },
    )

    # 9. Relatório final.
    return RIPDReport(
        project_name=project_name,
        generated_at=datetime.now(timezone.utc),
        data_categories=list(data_categories),
        legal_basis=legal_basis,
        pii_result=pii_result,
        policy_decisions=policy_decisions,
        prompt_security=prompt_security_result,
        trust_score=trust_score_result,
        regulatory_context=rag_result.chunks,
        mitigations=mitigations,
        executive_summary=executive_summary,
    )
