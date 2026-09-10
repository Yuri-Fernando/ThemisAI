# Changelog — Adversarial ML / AI Security

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Este módulo segue SemVer independente (`core/adversarial_ml/`).

## [0.1.0] - 2026-09-10

### Added

- `models.py`: `LogisticRegressionModel` (numpy puro, gradiente analítico em
  relação à entrada — FGSM/PGD sobre ele são exatos) e `BlackBoxModel`
  (gradiente por diferenças finitas centrais sobre qualquer `predict_proba`,
  ex.: modelo scikit-learn ou endpoint remoto).
- `attacks/`:
  - `fgsm.py` — Fast Gradient Sign Method (Goodfellow et al., 2015).
  - `pgd.py` — Projected Gradient Descent (Madry et al., 2018), com random
    start e projeção L-infinito.
  - `extraction.py` — model extraction por consulta (treina surrogate nos
    rótulos do alvo, mede `fidelity`).
  - `poisoning.py` — data poisoning por label flipping, mede degradação de
    acurácia limpa por ponto de contaminação.
- `defenses/`:
  - `adversarial_training.py` — min-max de Madry, `max` interno aproximado
    por PGD contra o próprio modelo em treino.
  - `preprocessing.py` — feature squeezing (Xu et al., 2018) + clipping de
    faixa, como wrapper que mantém a interface `TargetModel`.
  - `detection.py` — detector estatístico de entrada adversarial (limiares
    de entropia/margem calibrados em dados limpos).
- `robustness/`:
  - `metrics.py` — `robustness_curve`, `min_perturbation_budget`,
    `classify_risk` (traduz queda de acurácia em `RiskLevel` de negócio).
  - `evaluator.py` — `evaluate_robustness` roda FGSM+PGD+curva.
  - `report.py` — renderiza o **MODEL SECURITY REPORT** textual.
- `llm_security/assessor.py` — fachada que compõe `core/prompt_security` e
  `core/red_team_lab` (motor real, sem reimplementar detecção) numa seção do
  relatório, por categoria de ataque + gaps de cobertura.
- `assessment.py` — `run_security_assessment(model, X_test, y_test,
  n_classes, X_train=, y_train=, include_llm_security=, include_defense=)`,
  ponto de entrada único, devolve `ModelSecurityReport` já renderizado.
- Contratos novos em `shared/schemas.py` (`AdversarialAttackResult`,
  `RobustnessMetrics`, `DefenseEvaluation`, `ModelSecurityReport`),
  `SCHEMA_VERSION` 0.3.0 → 0.4.0 (aditivo, não-breaking).
- Suíte de testes pytest (`tests/`, 15 testes): FGSM/PGD realmente derrubam
  acurácia de modelo não defendido; PGD ≥ FGSM em força; perturbação
  respeita o orçamento L-infinito; ataque black-box (diferenças finitas)
  também funciona; extração recupera comportamento (fidelity > 0.8);
  poisoning degrada acurácia limpa; adversarial training não piora a
  robustez; detector sinaliza mais adversarial que limpo; relatório completo
  é renderizado com todos os ataques.
- `notebooks/adversarial_ml_dev_log.ipynb` — dev-log com dataset "difícil"
  (não linearmente separável) mostrando risco HIGH e o efeito real do
  adversarial training.

### Notes — origem do escopo

Este módulo vem de um brainstorm de consolidação de portfólio (`up.txt`,
2026-09) que estende deliberadamente o "teto de escopo" registrado no
`ROADMAP.md`. É implementação real (código + testes + notebook), no mesmo
rigor do resto do projeto — não stub. O Themis passa a ser a plataforma
central de **AI Governance + AI Security + Adversarial ML**, e os demais
projetos do portfólio (VisionGuard, Credit Score, RL-PID-AGV, Churn) são os
casos de uso que consomem este motor.
