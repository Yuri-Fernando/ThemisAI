"""Prompt Security Scanner — Themis AI.

Scanner 100% offline e determinístico para detectar tentativas de manipulação
de prompts (prompt injection, jailbreak, exfiltração de dados sensíveis e
ofuscação de payload) em texto enviado a um LLM.

Abordagem: heurística baseada em regex categorizadas por técnica de ataque.
Não há chamada de rede, não há modelo de ML — ver CHANGELOG.md e o notebook
de dev-log (notebooks/prompt_security_dev_log.ipynb) para a justificativa
dessa escolha de design e suas limitações conhecidas.

REGRA: os tipos de retorno vêm de shared/schemas.py (PromptSecurityFinding,
PromptSecurityResult). Este módulo nunca redefine esses contratos.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from shared.schemas import PromptSecurityFinding, PromptSecurityResult, RiskLevel

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

#: Limiar documentado: score >= SAFE_THRESHOLD é considerado seguro (is_safe=True).
#: 0.5 foi escolhido de forma que UM ÚNICO achado de severidade MEDIUM, HIGH ou
#: CRITICAL já seja suficiente para classificar o prompt como inseguro — a
#: intenção do scanner é "erra para o lado da cautela" (falso positivo é
#: preferível a deixar passar uma tentativa clara de manipulação). Apenas um
#: único achado LOW isolado (ex: menção solta a "decodifique em base64", sem
#: nenhum outro sinal) mantém o prompt como seguro. Ajustável conforme
#: feedback operacional.
SAFE_THRESHOLD = 0.5

#: Peso subtraído do score (que começa em 1.0) por achado único, por severidade.
#: Achados repetidos do MESMO padrão não são contados múltiplas vezes (ver
#: deduplicação por `(technique, label)` em `scan`), mas padrões diferentes
#: acumulam peso. Pesos de MEDIUM/HIGH/CRITICAL são > 0.5 propositalmente,
#: para que qualquer achado isolado dessas severidades já cruze o
#: SAFE_THRESHOLD sozinho.
SEVERITY_WEIGHT: dict[RiskLevel, float] = {
    RiskLevel.LOW: 0.15,
    RiskLevel.MEDIUM: 0.55,
    RiskLevel.HIGH: 0.75,
    RiskLevel.CRITICAL: 0.95,
}


@dataclass(frozen=True)
class _Rule:
    technique: str
    severity: RiskLevel
    pattern: re.Pattern[str]
    label: str  # descrição curta usada em matched_pattern


def _rule(technique: str, severity: RiskLevel, label: str, regex: str) -> _Rule:
    return _Rule(
        technique=technique,
        severity=severity,
        pattern=re.compile(regex, re.IGNORECASE | re.UNICODE),
        label=label,
    )


# ---------------------------------------------------------------------------
# Regras — prompt_injection
# ---------------------------------------------------------------------------
# Tentativas de sobrescrever ou desconsiderar as instruções do system prompt.

_PROMPT_INJECTION_RULES: list[_Rule] = [
    _rule(
        "prompt_injection",
        RiskLevel.HIGH,
        "ignore_previous_instructions",
        r"ignor[ae]\s+(todas?\s+(as\s+)?|as\s+|all\s+|the\s+)?instru[çc][õo]es\s+(anteriores|acima)"
        r"|ignore\s+(all\s+|the\s+)?previous\s+instructions"
        r"|ignore\s+(all\s+|the\s+)?prior\s+instructions",
    ),
    _rule(
        "prompt_injection",
        RiskLevel.HIGH,
        "disregard_everything_above",
        r"desconsider[ae]\s+tudo\s*(o que foi dito\s*)?(acima|anterior)"
        r"|disregard\s+(everything|all)\s+(above|previous)",
    ),
    _rule(
        "prompt_injection",
        RiskLevel.MEDIUM,
        "you_are_now_persona_override",
        r"voc[eê]\s+agora\s+[ée]\s"
        r"|you\s+are\s+now\s+(a|an|my)\b",
    ),
    _rule(
        "prompt_injection",
        RiskLevel.HIGH,
        "forget_your_rules",
        r"esque[çc]a\s+(suas|todas\s+as|as)\s+regras"
        r"|forget\s+(your|all)\s+(rules|instructions|guidelines)",
    ),
    _rule(
        "prompt_injection",
        RiskLevel.CRITICAL,
        "overwrite_system_prompt",
        r"sobrescrev[ae]\s+(o\s+)?system\s*prompt"
        r"|overwrite\s+(the\s+)?system\s*prompt"
        r"|substitua\s+(o\s+)?system\s*prompt",
    ),
    _rule(
        "prompt_injection",
        RiskLevel.MEDIUM,
        "new_instructions_marker",
        r"\bnovas?\s+instru[çc][õo]es\s*:"
        r"|\bnew\s+instructions\s*:",
    ),
    _rule(
        "prompt_injection",
        RiskLevel.MEDIUM,
        "act_as_if_no_restrictions",
        r"aja\s+como\s+se\s+(voc[eê]\s+)?n[ãa]o\s+tivesse\s+(restri[çc][õo]es|regras)"
        r"|act\s+as\s+if\s+you\s+have\s+no\s+restrictions",
    ),
    _rule(
        "prompt_injection",
        RiskLevel.HIGH,
        "system_role_spoofing",
        r"\[?\s*system\s*\]?\s*:\s*(you\s+are|voc[eê]\s+[ée])",
    ),
]

# ---------------------------------------------------------------------------
# Regras — jailbreak
# ---------------------------------------------------------------------------
# Padrões conhecidos de personas/jailbreaks publicados e pedidos de bypass
# explícito de políticas de segurança/conteúdo.

_JAILBREAK_RULES: list[_Rule] = [
    _rule(
        "jailbreak",
        RiskLevel.CRITICAL,
        "dan_persona",
        r"\bdan\b.{0,30}(do\s+anything\s+now)"
        r"|do\s+anything\s+now",
    ),
    _rule(
        "jailbreak",
        RiskLevel.HIGH,
        "known_jailbreak_persona",
        r"\b(stan|aim|dude|dax)\s+(mode|persona)\b",
    ),
    _rule(
        "jailbreak",
        RiskLevel.HIGH,
        "developer_mode",
        r"modo\s+(desenvolvedor|dev)\b"
        r"|developer\s+mode",
    ),
    _rule(
        "jailbreak",
        RiskLevel.HIGH,
        "respond_without_filters",
        r"responda\s+sem\s+(filtros|restri[çc][õo]es|censura)"
        r"|without\s+any\s+(filters|restrictions|limitations)"
        r"|sem\s+filtro\s+nenhum",
    ),
    _rule(
        "jailbreak",
        RiskLevel.MEDIUM,
        "roleplay_bypass",
        r"finja\s+que\s+(voc[eê]\s+)?(n[ãa]o\s+tem|est[aá]\s+sem)\s+(regras|pol[ií]ticas|filtros)"
        r"|pretend\s+(you\s+are|to\s+be)\s+an?\s+ai\s+(with\s+no|without)\s+(guidelines|restrictions|rules)"
        r"|roleplay\s+as\s+.{0,40}(no\s+rules|sem\s+regras)",
    ),
    _rule(
        "jailbreak",
        RiskLevel.MEDIUM,
        "explicit_jailbreak_mention",
        r"\bjailbreak\b",
    ),
    _rule(
        "jailbreak",
        RiskLevel.MEDIUM,
        "opposite_day",
        r"opposite\s+day\b"
        r"|dia\s+do\s+contr[aá]rio",
    ),
]

# ---------------------------------------------------------------------------
# Regras — pii_exfiltration
# ---------------------------------------------------------------------------
# Pedidos para revelar dados de treinamento, system prompt, segredos ou
# dados de outros usuários.

_PII_EXFILTRATION_RULES: list[_Rule] = [
    _rule(
        "pii_exfiltration",
        RiskLevel.HIGH,
        "reveal_system_prompt",
        r"revele?\s+(seu\s+|o\s+)?system\s*prompt"
        r"|mostre?\s+(suas?\s+)?instru[çc][õo]es\s+(originais|completas|internas)"
        r"|reveal\s+your\s+system\s*prompt"
        r"|show\s+me\s+your\s+(system\s*prompt|instructions)",
    ),
    _rule(
        "pii_exfiltration",
        RiskLevel.MEDIUM,
        "reveal_training_data",
        r"dados\s+de\s+treinamento"
        r"|training\s+data\s+(you\s+were\s+trained\s+on|used\s+to\s+train)"
        r"|repita\s+(exemplos\s+de\s+)?seus\s+dados\s+de\s+treinamento",
    ),
    _rule(
        "pii_exfiltration",
        RiskLevel.CRITICAL,
        "reveal_secrets_keys",
        r"(revele?|mostre?|qual\s+[ée])\s+(a\s+|sua\s+)*(chave\s+de\s+api|api\s*key|senha|token\s+secreto|secret\s+key)"
        r"|reveal\s+(your\s+)?(api\s*key|password|secret)",
    ),
    _rule(
        "pii_exfiltration",
        RiskLevel.CRITICAL,
        "other_users_data",
        r"dados\s+(\w+\s+)?de\s+outr[oa]s?\s+usu[aá]rios?"
        r"|informa[çc][õo]es\s+(\w+\s+)?de\s+outr[oa]\s+usu[aá]rio"
        r"|other\s+users?[''`]?\s+(data|information|conversations)",
    ),
    _rule(
        "pii_exfiltration",
        RiskLevel.HIGH,
        "print_env_vars",
        r"vari[aá]veis\s+de\s+ambiente"
        r"|environment\s+variables"
        r"|print(ar)?\s+env\b",
    ),
]

# ---------------------------------------------------------------------------
# Regras — obfuscation
# ---------------------------------------------------------------------------
# Payload disfarçado (base64/hex) ou uso excessivo de caracteres invisíveis
# (zero-width) para esconder instrução.

_ZERO_WIDTH_CHARS = "​‌‍⁠﻿"

_OBFUSCATION_RULES: list[_Rule] = [
    _rule(
        "obfuscation",
        RiskLevel.MEDIUM,
        "long_base64_blob",
        r"(?<![A-Za-z0-9+/=])[A-Za-z0-9+/]{40,}={0,2}(?![A-Za-z0-9+/=])",
    ),
    _rule(
        "obfuscation",
        RiskLevel.MEDIUM,
        "long_hex_blob",
        r"(?<![0-9a-fA-F])(?:0x)?[0-9a-fA-F]{32,}(?![0-9a-fA-F])",
    ),
    _rule(
        "obfuscation",
        RiskLevel.LOW,
        "decode_instruction_hint",
        r"decodifiqu[ae]\s+(isso\s+|este\s+texto\s+)?em\s+base64"
        r"|decode\s+(this|the\s+following)\s+(from\s+)?base64"
        r"|decode\s+.{0,20}hex\b",
    ),
]


def _zero_width_finding(prompt: str) -> PromptSecurityFinding | None:
    """Detecta uso anômalo de caracteres zero-width/invisíveis (>=3 ocorrências)."""
    count = sum(prompt.count(ch) for ch in _ZERO_WIDTH_CHARS)
    if count >= 3:
        return PromptSecurityFinding(
            technique="obfuscation",
            matched_pattern="excessive_zero_width_chars",
            severity=RiskLevel.MEDIUM,
        )
    return None


_ALL_RULES: list[_Rule] = [
    *_PROMPT_INJECTION_RULES,
    *_JAILBREAK_RULES,
    *_PII_EXFILTRATION_RULES,
    *_OBFUSCATION_RULES,
]


def _compute_score(findings: list[PromptSecurityFinding]) -> float:
    """1.0 (seguro) menos o peso de severidade de cada achado único, piso em 0.0.

    Achados são contados por (technique, matched_pattern) já deduplicados em
    `scan`, então repetir a mesma frase várias vezes no prompt não infla o
    score artificialmente — mas padrões diferentes (mesmo da mesma técnica)
    acumulam, refletindo um prompt com múltiplos vetores de ataque.
    """
    penalty = sum(SEVERITY_WEIGHT[f.severity] for f in findings)
    return max(0.0, round(1.0 - penalty, 4))


def scan(prompt: str) -> PromptSecurityResult:
    """Varre `prompt` em busca de técnicas de manipulação conhecidas.

    100% offline e determinístico: apenas regex/heurística, sem chamadas de
    rede e sem modelo de ML. Ver notebooks/prompt_security_dev_log.ipynb para
    a justificativa dessa escolha e as limitações conhecidas de evasão.

    Args:
        prompt: texto a ser analisado (ex: entrada de usuário para um LLM).

    Returns:
        PromptSecurityResult (shared/schemas.py) com a lista de achados,
        `is_safe` (score >= SAFE_THRESHOLD) e `score` em [0.0, 1.0].
    """
    if not prompt or not prompt.strip():
        return PromptSecurityResult(findings=[], is_safe=True, score=1.0)

    findings: list[PromptSecurityFinding] = []
    seen: set[tuple[str, str]] = set()

    for rule in _ALL_RULES:
        if rule.pattern.search(prompt):
            key = (rule.technique, rule.label)
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                PromptSecurityFinding(
                    technique=rule.technique,
                    matched_pattern=rule.label,
                    severity=rule.severity,
                )
            )

    zw = _zero_width_finding(prompt)
    if zw is not None:
        findings.append(zw)

    score = _compute_score(findings)
    is_safe = score >= SAFE_THRESHOLD

    return PromptSecurityResult(findings=findings, is_safe=is_safe, score=score)
