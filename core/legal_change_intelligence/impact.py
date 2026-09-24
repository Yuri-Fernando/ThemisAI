"""Mapeamento de clientes afetados + motor de regras de impacto.

A decisão de impacto é **regra, não LLM** — mesmo princípio de todo o Themis
(ver README, "Deliberadamente sem LLM no motor de decisão"): um escritório
precisa saber EXATAMENTE por que uma alteração foi marcada como "revisão
obrigatória", e a mesma entrada precisa dar sempre a mesma saída.

Tabela de regras (avaliadas todas; o nível final é o MAIS ALTO disparado):

| Regra                   | Condição                                             | Nível mínimo        | Risco    |
|-------------------------|------------------------------------------------------|---------------------|----------|
| R0 NO_CHANGE            | nenhuma alteração                                    | none                | low      |
| R1 REVOCATION           | dispositivo revogado ou removido                     | review_required     | high     |
| R2 MATERIAL_SIGNAL      | sinal material (prazo, pena, obrigação, polaridade…) | review_required     | high     |
| R3 STRONG_CLIENT_LINK   | documento de cliente cita dispositivo alterado       | review_required     | medium   |
| R4 COMBINED_EXPOSURE    | R3 + (R1 ou R2)                                      | review_required     | critical |
| R5 MATERIAL_TEXT_CHANGE | score textual ≥ 0.35                                 | review_recommended  | medium   |
| R6 NEW_AMENDING_ACT     | texto alterado + ato alterador novo na anotação      | review_recommended  | medium   |
| R7 WEAK_CLIENT_LINK     | cliente com afinidade temática/norma monitorada      | review_recommended  | medium   |
| R8 MINOR_CHANGE         | só alterações pequenas/anotação                      | informational       | low      |
"""
from __future__ import annotations

import re

from shared.schemas import (
    ClientContext,
    LegalChangeType,
    LegalImpactLevel,
    LegalRuleFiring,
    LegalUnitChange,
    RelatedClient,
    RiskLevel,
)

from core.legal_change_intelligence.signals import MATERIAL_SIGNALS

MATERIAL_TEXT_THRESHOLD = 0.35

_LEVEL_ORDER = [
    LegalImpactLevel.NONE,
    LegalImpactLevel.INFORMATIONAL,
    LegalImpactLevel.REVIEW_RECOMMENDED,
    LegalImpactLevel.REVIEW_REQUIRED,
]
_RISK_ORDER = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]

# "art. 20", "artigo 20", "arts. 18 e 20", "art. 20, § 1º", "art. 5º, inciso X"
_CITATION_RE = re.compile(
    r"\bart(?:igo)?s?\.?\s*(\d{1,3}(?:\.\d{3})*)\s*(?:º|°|o\b)?(?:\s*-\s*([A-Z]))?"
    r"(?:\s*,?\s*(?:§\s*(\d+)\s*(?:º|°)?|par[áa]grafo\s+([úu]nico)))?",
    re.IGNORECASE,
)


def _cited_unit_ids(text: str) -> set[str]:
    """Extrai ids citados em texto livre: `art. 20, § 1º` → {art-20, art-20.par-1}."""
    ids: set[str] = set()
    for m in _CITATION_RE.finditer(text or ""):
        article = m.group(1).replace(".", "") + (f"-{m.group(2).upper()}" if m.group(2) else "")
        ids.add(f"art-{article}")
        if m.group(3):
            ids.add(f"art-{article}.par-{m.group(3)}")
        elif m.group(4):
            ids.add(f"art-{article}.par-unico")
    return ids


def _mentions_norm(text: str, aliases: list[str]) -> bool:
    low = (text or "").lower()
    return any(alias and alias.lower() in low for alias in aliases)


def _changed_matches(cited: set[str], changes: list[LegalUnitChange]) -> list[str]:
    """Um documento que cita `art-20` é afetado por mudança em `art-20` ou em
    qualquer dispositivo dentro dele (`art-20.par-1...`); um que cita
    `art-20.par-1` só pelo próprio § e seus filhos."""
    matched = []
    for change in changes:
        for cited_id in cited:
            if change.unit_id == cited_id or change.unit_id.startswith(cited_id + "."):
                matched.append(change.unit_id)
                break
    return matched


def match_clients(
    changes: list[LegalUnitChange],
    affected_topics: list[str],
    clients: list[ClientContext],
    norm_id: str,
    norm_aliases: list[str],
) -> list[RelatedClient]:
    """Liga alterações a clientes. `strong` = algum documento do cliente cita
    um dispositivo alterado DESTA norma; `weak` = cliente monitora a norma ou
    tem tema em comum, mas nenhum documento cita o dispositivo."""
    related: list[RelatedClient] = []
    aliases = [norm_id, *norm_aliases]
    for client in clients:
        watches = norm_id in client.watched_norms or any(a in client.watched_norms for a in norm_aliases)
        matched_units: list[str] = []
        documents: list[str] = []
        reasons: list[str] = []
        for doc in client.documents:
            cited = set(doc.cited_units)
            # Citação em texto livre só vale se o documento nomeia a norma (ou
            # o cliente a monitora) — "art. 20" sozinho é ambíguo entre leis.
            if doc.text and (watches or _mentions_norm(doc.text, aliases) or _mentions_norm(doc.title, aliases)):
                cited |= _cited_unit_ids(doc.text)
            hits = _changed_matches(cited, changes)
            if hits:
                documents.append(doc.doc_id)
                for h in hits:
                    if h not in matched_units:
                        matched_units.append(h)
                reasons.append(f'Documento "{doc.title}" cita dispositivo alterado ({", ".join(hits)}).')
        common_topics = sorted(set(client.topics) & set(affected_topics))
        if matched_units:
            related.append(RelatedClient(client_id=client.client_id, name=client.name, strength="strong",
                                         matched_units=matched_units, related_documents=documents, reasons=reasons))
        elif watches or common_topics:
            if watches:
                reasons.append("Cliente monitora esta norma.")
            if common_topics:
                reasons.append(f"Tema em comum: {', '.join(common_topics)}.")
            related.append(RelatedClient(client_id=client.client_id, name=client.name, strength="weak", reasons=reasons))
    return sorted(related, key=lambda r: (r.strength != "strong", r.client_id))


def assess_impact(
    changes: list[LegalUnitChange],
    related_clients: list[RelatedClient],
) -> tuple[LegalImpactLevel, RiskLevel, list[LegalRuleFiring]]:
    """Aplica a tabela de regras do docstring do módulo."""
    fired: list[LegalRuleFiring] = []
    level, risk = LegalImpactLevel.NONE, RiskLevel.LOW

    def raise_to(new_level: LegalImpactLevel, new_risk: RiskLevel) -> None:
        nonlocal level, risk
        if _LEVEL_ORDER.index(new_level) > _LEVEL_ORDER.index(level):
            level = new_level
        if _RISK_ORDER.index(new_risk) > _RISK_ORDER.index(risk):
            risk = new_risk

    if not changes:
        fired.append(LegalRuleFiring(rule_id="R0_NO_CHANGE", description="Nenhuma alteração de dispositivo detectada."))
        return level, risk, fired

    revoked = [c.unit_id for c in changes if c.change_type in (LegalChangeType.REVOKED, LegalChangeType.REMOVED)]
    material = [f"{c.unit_id}: {s.signal_id}" for c in changes for s in c.signals if s.signal_id in MATERIAL_SIGNALS and s.signal_id not in ("REVOCATION", "PROVISION_REMOVED")]
    strong = [r for r in related_clients if r.strength == "strong"]
    weak = [r for r in related_clients if r.strength == "weak"]
    text_changed = [c for c in changes if c.change_type in (LegalChangeType.MODIFIED, LegalChangeType.ADDED)]
    big_text = [f"{c.unit_id} ({c.textual_change_score:.2f})" for c in text_changed if c.textual_change_score >= MATERIAL_TEXT_THRESHOLD]
    new_acts = sorted({a for c in text_changed for a in c.amended_by})

    if revoked:
        fired.append(LegalRuleFiring(rule_id="R1_REVOCATION", description="Dispositivo revogado ou removido.", evidence=revoked))
        raise_to(LegalImpactLevel.REVIEW_REQUIRED, RiskLevel.HIGH)
    if material:
        fired.append(LegalRuleFiring(rule_id="R2_MATERIAL_SIGNAL", description="Alteração com sinal de materialidade jurídica.", evidence=material))
        raise_to(LegalImpactLevel.REVIEW_REQUIRED, RiskLevel.HIGH)
    if strong:
        fired.append(LegalRuleFiring(rule_id="R3_STRONG_CLIENT_LINK", description="Documento de cliente cita dispositivo alterado.",
                                     evidence=[f"{r.client_id}: {', '.join(r.matched_units)}" for r in strong]))
        raise_to(LegalImpactLevel.REVIEW_REQUIRED, RiskLevel.MEDIUM)
        if revoked or material:
            fired.append(LegalRuleFiring(rule_id="R4_COMBINED_EXPOSURE", description="Alteração material em dispositivo citado por cliente.",
                                         evidence=[r.client_id for r in strong]))
            raise_to(LegalImpactLevel.REVIEW_REQUIRED, RiskLevel.CRITICAL)
    if big_text:
        fired.append(LegalRuleFiring(rule_id="R5_MATERIAL_TEXT_CHANGE", description=f"Reescrita textual relevante (score ≥ {MATERIAL_TEXT_THRESHOLD}).", evidence=big_text))
        raise_to(LegalImpactLevel.REVIEW_RECOMMENDED, RiskLevel.MEDIUM)
    if new_acts:
        fired.append(LegalRuleFiring(rule_id="R6_NEW_AMENDING_ACT", description="Texto alterado por ato normativo novo.", evidence=new_acts))
        raise_to(LegalImpactLevel.REVIEW_RECOMMENDED, RiskLevel.MEDIUM)
    if weak:
        fired.append(LegalRuleFiring(rule_id="R7_WEAK_CLIENT_LINK", description="Cliente com afinidade temática ou que monitora a norma.",
                                     evidence=[r.client_id for r in weak]))
        raise_to(LegalImpactLevel.REVIEW_RECOMMENDED, RiskLevel.MEDIUM)
    if level == LegalImpactLevel.NONE:
        fired.append(LegalRuleFiring(rule_id="R8_MINOR_CHANGE", description="Apenas alterações menores ou de anotação.",
                                     evidence=[c.unit_id for c in changes]))
        raise_to(LegalImpactLevel.INFORMATIONAL, RiskLevel.LOW)
    return level, risk, fired
