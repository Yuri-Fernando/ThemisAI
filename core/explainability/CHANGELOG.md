# Changelog — core/explainability

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
versionamento [SemVer](https://semver.org/lang/pt-BR/).

## [0.1.0] - 2026-08-19

### Added

- `explain(factors, subject, narrative_template=None) -> ExplainabilityResult`:
  motor de explicabilidade genérico e determinístico (não é machine learning).
  Ordena fatores numéricos por magnitude de contribuição (`abs(valor)`,
  decrescente) e gera narrativa em português natural explicando a decisão em
  ordem de importância.
- Tratamento correto de fatores positivos, negativos, mistos, dicionário
  vazio, fator único e valor neutro (`0.0`).
- Suporte a `narrative_template` customizado, em dois modos:
  - **molde** — se o template contém `{subject}` e/ou `{body}`, eles são
    substituídos;
  - **prefixo** — caso contrário, o template é usado como frase de abertura e
    a explicação padrão dos fatores é anexada.
- Módulo standalone: importa apenas `shared.schemas.ExplainabilityResult`.
  Não conhece nem importa nenhum outro módulo do projeto — é injetado por
  quem o consome (`trust_score`, `policy_engine`, `ripd_engine`, ...).
- Suíte de testes pytest (`core/explainability/tests/test_engine.py`)
  cobrindo: só positivos, só negativos, mistos, dict vazio, fator único,
  muitos fatores (ordenação), template customizado (molde e prefixo),
  valor de contribuição zero e preservação do `subject` livre.
- `notebooks/explainability_dev_log.ipynb` com exemplos ilustrativos de uso
  simulando `trust_score`, `policy_decision` e `pii_detection`, execução da
  suíte de testes e resumo de handoff para integração por outros módulos.
