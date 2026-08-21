# Changelog — Constitutional AI

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Este módulo segue SemVer independente (`core/constitutional_ai/`).

## [0.1.0] - 2026-08-20

### Added

- `constitution.yaml`: 6 princípios declarativos ("linhas vermelhas") reais,
  ancorados em artigos da LGPD: Transparência (Art. 20/9º), Não-discriminação
  (integra com `fairness_audit`), Supervisão humana (Art. 20 §1º),
  Minimização de dados (Art. 6º, III), Prestação de contas (Art. 6º, X,
  integra com `audit_logs`), Segurança (Art. 46, integra com
  `prompt_security`).
- `engine.py`: `check_constitution(context, constitution_path=None) ->
  ConstitutionalCheckResult`. Formato deliberadamente mais simples que
  `policy_engine/policies.yaml` (sem branching de múltiplos outcomes) — cada
  artigo é uma condição `forbidden_when.context` (match por igualdade, AND
  entre chaves); casar = violação. Versão "simples" citada no ROADMAP
  original ("regras declarativas → políticas executáveis, versão simples").
- Contratos novos em `shared/schemas.py` (`ConstitutionalViolation`,
  `ConstitutionalCheckResult`).
- Suíte de testes pytest (`tests/test_engine.py`, 10 testes): contexto
  conforme sem violações; cada um dos 6 princípios violado individualmente;
  múltiplas violações simultâneas; contexto vazio; constituição customizada
  via `constitution_path` (prova que o motor é genérico, não hardcoded para
  os 6 artigos padrão).

### Notes

- Complementar ao `policy_engine` (V1), não um substituto: `policy_engine`
  decide o que é **permitido com que condições** (branching de outcomes);
  `constitutional_ai` define o que **nunca pode acontecer**, independente de
  qual política se aplique — dois níveis de governança diferentes.
  `governance_copilot` é quem decide, numa onda futura, como compor os dois
  (TODO).
- Match de condição é só por igualdade simples (`context[chave] == valor`)
  — sem os operadores `_any`/`_all`/`_not_in` que `policy_engine` tem. Se
  isso se mostrar insuficiente para princípios futuros, é um TODO de
  extensão, não uma limitação escondida.
