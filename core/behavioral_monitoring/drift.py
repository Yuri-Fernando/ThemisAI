"""Behavioral Monitoring — extração REAL do item "Behavioral Monitoring" do
V3: detecção de mudança de comportamento (model/data drift) comparando duas
amostras de uma métrica numérica ao longo do tempo (ex. `trust_score.score`
de um período "baseline" contra um período "atual"), usando o **teste de
Kolmogorov-Smirnov de duas amostras** (`scipy.stats.ks_2samp`) — um teste
estatístico real e padrão da literatura para comparar se duas amostras vêm
da mesma distribuição.

Não reimplementa nada de `ai_observability`/`trust_score` — recebe duas
listas de valores numéricos já extraídas de onde o chamador quiser (ex. um
`ObservabilitySnapshot.metrics[i].duration_ms` de dois períodos, ou uma
lista de `TrustScoreResult.score`).
"""
from __future__ import annotations

from scipy import stats

from shared.schemas import DriftReport

DEFAULT_ALPHA = 0.05


def detect_drift(
    baseline: list[float],
    current: list[float],
    metric_name: str = "metric",
    alpha: float = DEFAULT_ALPHA,
) -> DriftReport:
    """Compara `baseline` contra `current` com o teste KS de duas amostras.

    Args:
        baseline: amostra de referência (ex. métricas do período "normal").
        current: amostra atual a comparar contra o baseline.
        metric_name: nome legível da métrica sendo monitorada.
        alpha: nível de significância (default 0.05 — convenção padrão).

    Returns:
        `DriftReport.drift_detected = True` se `p_value < alpha` (rejeita a
        hipótese nula de que as duas amostras vêm da mesma distribuição —
        indício estatístico real de mudança de comportamento).

    Levanta:
        ValueError: se `baseline` ou `current` tiver menos de 2 valores (o
            teste KS não é significativo com amostras degeneradas).
    """
    if len(baseline) < 2 or len(current) < 2:
        raise ValueError("detect_drift requer ao menos 2 valores em cada amostra (baseline e current).")

    result = stats.ks_2samp(baseline, current)
    drift_detected = bool(result.pvalue < alpha)

    if drift_detected:
        summary = (
            f"Drift DETECTADO em '{metric_name}': estatística KS={result.statistic:.4f}, "
            f"p-valor={result.pvalue:.4g} < alpha={alpha} — as distribuições baseline/atual "
            f"são estatisticamente diferentes."
        )
    else:
        summary = (
            f"Nenhum drift detectado em '{metric_name}': estatística KS={result.statistic:.4f}, "
            f"p-valor={result.pvalue:.4g} >= alpha={alpha} — sem evidência estatística de mudança "
            f"de distribuição entre baseline e atual."
        )

    return DriftReport(
        metric_name=metric_name,
        baseline_size=len(baseline),
        current_size=len(current),
        ks_statistic=float(result.statistic),
        p_value=float(result.pvalue),
        alpha=alpha,
        drift_detected=drift_detected,
        summary=summary,
    )
