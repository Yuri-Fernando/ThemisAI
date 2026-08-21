# Changelog — core/trust_score

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
versionamento [SemVer](https://semver.org/lang/pt-BR/).

## [0.1.0] - 2026-08-19

### Added

- `compute_trust_score()` — agregador puro do AI Trust Score. Recebe por
  injeção de dependência os resultados já computados de PII Detection,
  Policy Engine e (opcionalmente) Prompt Security e Explainability
  (todos tipados via `shared.schemas`), e retorna um `TrustScoreResult`.
- Fórmula de composição aditiva, documentada em detalhe no docstring de
  `core/trust_score/scorer.py`:
  - Score base 100.0.
  - Penalidade por achado de PII sensível (maior peso) e pessoal comum
    (menor peso), cada uma com teto próprio.
  - Política `DENY` aciona um piso (`POLICY_DENY_FLOOR = 5.0`) que veta
    o score independentemente de outros fatores.
  - Política `REQUIRES_HUMAN_REVIEW` penaliza um valor fixo por ocorrência.
  - Política `ALLOW_WITH_MITIGATION` penaliza proporcionalmente ao número
    de mitigações pendentes.
  - `PromptSecurityResult`, quando informado, penaliza de forma contínua
    (proporcional a `1 - score`) mais uma penalidade fixa adicional quando
    `is_safe is False`.
  - Mapeamento score -> `RiskLevel`: `>=80` LOW, `[50, 80)` MEDIUM,
    `[20, 50)` HIGH, `<20` CRITICAL.
- `components: dict[str, float]` expondo a contribuição individual de cada
  fator da fórmula (`base_score`, `pii_penalty`, `policy_human_review_penalty`,
  `policy_mitigation_penalty`, `policy_deny_penalty`, `prompt_security_penalty`,
  `final_score`) — pensado para alimentar `ExplainabilityResult.factors` quando
  o Governance Copilot compuser a explicação completa (Onda 2).
- `explanation: ExplainabilityResult | None` — apenas repassado como recebido;
  este módulo nunca gera sua própria narrativa explicativa.
- Suíte de testes pytest (`core/trust_score/tests/test_scorer.py`) cobrindo:
  caso ótimo, veto por `DENY`, `REQUIRES_HUMAN_REVIEW`, `ALLOW_WITH_MITIGATION`
  proporcional, dado sensível vs. pessoal comum, tetos de penalidade de PII,
  prompt inseguro (contínuo + flag `is_safe`), `explanation` ausente vs.
  repassado, limites do mapeamento de `RiskLevel`, contrato de `components` e
  não-negatividade do score em cenários extremos.

### Notes

- Este módulo **não importa** `core.pii_detection`, `core.policy_engine`,
  `core.prompt_security` nem `core.explainability` — arquitetura de injeção
  de dependência para evitar acoplamento entre módulos construídos em
  paralelo. A integração real (chamar cada módulo e alimentar
  `compute_trust_score()` com os resultados) é responsabilidade do
  Governance Copilot, na Onda 2.
