"""`analyze_legal_change` — ponto de entrada do Legal Change Intelligence.

    INPUT  norma anterior + norma atual (+ metadados + contexto de clientes)
      ↓ parse_legal_text_with_coverage   (estrutura: art/§/inciso/alínea)
      ↓ structural_diff                  (por dispositivo, não por linha)
      ↓ detect_signals                   (prazo, pena, obrigação, polaridade…)
      ↓ classify_topics                  (taxonomia por área do Direito)
      ↓ match_clients                    (quem cita o dispositivo alterado)
      ↓ assess_impact                    (regras R0–R8, determinístico)
      ↓ OversightQueue.enqueue           (se revisão obrigatória)
    OUTPUT LegalChangeAnalysis

Nenhum LLM participa da decisão. Um LLM pode, a jusante, redigir um resumo
em linguagem natural A PARTIR desta saída (é o que o Conecta AI faz na aba
Direito) — mas `impact_level`, `risk_level` e `requires_human_review` vêm
daqui e não são sobrescritos.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from core.legal_change_intelligence.diff import structural_diff
from core.legal_change_intelligence.impact import assess_impact, match_clients
from core.legal_change_intelligence.signals import classify_topics, detect_signals
from core.legal_change_intelligence.structure import parse_legal_text_with_coverage
from shared.schemas import (
    ClientContext,
    LegalChangeAnalysis,
    LegalImpactLevel,
)

ENGINE_VERSION = "0.1.0"

_LEVEL_LABEL = {
    LegalImpactLevel.NONE: "sem impacto",
    LegalImpactLevel.INFORMATIONAL: "informativo",
    LegalImpactLevel.REVIEW_RECOMMENDED: "revisão recomendada",
    LegalImpactLevel.REVIEW_REQUIRED: "revisão obrigatória",
}


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def analyze_legal_change(
    previous_text: str,
    current_text: str,
    metadata: dict[str, Any] | None = None,
    client_context: list[ClientContext] | list[dict] | None = None,
    oversight_queue: Any | None = None,
    analyzed_at: datetime | None = None,
) -> LegalChangeAnalysis:
    """Compara duas versões de uma norma e decide o impacto de forma auditável.

    Args:
        previous_text / current_text: texto normativo, um dispositivo por linha
            (use `source.html_to_legal_text` para HTML do Planalto).
        metadata: `{"norm_id": "lei-13709-2018", "title": "LGPD",
            "aliases": ["LGPD", "13.709"], ...}` — repassado em `document`.
        client_context: clientes do escritório (`ClientContext` ou dict).
        oversight_queue: `core.human_oversight.OversightQueue` opcional; se
            informado e a revisão for obrigatória, um item é enfileirado e o id
            volta em `oversight_item_id`.
        analyzed_at: relógio injetável (testes reproduzíveis).
    """
    metadata = dict(metadata or {})
    clients = [c if isinstance(c, ClientContext) else ClientContext.model_validate(c) for c in (client_context or [])]
    norm_id = str(metadata.get("norm_id", ""))
    aliases = [str(a) for a in metadata.get("aliases", [])]
    title = str(metadata.get("title", norm_id or "norma"))

    units_before, coverage_before = parse_legal_text_with_coverage(previous_text)
    units_after, coverage_after = parse_legal_text_with_coverage(current_text)

    changes = structural_diff(units_before, units_after)
    for change in changes:
        change.signals = detect_signals(change)

    topics = classify_topics([t for c in changes for t in (c.before, c.after) if t], extra_hint=title) if changes else []
    related = match_clients(changes, topics, clients, norm_id, aliases) if changes else []
    level, risk, fired = assess_impact(changes, related)
    requires_review = level == LegalImpactLevel.REVIEW_REQUIRED

    # Confiança ESTRUTURAL: quanto do texto o parser conseguiu endereçar. Não
    # é confiança na interpretação jurídica (essa é sempre do revisor humano).
    confidence = round(min(coverage_before, coverage_after), 4) if (previous_text.strip() and current_text.strip()) else 0.0

    counts: dict[str, int] = {}
    for change in changes:
        counts[change.change_type.value] = counts.get(change.change_type.value, 0) + 1
    if changes:
        detail = ", ".join(f"{n} {kind}" for kind, n in sorted(counts.items()))
        summary = (
            f"{title}: {len(changes)} dispositivo(s) alterado(s) ({detail}). "
            f"Impacto: {_LEVEL_LABEL[level]} (risco {risk.value}). "
            f"Clientes relacionados: {len(related)} ({sum(r.strength == 'strong' for r in related)} com citação direta)."
        )
    else:
        summary = f"{title}: nenhuma alteração de dispositivo entre as versões."

    oversight_item_id = None
    if requires_review and oversight_queue is not None:
        item = oversight_queue.enqueue(
            subject=f"Alteração normativa — {title}",
            reason=summary + " Regras: " + ", ".join(f.rule_id for f in fired) + ".",
            risk_level=risk,
        )
        oversight_item_id = item.item_id

    return LegalChangeAnalysis(
        engine_version=ENGINE_VERSION,
        document=metadata,
        previous_hash=content_hash(previous_text),
        current_hash=content_hash(current_text),
        units_before=len(units_before),
        units_after=len(units_after),
        parse_coverage_before=coverage_before,
        parse_coverage_after=coverage_after,
        changes=changes,
        affected_topics=topics,
        related_clients=related,
        impact_level=level,
        risk_level=risk,
        requires_human_review=requires_review,
        rules_fired=fired,
        confidence=confidence,
        oversight_item_id=oversight_item_id,
        summary=summary,
        analyzed_at=analyzed_at or datetime.now(timezone.utc),
    )
