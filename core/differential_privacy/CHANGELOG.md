# Changelog — Differential Privacy

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Este módulo segue SemVer independente (`core/differential_privacy/`).

## [0.2.0] - 2026-08-21 — Composição avançada real (V5, item 11)

### Added
- `advanced_composition_epsilon(epsilon_per_query, k, delta) -> float` —
  teorema de composição avançada de Dwork, Rothblum e Vadhan (2010,
  "Boosting and Differential Privacy"): `sqrt(2k·ln(1/delta))·epsilon +
  k·epsilon·(e^epsilon - 1)`. Cresce em `O(sqrt(k))` para `k` consultas
  homogêneas, contra `O(k)` da composição sequencial simples de
  `PrivacyBudget` — fórmula real da literatura, não aproximação inventada.
- 6 testes novos: cresce mais devagar que a soma ingênua para `k` grande
  (100 consultas de epsilon=0.1: composição avançada ≈ muito menor que
  10.0 da soma simples); bate com a fórmula fechada calculada
  independentemente no teste; cresce com `k`; validação de parâmetros
  (`epsilon<=0`, `k<=0`, `delta` fora de `(0,1)`).

### Notes
- `PrivacyBudget` continua com composição sequencial simples por padrão —
  este é um utilitário adicional para quem precisa de um orçamento mais
  justo em cenários de muitas consultas homogêneas, não uma mudança de
  comportamento do que já existia.

## [0.1.0] - 2026-08-20

### Added

- `mechanism.py`:
  - `laplace_mechanism(true_value, sensitivity, epsilon, seed=None) ->
    DPQueryResult` — mecanismo de Laplace real (`numpy.random.laplace`),
    o primitivo clássico de privacidade diferencial (Dwork et al.).
  - `private_count(records, predicate, sensitivity=1.0, epsilon=1.0,
    seed=None)` e `private_mean(values, lower_bound, upper_bound,
    epsilon=1.0, seed=None)` (com clipping obrigatório para sensibilidade
    finita).
  - `PrivacyBudget` — rastreia gasto de `epsilon` por composição sequencial
    simples, levanta erro se exceder o orçamento.
- Contrato novo em `shared/schemas.py` (`DPQueryResult`).
- Suíte de testes pytest (`tests/test_mechanism.py`, 13 testes): ruído real
  adicionado; determinístico com seed; epsilon menor produz mais ruído em
  média (comparação estatística sobre 200 amostras, não uma amostra só);
  validação de parâmetros inválidos; `private_count`/`private_mean` com
  epsilon alto convergem para o valor real; clipping de outlier; orçamento
  de privacidade rastreia gasto e recusa estouro.

### Notes

- `seed` existe só para reprodutibilidade em testes/demos — em uso real,
  nunca se fixa a seed (ruído previsível anula a proteção de privacidade).
- Composição de orçamento é o modelo sequencial simples (soma linear de
  epsilons) — composição avançada (ex. teorema de composição avançada,
  privacidade Rényi) é TODO de onda futura se a precisão do orçamento
  se tornar crítica.
