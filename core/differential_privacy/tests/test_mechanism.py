"""Testes do Differential Privacy — ruído real de Laplace (numpy), seedado
para reprodutibilidade."""
from __future__ import annotations

import pytest

from core.differential_privacy.mechanism import (
    PrivacyBudget,
    advanced_composition_epsilon,
    laplace_mechanism,
    private_count,
    private_mean,
)
from shared.schemas import DPQueryResult


def test_laplace_mechanism_adds_real_noise():
    result = laplace_mechanism(true_value=100.0, sensitivity=1.0, epsilon=1.0, seed=42)
    assert isinstance(result, DPQueryResult)
    assert result.true_value == 100.0
    assert result.noisy_value != 100.0  # ruído real foi adicionado


def test_laplace_mechanism_deterministic_with_seed():
    r1 = laplace_mechanism(100.0, 1.0, 1.0, seed=7)
    r2 = laplace_mechanism(100.0, 1.0, 1.0, seed=7)
    assert r1.noisy_value == r2.noisy_value


def test_laplace_mechanism_different_seeds_differ():
    r1 = laplace_mechanism(100.0, 1.0, 1.0, seed=1)
    r2 = laplace_mechanism(100.0, 1.0, 1.0, seed=2)
    assert r1.noisy_value != r2.noisy_value


def test_lower_epsilon_means_more_noise_on_average():
    # Menor epsilon = mais privacidade = mais ruído (escala maior). Compara
    # o desvio absoluto médio ao longo de várias amostras (não uma única
    # amostra, que seria ruidosa demais para comparar de forma estável).
    import statistics

    high_privacy_devs = [abs(laplace_mechanism(0.0, 1.0, epsilon=0.1, seed=i).noisy_value) for i in range(200)]
    low_privacy_devs = [abs(laplace_mechanism(0.0, 1.0, epsilon=10.0, seed=i).noisy_value) for i in range(200)]
    assert statistics.mean(high_privacy_devs) > statistics.mean(low_privacy_devs)


def test_invalid_epsilon_raises():
    with pytest.raises(ValueError):
        laplace_mechanism(10.0, sensitivity=1.0, epsilon=0.0)


def test_invalid_sensitivity_raises():
    with pytest.raises(ValueError):
        laplace_mechanism(10.0, sensitivity=-1.0, epsilon=1.0)


def test_private_count_close_to_true_count_with_high_epsilon():
    records = list(range(100))
    result = private_count(records, predicate=lambda r: r % 2 == 0, epsilon=1000.0, seed=1)
    assert result.true_value == 50.0
    assert abs(result.noisy_value - 50.0) < 1.0  # epsilon alto -> ruído desprezível


def test_private_mean_clips_outliers():
    values = [5.0, 5.0, 5.0, 1000.0]  # outlier extremo
    result = private_mean(values, lower_bound=0.0, upper_bound=10.0, epsilon=1000.0, seed=1)
    # Com clipping em [0, 10], o outlier vira 10.0 -> média real = (5+5+5+10)/4 = 6.25
    assert result.true_value == pytest.approx(6.25)


def test_private_mean_empty_values_raises():
    with pytest.raises(ValueError):
        private_mean([], 0.0, 10.0)


def test_privacy_budget_tracks_spending():
    budget = PrivacyBudget(total_epsilon=1.0)
    budget.spend(0.3)
    budget.spend(0.4)
    assert budget.spent == pytest.approx(0.7)
    assert budget.remaining == pytest.approx(0.3)


def test_privacy_budget_raises_when_exceeded():
    budget = PrivacyBudget(total_epsilon=1.0)
    budget.spend(0.8)
    with pytest.raises(ValueError):
        budget.spend(0.5)


def test_privacy_budget_invalid_total_raises():
    with pytest.raises(ValueError):
        PrivacyBudget(total_epsilon=0.0)


def test_privacy_budget_invalid_spend_amount_raises():
    budget = PrivacyBudget(total_epsilon=1.0)
    with pytest.raises(ValueError):
        budget.spend(-0.1)


# --- advanced_composition_epsilon (V5, item 11) ---

def test_advanced_composition_grows_slower_than_naive_sum_for_large_k():
    # Composição sequencial simples (naive): k * epsilon.
    # Composição avançada real (Dwork et al. 2010) deve ser bem menor para k grande.
    epsilon_per_query = 0.1
    k = 100
    delta = 1e-5
    naive_total = k * epsilon_per_query
    advanced_total = advanced_composition_epsilon(epsilon_per_query, k, delta)
    assert advanced_total < naive_total


def test_advanced_composition_matches_known_formula():
    import math

    epsilon, k, delta = 0.05, 50, 1e-6
    expected = math.sqrt(2 * k * math.log(1 / delta)) * epsilon + k * epsilon * (math.exp(epsilon) - 1)
    assert advanced_composition_epsilon(epsilon, k, delta) == pytest.approx(expected)


def test_advanced_composition_increases_with_k():
    low_k = advanced_composition_epsilon(0.1, 10, 1e-5)
    high_k = advanced_composition_epsilon(0.1, 100, 1e-5)
    assert high_k > low_k


def test_advanced_composition_invalid_epsilon_raises():
    with pytest.raises(ValueError):
        advanced_composition_epsilon(0.0, 10, 1e-5)


def test_advanced_composition_invalid_k_raises():
    with pytest.raises(ValueError):
        advanced_composition_epsilon(0.1, 0, 1e-5)


def test_advanced_composition_invalid_delta_raises():
    with pytest.raises(ValueError):
        advanced_composition_epsilon(0.1, 10, 0.0)
    with pytest.raises(ValueError):
        advanced_composition_epsilon(0.1, 10, 1.0)
