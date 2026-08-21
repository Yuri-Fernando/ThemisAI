"""Explainability Engine — motor genérico e determinístico de explicabilidade.

IMPORTANTE — isto NÃO é machine learning. Não há modelo treinado, não há
inferência estatística e não há "importância de feature" aprendida. O motor
é 100% determinístico: recebe um dicionário de fatores já calculados por
quem chama (`{nome_do_fator: contribuição_numérica}`), ordena esses fatores
por magnitude (|contribuição|, do maior para o menor) e gera uma narrativa
em português natural descrevendo essa ordem — nada além disso.

Papel no pipeline: este módulo é uma UTILIDADE GENÉRICA e standalone. Ele
NÃO importa nenhum outro módulo do projeto (além de `shared.schemas`, o
contrato compartilhado) e não conhece conceitos de domínio como PII,
política ou trust score — apenas números e texto livre. Outros módulos
(`trust_score`, `policy_engine`, `ripd_engine`, ...) são responsáveis por
calcular seus próprios fatores e injetar este motor via chamada direta de
`explain(...)`, usando o `ExplainabilityResult` retornado como parte do
seu próprio resultado (ver `shared.schemas.TrustScoreResult.explanation`).
Este módulo nunca importa, referencia ou tem qualquer acoplamento com esses
consumidores — a relação de dependência é sempre em uma única direção,
dos módulos de domínio para este motor.
"""
from __future__ import annotations

from shared.schemas import ExplainabilityResult

_DEFAULT_NO_FACTORS_TEMPLATE = (
    "Não há fatores registrados para explicar a decisão sobre '{subject}'."
)


def _format_contribution(value: float) -> str:
    """Formata a contribuição numérica com sinal explícito (+/-), 2 casas decimais."""
    return f"+{value:.2f}" if value >= 0 else f"{value:.2f}"


def _direction_phrase(value: float) -> str:
    """Descreve o efeito da contribuição em português natural."""
    if value > 0:
        return "aumentando o resultado"
    if value < 0:
        return "reduzindo o resultado"
    return "sem impacto líquido sobre o resultado"


def _build_body(ordered_factors: list[tuple[str, float]]) -> str:
    """Monta a lista de cláusulas em ordem de importância (maior |contribuição| primeiro)."""
    clauses: list[str] = []
    for index, (name, value) in enumerate(ordered_factors):
        lead = "principalmente influenciada por" if index == 0 else "seguido por"
        clauses.append(
            f"{lead} '{name}' (contribuição de {_format_contribution(value)}, "
            f"{_direction_phrase(value)})"
        )
    return "; ".join(clauses)


def _compose_narrative(subject: str, body: str, narrative_template: str | None) -> str:
    """Compõe a narrativa final, usando `narrative_template` como molde/prefixo se fornecido.

    Se o template contiver os placeholders `{subject}` e/ou `{body}`, eles são
    substituídos (modo "molde"). Caso contrário, o template é usado como frase de
    abertura e a explicação padrão dos fatores é anexada em seguida (modo "prefixo").
    """
    if narrative_template is None:
        return f"A decisão sobre '{subject}' foi {body}."

    if "{subject}" in narrative_template or "{body}" in narrative_template:
        try:
            return narrative_template.format(subject=subject, body=body)
        except (KeyError, IndexError):
            pass  # template malformado: cai para o modo "prefixo" abaixo

    prefix = narrative_template.rstrip()
    if not prefix.endswith((".", ":", ";", "!", "?")):
        prefix += ":"
    return f"{prefix} a decisão foi {body}."


def _compose_empty_narrative(subject: str, narrative_template: str | None) -> str:
    """Narrativa usada quando `factors` é um dicionário vazio."""
    if narrative_template is None:
        return _DEFAULT_NO_FACTORS_TEMPLATE.format(subject=subject)

    if "{subject}" in narrative_template or "{body}" in narrative_template:
        try:
            return narrative_template.format(subject=subject, body="nenhum fator registrado")
        except (KeyError, IndexError):
            pass  # template malformado: cai para o modo "prefixo" abaixo

    prefix = narrative_template.rstrip()
    if not prefix.endswith((".", ":", ";", "!", "?")):
        prefix += ":"
    return f"{prefix} não há fatores registrados para esta decisão."


def explain(
    factors: dict[str, float],
    subject: str,
    narrative_template: str | None = None,
) -> ExplainabilityResult:
    """Gera uma explicação determinística e legível para um conjunto de fatores numéricos.

    Este é um motor de regras, NÃO machine learning: a "importância" de cada fator é
    simplesmente sua magnitude (`abs(valor)`), fornecida por quem chama a função.

    Args:
        factors: dicionário `{nome_do_fator: contribuição}`. A contribuição pode ser
            positiva (empurra a decisão em uma direção) ou negativa (empurra na
            direção oposta). Pode ser um dicionário vazio.
        subject: string livre descrevendo o que está sendo explicado
            (ex.: "trust_score", "policy_decision:pol_health_data").
        narrative_template: molde opcional para a narrativa. Se contiver os
            placeholders `{subject}` e/ou `{body}`, eles são substituídos
            (`body` é a lista de fatores já formatada). Caso contrário, é usado
            como frase de abertura e a explicação padrão é anexada a ele.
            Se `None`, usa o template padrão do motor.

    Returns:
        `ExplainabilityResult` (de `shared.schemas`) com `subject`, os `factors`
        originais (não modificados) e a `narrative` gerada.
    """
    if not factors:
        narrative = _compose_empty_narrative(subject, narrative_template)
        return ExplainabilityResult(subject=subject, factors={}, narrative=narrative)

    ordered_factors = sorted(factors.items(), key=lambda item: abs(item[1]), reverse=True)
    body = _build_body(ordered_factors)
    narrative = _compose_narrative(subject, body, narrative_template)

    return ExplainabilityResult(subject=subject, factors=dict(factors), narrative=narrative)
