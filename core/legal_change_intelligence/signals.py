"""Sinais determinísticos de materialidade jurídica + taxonomia de temas.

Um diff lexical diz QUANTO o texto mudou; estes sinais dizem se o que mudou
é o tipo de coisa que costuma importar juridicamente: prazo, valor/pena,
força da obrigação (poderá → deverá), polaridade (inserção/remoção de "não"),
escopo (exceções), salvaguarda de revisão humana. Cada sinal carrega a
evidência textual que o disparou — nada é inferido sem trecho que o sustente.

**Escopo honesto**: são heurísticas lexicais de alta precisão e recall
limitado (ex. uma mudança de sentido por reescrita completa, sem nenhuma
dessas palavras-gatilho, não dispara sinal — cai só no score textual). É
por isso que a decisão final é conservadora (ver `impact.py`) e sempre
recomenda revisão humana quando há dúvida.
"""
from __future__ import annotations

import re
from collections import Counter

from shared.schemas import LegalChangeType, LegalSignal, LegalUnitChange

_NUMBER_WORDS = (
    r"um|uma|dois|duas|tr[êe]s|quatro|cinco|seis|sete|oito|nove|dez|onze|doze|quinze|vinte|trinta|"
    r"quarenta|cinquenta|sessenta|noventa|cento|cem|duzentos|trezentos|quinhentos|mil"
)
_DEADLINE_RE = re.compile(
    rf"\b(\d+|(?:(?:{_NUMBER_WORDS})(?:\s+e\s+|\s+)?)+)\s*(?:\(\s*[\w\s]+\s*\)\s*)?(dias?|meses|m[êe]s|anos?|horas?|semanas?)(?:\s+[úu]teis|\s+corridos)?\b",
    re.IGNORECASE,
)
_MONEY_RE = re.compile(r"R\$\s*[\d\.]+(?:,\d{2})?|\b\d+(?:,\d+)?\s*(?:%|por\s+cento)|\b[\w\s]{0,20}sal[áa]rios?[\s-]+m[íi]nimos?", re.IGNORECASE)
_PENALTY_RE = re.compile(r"\b(multa|reclus[ãa]o|deten[çc][ãa]o|pena\b|san[çc][ãa]o|san[çc][õo]es|suspens[ãa]o\s+d[aeo]s?\s+atividades?|advert[êe]ncia|interdi[çc][ãa]o)", re.IGNORECASE)
_OBLIGATORY_RE = re.compile(r"\b(dever[áa]|devem|deve|dever[ãa]o|[ée]\s+obrigat[óo]ri[oa]|obrigatoriamente|[ée]\s+vedad[oa]|s[ãa]o\s+vedad[oa]s|[ée]\s+proibid[oa]|[ée]\s+defeso|fica\s+obrigad[oa])\b", re.IGNORECASE)
_PERMISSIVE_RE = re.compile(r"\b(poder[áa]|podem|pode|poder[ãa]o|[ée]\s+facultad[oa]|facultativamente|a\s+crit[ée]rio)\b", re.IGNORECASE)
_NEGATION_RE = re.compile(r"\b(n[ãa]o|nunca|nenhum|nenhuma|jamais)\b", re.IGNORECASE)
_SCOPE_RE = re.compile(r"\b(salvo|exceto|ressalvad[oa]s?|desde\s+que|somente|apenas|exclusivamente|inclusive|independentemente)\b", re.IGNORECASE)
_HUMAN_REVIEW_RE = re.compile(r"\b(pessoa\s+natural|revis[ãa]o\s+humana|interven[çc][ãa]o\s+humana|supervis[ãa]o\s+humana)\b", re.IGNORECASE)

SIGNAL_WEIGHTS = {
    "REVOCATION": 0.9,
    "PENALTY_OR_AMOUNT_CHANGED": 0.8,
    "HUMAN_REVIEW_SAFEGUARD_CHANGED": 0.8,
    "OBLIGATION_STRENGTHENED": 0.7,
    "OBLIGATION_WEAKENED": 0.7,
    "DEADLINE_CHANGED": 0.7,
    "POLARITY_CHANGED": 0.6,
    "SCOPE_CHANGED": 0.5,
    "NEW_PROVISION": 0.5,
    "PROVISION_REMOVED": 0.6,
}
MATERIAL_SIGNALS = {
    "REVOCATION", "PENALTY_OR_AMOUNT_CHANGED", "HUMAN_REVIEW_SAFEGUARD_CHANGED",
    "OBLIGATION_STRENGTHENED", "OBLIGATION_WEAKENED", "DEADLINE_CHANGED", "POLARITY_CHANGED",
    "PROVISION_REMOVED",
}

# Taxonomia de temas — palavras-chave (minúsculas, sem regex) por área.
TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "protecao_de_dados": ("dados pessoais", "titular", "controlador", "operador", "tratamento de dados", "anonimiza", "autoridade nacional", "lgpd", "privacidade"),
    "tributario": ("tributo", "tribut", "imposto", "contribuinte", "fato gerador", "lançamento", "crédito tributário", "fisco", "fazenda pública", "obrigação acessória", "alíquota"),
    "trabalhista": ("empregado", "empregador", "contrato de trabalho", "jornada", "salário", "férias", "rescisão", "justa causa", "sindicato", "consolidação"),
    "consumidor": ("consumidor", "fornecedor", "produto", "serviço", "relação de consumo", "publicidade", "vício", "defeito"),
    "processual_civil": ("processo", "juiz", "sentença", "recurso", "petição", "citação", "intimação", "prazo processual", "tutela", "execução", "precedente"),
    "penal": ("crime", "pena", "reclusão", "detenção", "delito", "contravenção", "culpável", "dolo"),
    "processual_penal": ("inquérito", "ação penal", "denúncia", "prisão preventiva", "réu", "acusado", "flagrante"),
    "civil_contratos": ("contrato", "obrigação", "responsabilidade civil", "indenização", "posse", "propriedade", "herança", "casamento", "prescrição"),
    "empresarial_societario": ("sociedade", "sócio", "empresário", "administrador", "capital social", "falência", "recuperação judicial",
                               "conselho de administração", "comitê de auditoria", "acionista", "assembleia geral", "governança corporativa"),
    "constitucional": ("direitos fundamentais", "união", "estados", "municípios", "congresso nacional", "supremo tribunal", "emenda constitucional", "garantias"),
    "administrativo": ("administração pública", "servidor público", "licitação", "agente público", "autarquia", "concessão"),
    "digital_internet": ("internet", "provedor de aplicação", "provedor de conexão", "registro de acesso", "neutralidade", "dados de conexão"),
    "advocacia": ("advogado", "advocacia", "ordem dos advogados", "honorários", "inscrição na oab"),
}


# Palavra inteira (prefixo permitido: "tribut" casa "tributário"), para
# "pena" não casar dentro de "apenas".
_TOPIC_PATTERNS = {
    topic: re.compile(r"\b(?:" + "|".join(re.escape(k) for k in keywords) + r")", re.IGNORECASE)
    for topic, keywords in TOPIC_KEYWORDS.items()
}


def _counts(regex: re.Pattern, text: str) -> Counter:
    return Counter(normalize(m.group(0)) for m in regex.finditer(text or ""))


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _diff_evidence(before: Counter, after: Counter) -> str:
    removed = sorted((before - after).elements())
    added = sorted((after - before).elements())
    parts = []
    if removed:
        parts.append("removido: " + ", ".join(f'"{x}"' for x in removed[:5]))
    if added:
        parts.append("incluído: " + ", ".join(f'"{x}"' for x in added[:5]))
    return "; ".join(parts)


def detect_signals(change: LegalUnitChange) -> list[LegalSignal]:
    """Sinais de materialidade para UMA alteração de dispositivo."""
    signals: list[LegalSignal] = []

    def add(signal_id: str, description: str, evidence: str) -> None:
        signals.append(LegalSignal(signal_id=signal_id, description=description, weight=SIGNAL_WEIGHTS[signal_id], evidence=evidence))

    if change.change_type == LegalChangeType.REVOKED:
        add("REVOCATION", "Dispositivo revogado.", (change.before or "")[:200] or change.unit_id)
        return signals
    if change.change_type == LegalChangeType.REMOVED:
        add("PROVISION_REMOVED", "Dispositivo deixou de existir no texto.", (change.before or "")[:200] or change.unit_id)
        return signals
    if change.change_type == LegalChangeType.ADDED:
        add("NEW_PROVISION", "Dispositivo novo incluído.", (change.after or "")[:200] or change.unit_id)
    if change.change_type == LegalChangeType.ANNOTATION_ONLY:
        return signals

    before, after = change.before or "", change.after or ""
    checks = (
        ("DEADLINE_CHANGED", _DEADLINE_RE, "Prazo alterado."),
        ("HUMAN_REVIEW_SAFEGUARD_CHANGED", _HUMAN_REVIEW_RE, "Salvaguarda de revisão/intervenção humana alterada."),
        ("SCOPE_CHANGED", _SCOPE_RE, "Escopo/exceções alterados."),
    )
    for signal_id, regex, description in checks:
        b, a = _counts(regex, before), _counts(regex, after)
        if b != a:
            add(signal_id, description, _diff_evidence(b, a))

    money_b, money_a = _counts(_MONEY_RE, before) + _counts(_PENALTY_RE, before), _counts(_MONEY_RE, after) + _counts(_PENALTY_RE, after)
    if money_b != money_a:
        add("PENALTY_OR_AMOUNT_CHANGED", "Valor, percentual ou sanção alterados.", _diff_evidence(money_b, money_a))

    ob_b, ob_a = sum(_counts(_OBLIGATORY_RE, before).values()), sum(_counts(_OBLIGATORY_RE, after).values())
    pe_b, pe_a = sum(_counts(_PERMISSIVE_RE, before).values()), sum(_counts(_PERMISSIVE_RE, after).values())
    if ob_a > ob_b and pe_a <= pe_b and before:
        add("OBLIGATION_STRENGTHENED", "Linguagem de obrigação/vedação reforçada.",
            _diff_evidence(_counts(_OBLIGATORY_RE, before) + _counts(_PERMISSIVE_RE, before), _counts(_OBLIGATORY_RE, after) + _counts(_PERMISSIVE_RE, after)))
    elif ob_a < ob_b and before:
        add("OBLIGATION_WEAKENED", "Linguagem de obrigação/vedação atenuada.",
            _diff_evidence(_counts(_OBLIGATORY_RE, before) + _counts(_PERMISSIVE_RE, before), _counts(_OBLIGATORY_RE, after) + _counts(_PERMISSIVE_RE, after)))

    neg_b, neg_a = _counts(_NEGATION_RE, before), _counts(_NEGATION_RE, after)
    if before and sum(neg_b.values()) != sum(neg_a.values()):
        add("POLARITY_CHANGED", "Polaridade alterada (negação incluída/removida).", _diff_evidence(neg_b, neg_a))

    return signals


def classify_topics(texts: list[str], extra_hint: str = "") -> list[str]:
    """Temas cujas palavras-chave aparecem no texto alterado (ordenado por
    número de ocorrências, desempate alfabético)."""
    corpus = " ".join(t.lower() for t in texts if t) + " " + extra_hint.lower()
    scored = []
    for topic, pattern in _TOPIC_PATTERNS.items():
        hits = len(pattern.findall(corpus))
        if hits:
            scored.append((-hits, topic))
    return [topic for _, topic in sorted(scored)]
