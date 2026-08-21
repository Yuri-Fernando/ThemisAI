"""Differential Privacy — mecanismo de Laplace, o primitivo clássico e real
de privacidade diferencial (Dwork et al.), para consultas agregadas
(contagem, média) sobre dados sensíveis.

**Real, não simulado**: o ruído é amostrado de verdade de uma distribuição
de Laplace (`numpy.random.laplace`) calibrada pela sensibilidade da consulta
e pelo orçamento de privacidade `epsilon` — a mesma matemática usada em
implementações de produção (ex. a análise de privacidade do Census dos EUA
usa o mesmo mecanismo base). `seed` é aceito para reprodutibilidade em
testes; em uso real, nunca se fixa a seed (previsibilidade do ruído anula a
proteção).
"""
from __future__ import annotations

import math

import numpy as np

from shared.schemas import DPQueryResult


def laplace_mechanism(
    true_value: float,
    sensitivity: float,
    epsilon: float,
    seed: int | None = None,
) -> DPQueryResult:
    """Aplica o mecanismo de Laplace a `true_value`: soma ruído amostrado de
    `Laplace(0, sensitivity/epsilon)`.

    Args:
        true_value: o valor real da consulta agregada (ex. uma contagem).
        sensitivity: sensibilidade da consulta — quanto `true_value` pode
            mudar com a adição/remoção de um único registro (ex. `1.0` para
            contagem simples).
        epsilon: orçamento de privacidade (menor = mais ruído = mais
            privado; maior = menos ruído = menos privado). Precisa ser > 0.
        seed: opcional, só para reprodutibilidade em testes/demos.

    Returns:
        `DPQueryResult` com o valor real, o valor ruidoso e os parâmetros
        usados.

    Levanta:
        ValueError: se `epsilon <= 0` ou `sensitivity <= 0`.
    """
    if epsilon <= 0:
        raise ValueError("epsilon precisa ser > 0 (orçamento de privacidade inválido).")
    if sensitivity <= 0:
        raise ValueError("sensitivity precisa ser > 0.")

    rng = np.random.default_rng(seed)
    scale = sensitivity / epsilon
    noise = rng.laplace(loc=0.0, scale=scale)
    noisy_value = true_value + noise

    return DPQueryResult(
        mechanism="laplace",
        true_value=float(true_value),
        noisy_value=float(noisy_value),
        epsilon=float(epsilon),
        sensitivity=float(sensitivity),
    )


def private_count(
    records: list,
    predicate,
    sensitivity: float = 1.0,
    epsilon: float = 1.0,
    seed: int | None = None,
) -> DPQueryResult:
    """Contagem privada: aplica `predicate` a cada item de `records`, conta
    quantos são `True`, e retorna essa contagem com ruído de Laplace.
    """
    true_count = sum(1 for r in records if predicate(r))
    return laplace_mechanism(float(true_count), sensitivity=sensitivity, epsilon=epsilon, seed=seed)


def private_mean(
    values: list[float],
    lower_bound: float,
    upper_bound: float,
    epsilon: float = 1.0,
    seed: int | None = None,
) -> DPQueryResult:
    """Média privada de `values`, com clipping em `[lower_bound, upper_bound]`
    ANTES de calcular a média (necessário para ter uma sensibilidade finita
    e conhecida — sem clipping, um único outlier extremo tornaria a
    sensibilidade ilimitada, quebrando a garantia de privacidade).

    Sensibilidade usada: `(upper_bound - lower_bound) / len(values)` —
    trocar um único valor pelo extremo oposto do intervalo muda a média em
    no máximo isso.

    Levanta `ValueError` se `values` estiver vazio.
    """
    if not values:
        raise ValueError("private_mean requer ao menos um valor em `values`.")

    clipped = [min(max(v, lower_bound), upper_bound) for v in values]
    true_mean = sum(clipped) / len(clipped)
    sensitivity = (upper_bound - lower_bound) / len(clipped)
    return laplace_mechanism(true_mean, sensitivity=sensitivity, epsilon=epsilon, seed=seed)


def advanced_composition_epsilon(epsilon_per_query: float, k: int, delta: float) -> float:
    """Orçamento total de epsilon para `k` consultas, cada uma
    `epsilon_per_query`-DP, sob o **teorema de composição avançada** de
    Dwork, Rothblum e Vadhan (2010, "Boosting and Differential Privacy") —
    literatura real, fórmula real, não aproximação inventada:

        epsilon' = sqrt(2k · ln(1/delta)) · epsilon + k · epsilon · (e^epsilon - 1)

    A composição resultante é `(epsilon', k·delta_original + delta)-DP`. Para
    `k` grande, `epsilon'` cresce em `O(sqrt(k))`, bem mais devagar que a
    composição sequencial simples usada por `PrivacyBudget`
    (`O(k)` — soma linear) — é o ganho real de usar essa teoria em vez da
    composição básica, ao custo de aceitar uma folga `delta` (probabilidade
    pequena de falha da garantia) que a composição sequencial simples não
    precisa.

    Args:
        epsilon_per_query: epsilon de CADA consulta individual (assume-se
            que todas as `k` consultas usam o mesmo epsilon — é a hipótese
            do teorema; se as consultas tiverem epsilons diferentes, aplique
            o teorema separadamente por grupo homogêneo).
        k: número de consultas compostas.
        delta: folga de probabilidade aceita (tipicamente pequena, ex.
            `1e-5`) — precisa ser `0 < delta < 1`.

    Levanta `ValueError` se `epsilon_per_query <= 0`, `k <= 0`, ou `delta`
    fora de `(0, 1)`.
    """
    if epsilon_per_query <= 0:
        raise ValueError("epsilon_per_query precisa ser > 0.")
    if k <= 0:
        raise ValueError("k precisa ser > 0.")
    if not (0.0 < delta < 1.0):
        raise ValueError("delta precisa estar em (0, 1).")

    return math.sqrt(2 * k * math.log(1 / delta)) * epsilon_per_query + k * epsilon_per_query * (
        math.exp(epsilon_per_query) - 1
    )


class PrivacyBudget:
    """Rastreia o orçamento de privacidade (`epsilon` total) consumido por
    múltiplas consultas — composição sequencial simples (soma linear dos
    epsilons gastos), o modelo de composição básico da literatura de DP.
    """

    def __init__(self, total_epsilon: float) -> None:
        if total_epsilon <= 0:
            raise ValueError("total_epsilon precisa ser > 0.")
        self.total_epsilon = total_epsilon
        self._spent = 0.0

    @property
    def spent(self) -> float:
        return self._spent

    @property
    def remaining(self) -> float:
        return round(self.total_epsilon - self._spent, 10)

    def spend(self, epsilon: float) -> None:
        """Registra o gasto de `epsilon`. Levanta `ValueError` se exceder o
        orçamento total restante — nenhuma consulta é permitida "estourar"
        silenciosamente o orçamento.
        """
        if epsilon <= 0:
            raise ValueError("epsilon a gastar precisa ser > 0.")
        if epsilon > self.remaining + 1e-9:
            raise ValueError(
                f"Orçamento de privacidade excedido: tentando gastar {epsilon}, restam apenas {self.remaining}."
            )
        self._spent += epsilon
