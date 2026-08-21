"""PII Detection — motor regex-first, 100% offline e determinístico, com
heurística leve de nomes próprios e enriquecimento opcional via spaCy.

Escopo (V1 — ver ROADMAP.md):
    - CPF, CNPJ (com validação de dígito verificador)
    - RG (com validação de dígito verificador é inviável — formato varia por
      estado; usamos janela de contexto com a palavra "RG" para reduzir falso
      positivo com o formato de CPF)
    - E-mail
    - Telefone BR (com/sem DDD, com/sem +55)
    - CEP
    - Data de nascimento (regex de data + janela de contexto, ex. "nasc",
      "data de nascimento", "DN")
    - Nome próprio: heurística leve (sequência de 2+ palavras capitalizadas,
      fora de início de frase, com lista de stopwords em português para
      reduzir falso positivo). NÃO é um NER real — ver limitações no
      notebook de dev-log.

Classificação (LGPD Art. 5º):
    - CPF / RG / nome / e-mail / telefone / CEP / data de nascimento =>
      DataCategory.PERSONAL (Art. 5º, I)
    - Menções a dado de saúde, biometria, orientação sexual, religião,
      etnia/raça, opinião política ou filiação sindical => DataCategory.SENSITIVE
      (Art. 5º, II) — detectado por lista de palavras-chave, NÃO por NLP real.

Enriquecimento opcional via spaCy (pt_core_news_sm): tentado em best-effort
dentro de try/except. Se o modelo não estiver instalado/baixável, o caminho
regex sozinho já cobre 100% dos tipos exigidos e todos os testes passam sem
o spaCy.
"""
from __future__ import annotations

import re
from typing import Any

from shared.schemas import DataCategory, PIIDetectionResult, PIIFinding

# ---------------------------------------------------------------------------
# Validação de dígito verificador (CPF / CNPJ)
# ---------------------------------------------------------------------------


def _validate_cpf(digits: str) -> bool:
    """Valida CPF (11 dígitos) pelo algoritmo oficial de dígito verificador."""
    if len(digits) != 11 or len(set(digits)) == 1:
        return False

    def _calc(base: str, start_factor: int) -> str:
        total = sum(int(n) * f for n, f in zip(base, range(start_factor, 1, -1)))
        remainder = total % 11
        return "0" if remainder < 2 else str(11 - remainder)

    d1 = _calc(digits[:9], 10)
    d2 = _calc(digits[:9] + d1, 11)
    return digits[-2:] == d1 + d2


def _validate_cnpj(digits: str) -> bool:
    """Valida CNPJ (14 dígitos) pelo algoritmo oficial de dígito verificador."""
    if len(digits) != 14 or len(set(digits)) == 1:
        return False

    weights_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    weights_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

    def _calc(base: str, weights: list[int]) -> str:
        total = sum(int(n) * w for n, w in zip(base, weights))
        remainder = total % 11
        return "0" if remainder < 2 else str(11 - remainder)

    d1 = _calc(digits[:12], weights_1)
    d2 = _calc(digits[:12] + d1, weights_2)
    return digits[-2:] == d1 + d2


# ---------------------------------------------------------------------------
# Regex — caminho crítico determinístico
# ---------------------------------------------------------------------------

_CPF_FORMATTED_RE = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
_CPF_PLAIN_RE = re.compile(r"(?<!\d)\d{11}(?!\d)")

_CNPJ_FORMATTED_RE = re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b")
_CNPJ_PLAIN_RE = re.compile(r"(?<!\d)\d{14}(?!\d)")

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

_CEP_FORMATTED_RE = re.compile(r"\b\d{5}-\d{3}\b")
_CEP_PLAIN_RE = re.compile(r"(?<!\d)\d{8}(?!\d)")
_CEP_CONTEXT_RE = re.compile(r"\bcep\b", re.IGNORECASE)

# Telefone com DDD, com ou sem formatação, com ou sem +55.
_PHONE_WITH_DDD_RE = re.compile(
    r"(?<!\d)(?:\+55[\s.-]?)?\(?\d{2}\)?[\s.-]?9?\d{4}[\s.-]?\d{4}(?!\d)"
)
# Telefone sem DDD — só aceito com hífen explícito (reduz falso positivo).
_PHONE_NO_DDD_RE = re.compile(r"(?<!\d)9?\d{4}-\d{4}(?!\d)")

_RG_KEYWORD_RE = re.compile(r"\bRG\b\.?\s*:?\s*", re.IGNORECASE)
_RG_NUMBER_RE = re.compile(r"\d{1,2}\.\d{3}\.\d{3}-[\dXx]\b")

_BIRTHDATE_KEYWORD_RE = re.compile(
    r"(data de nascimento|nascid[oa]\s+em|nasc\.?\b|\bdn\b\s*:?)", re.IGNORECASE
)
_DATE_RE = re.compile(
    r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
    r"|\d{1,2}\s+de\s+[a-zçãéêíóôõú]+\s+de\s+\d{4}",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Heurística leve de nome próprio
# ---------------------------------------------------------------------------

# Sequência de 2+ palavras capitalizadas, permitindo conectores minúsculos
# comuns em nomes compostos brasileiros ("da", "de", "do", "das", "dos", "e").
_NAME_RE = re.compile(
    r"\b[A-ZÀ-Ý][a-zà-ÿ]+"
    r"(?:\s+(?:d[aeo]s?|e)\s+[A-ZÀ-Ý][a-zà-ÿ]+|\s+[A-ZÀ-Ý][a-zà-ÿ]+)+\b"
)

# Palavras capitalizadas comuns em português que NÃO são nomes próprios —
# reduz falso positivo da heurística de nome. Lista deliberadamente pequena
# e pragmática (não exaustiva) — ver limitações no notebook de dev-log.
_NAME_STOPWORDS = {
    "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
    "sexta-feira", "sábado", "domingo",
    "janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
    "agosto", "setembro", "outubro", "novembro", "dezembro",
    "brasil", "brasileiro", "brasileira", "governo", "empresa", "ministério",
    "secretaria", "conforme", "portanto", "assim", "além", "segundo",
    "quando", "onde", "porque", "contudo", "todavia", "entretanto",
    "estado", "município", "prefeitura", "república", "constituição",
    "lei", "artigo", "capítulo", "anexo", "processo", "protocolo",
    "sistema", "plataforma", "departamento", "diretoria", "gerência",
    "atenciosamente", "prezado", "prezada", "senhor", "senhora",
}

# ---------------------------------------------------------------------------
# Palavras-chave de dado sensível (LGPD Art. 5º, II)
# ---------------------------------------------------------------------------

_SENSITIVE_KEYWORDS: dict[str, list[str]] = {
    "SENSITIVE_HEALTH": [
        "dado de saúde", "saúde", "doença", "diagnóstico", "tratamento médico",
        "exame médico", "hiv", "câncer", "depressão", "diabetes", "cirurgia",
        "prontuário médico", "transtorno mental", "medicamento controlado",
        "deficiência",
    ],
    "SENSITIVE_BIOMETRIC": [
        "biometria", "biométrico", "biométrica", "impressão digital",
        "reconhecimento facial", "leitura de íris", "digital do dedo",
    ],
    "SENSITIVE_SEXUAL_ORIENTATION": [
        "orientação sexual", "homossexual", "heterossexual", "bissexual",
        "gay", "lésbica", "transexual",
    ],
    "SENSITIVE_RELIGION": [
        "religião", "religioso", "religiosa", "católico", "católica",
        "evangélico", "evangélica", "espírita", "umbanda", "candomblé",
        "muçulmano", "muçulmana", "judeu", "judia", "ateu", "ateia",
    ],
    "SENSITIVE_ETHNICITY": [
        "etnia", "racial", "raça", "indígena", "afrodescendente",
        "quilombola",
    ],
    "SENSITIVE_POLITICAL_UNION": [
        "opinião política", "filiação partidária", "filiação sindical",
        "sindicato", "partido político",
    ],
}


# ---------------------------------------------------------------------------
# Resolução de sobreposição de spans
# ---------------------------------------------------------------------------


def _resolve_overlaps(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Resolve spans sobrepostos: maior confiança vence; empate -> mais longo."""
    ordered = sorted(
        candidates,
        key=lambda c: (-c["confidence"], -(c["end"] - c["start"]), c["start"]),
    )
    accepted: list[dict[str, Any]] = []
    occupied: list[tuple[int, int]] = []
    for cand in ordered:
        overlaps = any(
            not (cand["end"] <= s or cand["start"] >= e) for s, e in occupied
        )
        if overlaps:
            continue
        accepted.append(cand)
        occupied.append((cand["start"], cand["end"]))
    accepted.sort(key=lambda c: c["start"])
    return accepted


# ---------------------------------------------------------------------------
# Matchers individuais — cada um retorna uma lista de candidatos
# ---------------------------------------------------------------------------


def _match_cpf(text: str) -> list[dict[str, Any]]:
    out = []
    for m in _CPF_FORMATTED_RE.finditer(text):
        digits = re.sub(r"\D", "", m.group())
        confidence = 0.98 if _validate_cpf(digits) else 0.6
        out.append(
            {
                "start": m.start(), "end": m.end(), "text": m.group(),
                "entity_type": "CPF", "category": DataCategory.PERSONAL,
                "confidence": confidence,
            }
        )
    for m in _CPF_PLAIN_RE.finditer(text):
        digits = m.group()
        if _validate_cpf(digits):
            out.append(
                {
                    "start": m.start(), "end": m.end(), "text": m.group(),
                    "entity_type": "CPF", "category": DataCategory.PERSONAL,
                    "confidence": 0.9,
                }
            )
    return out


def _match_cnpj(text: str) -> list[dict[str, Any]]:
    out = []
    for m in _CNPJ_FORMATTED_RE.finditer(text):
        digits = re.sub(r"\D", "", m.group())
        confidence = 0.98 if _validate_cnpj(digits) else 0.6
        out.append(
            {
                "start": m.start(), "end": m.end(), "text": m.group(),
                "entity_type": "CNPJ", "category": DataCategory.PERSONAL,
                "confidence": confidence,
            }
        )
    for m in _CNPJ_PLAIN_RE.finditer(text):
        digits = m.group()
        if _validate_cnpj(digits):
            out.append(
                {
                    "start": m.start(), "end": m.end(), "text": m.group(),
                    "entity_type": "CNPJ", "category": DataCategory.PERSONAL,
                    "confidence": 0.9,
                }
            )
    return out


def _match_email(text: str) -> list[dict[str, Any]]:
    return [
        {
            "start": m.start(), "end": m.end(), "text": m.group(),
            "entity_type": "EMAIL", "category": DataCategory.PERSONAL,
            "confidence": 0.97,
        }
        for m in _EMAIL_RE.finditer(text)
    ]


def _match_cep(text: str) -> list[dict[str, Any]]:
    out = []
    for m in _CEP_FORMATTED_RE.finditer(text):
        out.append(
            {
                "start": m.start(), "end": m.end(), "text": m.group(),
                "entity_type": "CEP", "category": DataCategory.PERSONAL,
                "confidence": 0.9,
            }
        )
    for m in _CEP_PLAIN_RE.finditer(text):
        window_start = max(0, m.start() - 15)
        if _CEP_CONTEXT_RE.search(text[window_start:m.start()]):
            out.append(
                {
                    "start": m.start(), "end": m.end(), "text": m.group(),
                    "entity_type": "CEP", "category": DataCategory.PERSONAL,
                    "confidence": 0.7,
                }
            )
    return out


def _match_phone(text: str) -> list[dict[str, Any]]:
    out = []
    for m in _PHONE_WITH_DDD_RE.finditer(text):
        raw = m.group()
        digits = re.sub(r"\D", "", raw)
        has_explicit_format = any(ch in raw for ch in "()+-. ")
        if has_explicit_format:
            confidence = 0.85
        else:
            # Dígitos "crus" (sem separador): só aceita se tiver o formato
            # plausível de DDD (11-99) + celular (9 na 3ª posição) ou fixo.
            if len(digits) not in (10, 11):
                continue
            ddd_ok = 11 <= int(digits[:2]) <= 99
            if not ddd_ok:
                continue
            if len(digits) == 11 and digits[2] != "9":
                continue
            confidence = 0.7
        out.append(
            {
                "start": m.start(), "end": m.end(), "text": raw,
                "entity_type": "TELEFONE", "category": DataCategory.PERSONAL,
                "confidence": confidence,
            }
        )
    for m in _PHONE_NO_DDD_RE.finditer(text):
        out.append(
            {
                "start": m.start(), "end": m.end(), "text": m.group(),
                "entity_type": "TELEFONE", "category": DataCategory.PERSONAL,
                "confidence": 0.55,
            }
        )
    return out


def _match_rg(text: str) -> list[dict[str, Any]]:
    out = []
    for kw in _RG_KEYWORD_RE.finditer(text):
        window = text[kw.end():kw.end() + 20]
        num = _RG_NUMBER_RE.match(window)
        if num:
            start = kw.end() + num.start()
            end = kw.end() + num.end()
            out.append(
                {
                    "start": start, "end": end, "text": num.group(),
                    "entity_type": "RG", "category": DataCategory.PERSONAL,
                    "confidence": 0.85,
                }
            )
    return out


def _match_birthdate(text: str) -> list[dict[str, Any]]:
    out = []
    for kw in _BIRTHDATE_KEYWORD_RE.finditer(text):
        window = text[kw.end():kw.end() + 40]
        date_m = _DATE_RE.search(window)
        if date_m:
            start = kw.end() + date_m.start()
            end = kw.end() + date_m.end()
            out.append(
                {
                    "start": start, "end": end, "text": date_m.group(),
                    "entity_type": "DATA_NASCIMENTO",
                    "category": DataCategory.PERSONAL, "confidence": 0.85,
                }
            )
    return out


def _match_names(text: str) -> list[dict[str, Any]]:
    out = []
    for m in _NAME_RE.finditer(text):
        words = m.group().split()
        if any(w[0].isupper() and _fold(w) in _NAME_STOPWORDS_FOLDED for w in words):
            continue
        # Heurística "fora de início de frase": ignora se o match começa no
        # início absoluto do texto ou logo após pontuação de fim de frase.
        start = m.start()
        prefix = text[max(0, start - 2):start]
        if start == 0 or re.search(r"[.!?\n]\s*$", prefix):
            continue
        out.append(
            {
                "start": m.start(), "end": m.end(), "text": m.group(),
                "entity_type": "NOME", "category": DataCategory.PERSONAL,
                "confidence": 0.55,
            }
        )
    return out


# Tradução acento -> letra base ASCII, aplicada sobre string já em minúsculo
# (mantém o mesmo número de caracteres, então os offsets continuam válidos
# no texto original). Necessário porque texto real em português brasileiro
# frequentemente aparece SEM acentuação (WhatsApp, formulários, logs mal
# codificados) — sem isso, "diagnostico de depressao" (sem acento) não
# bateria com a palavra-chave "diagnóstico"/"depressão", gerando falso
# negativo num cenário comum.
_ACCENT_FOLD_MAP = str.maketrans(
    "áàâãäéèêëíìîïóòôõöúùûüç",
    "aaaaaeeeeiiiiooooouuuuc",
)


def _fold(s: str) -> str:
    """Minúsculo + remoção de acento, preservando o comprimento da string."""
    return s.lower().translate(_ACCENT_FOLD_MAP)


# Versão "fold" da stopword list de nomes, para casar com texto sem acento.
_NAME_STOPWORDS_FOLDED = {_fold(w) for w in _NAME_STOPWORDS}


def _match_sensitive_keywords(text: str) -> list[dict[str, Any]]:
    out = []
    folded_text = _fold(text)
    for entity_type, keywords in _SENSITIVE_KEYWORDS.items():
        for kw in keywords:
            pattern = re.compile(r"\b" + re.escape(_fold(kw)) + r"\b")
            for m in pattern.finditer(folded_text):
                out.append(
                    {
                        # _fold() preserva o comprimento 1:1, então os
                        # offsets do match em folded_text são válidos no
                        # texto original — usamos o texto original (com
                        # acento/caixa originais) como text_span.
                        "start": m.start(), "end": m.end(),
                        "text": text[m.start():m.end()],
                        "entity_type": entity_type,
                        "category": DataCategory.SENSITIVE,
                        "confidence": 0.65,
                    }
                )
    return out


# ---------------------------------------------------------------------------
# Enriquecimento opcional via spaCy (NUNCA obrigatório)
# ---------------------------------------------------------------------------

_NLP_CACHE: dict[str, Any] = {}


def _get_spacy_nlp() -> Any:
    """Carrega o modelo spaCy pt_core_news_sm em best-effort, com cache.

    Retorna None se spaCy ou o modelo não estiverem disponíveis — o caminho
    regex nunca depende deste retorno para funcionar.
    """
    if "nlp" not in _NLP_CACHE:
        try:
            import spacy  # type: ignore

            _NLP_CACHE["nlp"] = spacy.load("pt_core_news_sm")
        except Exception:
            _NLP_CACHE["nlp"] = None
    return _NLP_CACHE["nlp"]


def _match_names_spacy(
    text: str, occupied: list[tuple[int, int]]
) -> list[dict[str, Any]]:
    """Enriquecimento opcional: entidades PER via spaCy NER, fora do já
    coberto pela heurística regex. Best-effort — nunca lança exceção."""
    out: list[dict[str, Any]] = []
    try:
        nlp = _get_spacy_nlp()
        if nlp is None:
            return out
        doc = nlp(text)
        for ent in doc.ents:
            if ent.label_ != "PER":
                continue
            if any(
                not (ent.end_char <= s or ent.start_char >= e)
                for s, e in occupied
            ):
                continue
            out.append(
                {
                    "start": ent.start_char, "end": ent.end_char,
                    "text": ent.text, "entity_type": "NOME_NER_SPACY",
                    "category": DataCategory.PERSONAL, "confidence": 0.8,
                }
            )
    except Exception:
        return out
    return out


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------


def detect(text: str) -> PIIDetectionResult:
    """Detecta dados pessoais e sensíveis em texto livre em português.

    Caminho crítico 100% offline e determinístico via regex (CPF, CNPJ, RG,
    e-mail, telefone, CEP, data de nascimento) + heurística leve de nomes
    próprios, mais classificação de menções a dado sensível (LGPD Art. 5º,
    II) por palavra-chave. Enriquecimento opcional via spaCy roda em
    best-effort e nunca é necessário para o resultado ser válido.

    Args:
        text: texto livre em português a ser analisado.

    Returns:
        PIIDetectionResult (ver shared/schemas.py) com a lista de achados,
        a flag has_sensitive_data e um resumo textual.
    """
    if not text:
        return PIIDetectionResult(findings=[], has_sensitive_data=False, summary="0 achado(s).")

    candidates: list[dict[str, Any]] = []
    candidates += _match_cpf(text)
    candidates += _match_cnpj(text)
    candidates += _match_email(text)
    candidates += _match_cep(text)
    candidates += _match_phone(text)
    candidates += _match_rg(text)
    candidates += _match_birthdate(text)
    candidates += _match_names(text)

    resolved = _resolve_overlaps(candidates)

    # Enriquecimento opcional (spaCy) roda depois, só preenchendo lacunas
    # não cobertas pelo caminho regex.
    occupied = [(c["start"], c["end"]) for c in resolved]
    spacy_findings = _match_names_spacy(text, occupied)
    resolved = _resolve_overlaps(resolved + spacy_findings) if spacy_findings else resolved

    # Menções a dado sensível não competem por span com o restante (podem
    # se sobrepor a um nome/CPF, ex. "João tem HIV") — tratadas à parte.
    sensitive = _match_sensitive_keywords(text)

    findings = [
        PIIFinding(
            entity_type=c["entity_type"],
            text_span=c["text"],
            start=c["start"],
            end=c["end"],
            category=c["category"],
            confidence=c["confidence"],
        )
        for c in resolved
    ] + [
        PIIFinding(
            entity_type=c["entity_type"],
            text_span=c["text"],
            start=c["start"],
            end=c["end"],
            category=c["category"],
            confidence=c["confidence"],
        )
        for c in sensitive
    ]
    findings.sort(key=lambda f: f.start)

    has_sensitive = any(f.category == DataCategory.SENSITIVE for f in findings)

    counts: dict[str, int] = {}
    for f in findings:
        counts[f.entity_type] = counts.get(f.entity_type, 0) + 1
    summary_parts = ", ".join(f"{k}={v}" for k, v in counts.items())
    summary = f"{len(findings)} achado(s)" + (f" — {summary_parts}" if summary_parts else "")

    return PIIDetectionResult(
        findings=findings, has_sensitive_data=has_sensitive, summary=summary
    )
