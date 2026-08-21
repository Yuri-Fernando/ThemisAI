# Changelog — Behavioral Monitoring

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Este módulo segue SemVer independente (`core/behavioral_monitoring/`).

## [0.1.0] - 2026-08-21

### Added

- Extração real do item "Behavioral Monitoring" do V3.
- `drift.py`: `detect_drift(baseline, current, metric_name="metric",
  alpha=0.05) -> DriftReport` — teste de Kolmogorov-Smirnov de duas amostras
  real (`scipy.stats.ks_2samp`), não simulado.
- Nova dependência: `scipy` (`requirements-core.txt`).
- Contrato novo em `shared/schemas.py` (`DriftReport`).
- Suíte de testes pytest (`tests/test_drift.py`, 6 testes): distribuições
  idênticas não geram drift; distribuições claramente diferentes geram
  drift; tamanhos de amostra registrados; `alpha` customizável; validação de
  amostras pequenas demais; **drift medido sobre `trust_score.score` real**
  (via `policy_engine` + `trust_score` reais) comparando decisões de baixo
  vs. alto risco.

### Notes

- Compatível com qualquer série numérica de qualquer módulo V1/V2 (não
  amarrado a `ai_observability` especificamente) — o chamador extrai os
  valores de onde fizer sentido.
