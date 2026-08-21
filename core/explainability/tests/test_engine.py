"""Testes do motor de explicabilidade (`core/explainability/engine.py`)."""
from __future__ import annotations

from shared.schemas import ExplainabilityResult

from core.explainability.engine import explain


def test_returns_explainability_result_instance():
    result = explain({"a": 0.5}, subject="teste")
    assert isinstance(result, ExplainabilityResult)


def test_empty_factors_returns_appropriate_narrative():
    result = explain({}, subject="trust_score")
    assert result.subject == "trust_score"
    assert result.factors == {}
    assert "trust_score" in result.narrative
    # deve indicar claramente a ausência de fatores
    assert any(
        keyword in result.narrative.lower()
        for keyword in ("não há fatores", "nenhum fator", "sem fatores")
    )


def test_single_factor():
    result = explain({"unico_fator": -0.75}, subject="policy_decision:pol_x")
    assert result.factors == {"unico_fator": -0.75}
    assert "unico_fator" in result.narrative
    assert "-0.75" in result.narrative
    assert "principalmente" in result.narrative


def test_only_positive_factors():
    factors = {"idade_conta": 0.3, "historico_limpo": 0.6, "verificacao_2fa": 0.1}
    result = explain(factors, subject="trust_score")

    assert result.factors == factors
    # todos os fatores devem aparecer na narrativa
    for name in factors:
        assert name in result.narrative
    # sinais positivos explícitos
    assert "+0.60" in result.narrative
    assert "+0.30" in result.narrative
    assert "+0.10" in result.narrative
    assert "aumentando" in result.narrative
    assert "reduzindo" not in result.narrative


def test_only_negative_factors():
    factors = {"vazamento_anterior": -0.8, "atraso_resposta": -0.2}
    result = explain(factors, subject="trust_score")

    assert result.factors == factors
    assert "-0.80" in result.narrative
    assert "-0.20" in result.narrative
    assert "reduzindo" in result.narrative
    assert "aumentando" not in result.narrative


def test_mixed_positive_and_negative_factors():
    factors = {"dado_sensivel_detectado": -0.4, "base_legal_valida": 0.2, "consentimento": 0.05}
    result = explain(factors, subject="policy_decision:pol_health_data")

    assert "-0.40" in result.narrative
    assert "+0.20" in result.narrative
    assert "+0.05" in result.narrative
    assert "aumentando" in result.narrative
    assert "reduzindo" in result.narrative


def test_ordering_by_magnitude_descending_many_factors():
    factors = {
        "fator_pequeno": 0.05,
        "fator_gigante_negativo": -0.9,
        "fator_medio": 0.3,
        "fator_zero": 0.0,
        "fator_medio_negativo": -0.35,
        "fator_grande": 0.6,
    }
    result = explain(factors, subject="trust_score")

    # ordem esperada por |valor| decrescente:
    # fator_gigante_negativo (0.9) > fator_grande (0.6) > fator_medio_negativo (0.35)
    # > fator_medio (0.3) > fator_pequeno (0.05) > fator_zero (0.0)
    expected_order = [
        "fator_gigante_negativo",
        "fator_grande",
        "fator_medio_negativo",
        "fator_medio",
        "fator_pequeno",
        "fator_zero",
    ]
    # busca pelo nome entre aspas simples (como aparece na narrativa) para evitar
    # falso positivo de substring (ex: "fator_medio" é prefixo de "fator_medio_negativo")
    positions = [result.narrative.index(f"'{name}'") for name in expected_order]
    assert positions == sorted(positions), "fatores não estão em ordem de magnitude decrescente"

    # o primeiro da lista deve ser descrito como "principal"
    first_index = result.narrative.index("principalmente")
    gigante_index = result.narrative.index("'fator_gigante_negativo'")
    assert first_index < gigante_index

    # factors originais preservados (não modificados/reordenados como dict)
    assert result.factors == factors


def test_custom_narrative_template_as_prefix():
    result = explain(
        {"a": 0.5, "b": -0.2},
        subject="trust_score",
        narrative_template="Este é um resumo executivo customizado",
    )
    assert result.narrative.startswith("Este é um resumo executivo customizado")
    assert "a" in result.narrative
    assert "+0.50" in result.narrative


def test_custom_narrative_template_with_placeholders():
    result = explain(
        {"fator_x": 0.9},
        subject="ripd_risk",
        narrative_template="[{subject}] Resumo: {body}.",
    )
    assert result.narrative.startswith("[ripd_risk] Resumo:")
    assert "fator_x" in result.narrative
    assert "+0.90" in result.narrative


def test_custom_narrative_template_empty_factors():
    result = explain(
        {},
        subject="trust_score",
        narrative_template="Aviso especial de auditoria",
    )
    assert result.narrative.startswith("Aviso especial de auditoria")
    assert result.factors == {}


def test_subject_is_free_text_and_preserved():
    result = explain({"x": 1.0}, subject="qualquer:coisa/livre-123")
    assert result.subject == "qualquer:coisa/livre-123"


def test_negative_and_positive_zero_boundary_value():
    # valor exatamente 0.0 deve ser tratado como neutro, sem quebrar a ordenação
    result = explain({"neutro": 0.0, "impacto": 0.1}, subject="trust_score")
    assert "impacto" in result.narrative
    assert "neutro" in result.narrative
    impacto_index = result.narrative.index("impacto")
    neutro_index = result.narrative.index("neutro")
    assert impacto_index < neutro_index
