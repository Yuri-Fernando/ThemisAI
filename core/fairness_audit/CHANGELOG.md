# Changelog — Fairness Audit

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Este módulo segue SemVer independente (`core/fairness_audit/`).

## [0.2.0] - 2026-08-21 — Teste de significância estatística real (V5, item 12)

### Added
- `significance.py`: `chi_square_significance(records, outcome_key,
  protected_attribute_key, favorable_outcome=True, alpha=0.05) ->
  FairnessSignificanceResult` — teste qui-quadrado de independência
  (`scipy.stats.chi2_contingency`) sobre a tabela de contingência real
  grupo x resultado. Fecha a limitação documentada na v0.1.0 ("não avalia
  significância estatística").
- Contrato novo em `shared/schemas.py` (`FairnessSignificanceResult`).
- 8 testes novos (`tests/test_significance.py`): disparidade grande em
  amostra grande é significativa; mesma taxa em amostra pequena não é;
  **demonstração real da lacuna que motivou o item** — uma disparidade que
  reprova a regra dos 80% (`audit_fairness`) com só 5 registros por grupo
  não sustenta significância estatística forte (`p_value > 0.01`); alpha
  customizável; validação de entrada (vazio, grupo único); 3+ grupos;
  resumo.

### Notes
- Função independente de `audit_fairness()` (mesmo formato de `records`,
  reusável junto ou sozinha) — não altera o contrato/comportamento de
  `audit_fairness()` existente.
- Reusável por `core/causal_fairness` (V3, extração real) para testar
  significância dentro de cada estrato, se necessário numa onda futura —
  não integrado automaticamente nesta versão.

## [0.1.0] - 2026-08-20

### Added

- `engine.py`: `audit_fairness(records, outcome_key, protected_attribute_key,
  favorable_outcome=True, threshold=0.8) -> FairnessAuditResult`. Motor 100%
  estatístico e determinístico (sem ML/treinamento) que calcula duas métricas
  de equidade padrão da literatura:
  - **Disparate impact ratio** (regra dos 80%, convenção EEOC): taxa de
    seleção do grupo / taxa de seleção do grupo de referência (o de maior
    taxa). `passed = ratio >= threshold`.
  - **Demographic parity difference**: diferença absoluta entre a taxa de
    seleção do grupo de referência e a do grupo comparado.
  - Grupo de referência escolhido automaticamente como o de maior taxa de
    seleção (convenção padrão da regra dos 80%); todos os demais grupos são
    comparados contra ele.
  - `summary` determinístico em português com o veredito e as taxas de
    seleção por grupo.
- Contratos novos em `shared/schemas.py` (`FairnessMetric`,
  `FairnessAuditResult`) — `SCHEMA_VERSION` bump para `0.2.0` (seção "Shared
  Contracts").
- Suíte de testes pytest (`tests/test_engine.py`, 10 testes): taxas iguais
  são justas; disparidade abaixo do limiar é sinalizada; grupo de referência
  correto; 3+ grupos comparados corretamente contra a referência; grupo único
  é "justo por vacuidade" (documentado, não é uma auditoria completa);
  `favorable_outcome`/`threshold` customizáveis; validação de entrada
  (`records` vazio, chave de atributo protegido ausente); proteção contra
  divisão por zero quando a taxa do grupo de referência é 0.

### Notes

- Motor standalone (dependency injection), no mesmo espírito de
  `explainability`/`trust_score` no V1: não importa `policy_engine` nem
  nenhum outro módulo — recebe `records` já produzidos por qualquer sistema
  de decisão (interno ou externo).
- Limitação documentada: com apenas 2 grupos, a métrica é simples e direta;
  com 3+ grupos, a comparação é sempre grupo-a-grupo contra a referência
  (não par-a-par entre todos os grupos) — suficiente para a regra dos 80%,
  mas não substitui uma análise estatística multivariada completa (ex.
  controle por variáveis confundidoras) — isso é um TODO explícito de onda
  futura, não fingido aqui.
- Não avalia significância estatística (intervalo de confiança/p-valor) das
  diferenças encontradas — amostras pequenas podem gerar `disparate_impact`
  ruidoso; documentado como limitação conhecida.
