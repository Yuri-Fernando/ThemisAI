"""Testes do teste de significância estatística do Fairness Audit (V5, item 12)."""
from __future__ import annotations

import pytest

from core.fairness_audit.significance import chi_square_significance
from shared.schemas import FairnessSignificanceResult


def _records(n_a_favorable, n_a_total, n_b_favorable, n_b_total):
    records = []
    for i in range(n_a_total):
        records.append({"outcome": i < n_a_favorable, "group": "A"})
    for i in range(n_b_total):
        records.append({"outcome": i < n_b_favorable, "group": "B"})
    return records


def test_large_clear_disparity_is_significant():
    # Amostra grande, disparidade clara -- deve ser estatisticamente significativa.
    records = _records(90, 100, 40, 100)
    result = chi_square_significance(records, "outcome", "group")
    assert isinstance(result, FairnessSignificanceResult)
    assert result.significant is True
    assert result.p_value < 0.05


def test_small_sample_same_rate_not_significant():
    # Amostra pequena, mesma taxa -- não deveria ser significativo.
    records = _records(2, 4, 2, 4)
    result = chi_square_significance(records, "outcome", "group")
    assert result.significant is False


def test_small_sample_disparity_may_not_be_significant():
    # Amostra pequena (n=5 por grupo) com disparidade -- ilustra exatamente a
    # limitação que audit_fairness (sozinho) não capturava: o disparate impact
    # pode acusar "injusto" mesmo quando a amostra é pequena demais para
    # sustentar a conclusão estatisticamente.
    from core.fairness_audit.engine import audit_fairness

    records = _records(4, 5, 1, 5)  # 80% vs 20% -- disparate impact reprovaria
    fairness_result = audit_fairness(records, "outcome", "group", favorable_outcome=True)
    assert fairness_result.overall_fair is False  # regra dos 80% acusa disparidade

    significance_result = chi_square_significance(records, "outcome", "group")
    # Com n=5 por grupo, a significância estatística é bem mais fraca que a
    # regra dos 80% sozinha sugeriria -- exatamente o ponto do módulo.
    assert significance_result.p_value > 0.01  # não é um resultado esmagador


def test_custom_alpha():
    records = _records(90, 100, 40, 100)
    strict = chi_square_significance(records, "outcome", "group", alpha=0.001)
    lenient = chi_square_significance(records, "outcome", "group", alpha=0.5)
    assert strict.p_value == lenient.p_value  # mesmo teste estatístico
    assert lenient.significant is True


def test_empty_records_raises():
    with pytest.raises(ValueError):
        chi_square_significance([], "outcome", "group")


def test_single_group_raises():
    records = [{"outcome": True, "group": "A"}, {"outcome": False, "group": "A"}]
    with pytest.raises(ValueError):
        chi_square_significance(records, "outcome", "group")


def test_three_groups_supported():
    records = (
        [{"outcome": i < 80, "group": "A"} for i in range(100)]
        + [{"outcome": i < 78, "group": "B"} for i in range(100)]
        + [{"outcome": i < 20, "group": "C"} for i in range(100)]
    )
    result = chi_square_significance(records, "outcome", "group")
    assert result.degrees_of_freedom == 2  # (3 grupos - 1) * (2 colunas - 1)
    assert result.significant is True


def test_summary_mentions_significance_verdict():
    records = _records(90, 100, 40, 100)
    result = chi_square_significance(records, "outcome", "group")
    assert "SIGNIFICATIVA" in result.summary
