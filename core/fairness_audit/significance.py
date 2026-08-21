"""Fairness Audit — teste de significância estatística real (V5, item 12).

`audit_fairness()` (`engine.py`) mede disparate impact/paridade demográfica,
mas não diz se a diferença observada é estatisticamente significativa ou só
ruído de amostra pequena — limitação documentada desde a v0.1.0. Este módulo
fecha essa lacuna com o **teste qui-quadrado de independência**
(`scipy.stats.chi2_contingency`), aplicado a uma tabela de contingência real
2xN (grupo x resultado favorável/desfavorável) — teste padrão da literatura
para essa pergunta exata: "a distribuição de resultados é independente do
grupo, ou há associação estatisticamente significativa?".
"""
from __future__ import annotations

from typing import Any

from scipy import stats

from shared.schemas import FairnessSignificanceResult

DEFAULT_ALPHA = 0.05


def chi_square_significance(
    records: list[dict[str, Any]],
    outcome_key: str,
    protected_attribute_key: str,
    favorable_outcome: Any = True,
    alpha: float = DEFAULT_ALPHA,
) -> FairnessSignificanceResult:
    """Testa se a associação entre `protected_attribute_key` e o resultado
    favorável/desfavorável é estatisticamente significativa (qui-quadrado).

    Args:
        records: mesmo formato de `fairness_audit.audit_fairness()`.
        outcome_key: chave do resultado da decisão em cada record.
        protected_attribute_key: chave do atributo protegido (grupo).
        favorable_outcome: valor de `outcome_key` considerado favorável.
        alpha: nível de significância (default 0.05).

    Returns:
        `FairnessSignificanceResult.significant = True` se `p_value < alpha`
        — indício estatístico real de que a disparidade observada não é
        só ruído de amostra pequena.

    Levanta:
        ValueError: se `records` estiver vazio, se houver menos de 2 grupos
            distintos, ou se algum grupo tiver 0 registros de alguma
            categoria de resultado (tabela de contingência degenerada —
            o teste qui-quadrado não é bem definido nesse caso).
    """
    if not records:
        raise ValueError("chi_square_significance requer ao menos um registro em `records`.")

    groups: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        group = str(record.get(protected_attribute_key))
        groups.setdefault(group, []).append(record)

    if len(groups) < 2:
        raise ValueError(
            f"chi_square_significance requer ao menos 2 grupos distintos de '{protected_attribute_key}' "
            f"para comparar (encontrado(s): {len(groups)})."
        )

    # Tabela de contingência: uma linha por grupo, colunas [favorável, desfavorável].
    contingency_table = []
    for group, group_records in sorted(groups.items()):
        favorable = sum(1 for r in group_records if r.get(outcome_key) == favorable_outcome)
        unfavorable = len(group_records) - favorable
        contingency_table.append([favorable, unfavorable])

    try:
        chi2, p_value, dof, _expected = stats.chi2_contingency(contingency_table)
    except ValueError as exc:
        raise ValueError(
            f"Tabela de contingência degenerada para '{protected_attribute_key}' "
            f"(alguma linha ou coluna com soma zero): {exc}"
        ) from exc

    significant = bool(p_value < alpha)

    if significant:
        summary = (
            f"Associação entre '{protected_attribute_key}' e o resultado é ESTATISTICAMENTE "
            f"SIGNIFICATIVA (qui-quadrado={chi2:.4f}, p-valor={p_value:.4g} < alpha={alpha}) — "
            f"a disparidade observada dificilmente é só ruído de amostra."
        )
    else:
        summary = (
            f"Associação entre '{protected_attribute_key}' e o resultado NÃO é estatisticamente "
            f"significativa (qui-quadrado={chi2:.4f}, p-valor={p_value:.4g} >= alpha={alpha}) — "
            f"a disparidade observada pode ser explicada por ruído de amostra pequena."
        )

    return FairnessSignificanceResult(
        protected_attribute=protected_attribute_key,
        chi2_statistic=round(float(chi2), 6),
        p_value=round(float(p_value), 8),
        degrees_of_freedom=int(dof),
        alpha=alpha,
        significant=significant,
        summary=summary,
    )
