# Changelog — Red Team Lab

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Este módulo segue SemVer independente (`core/red_team_lab/`).

## [0.1.0] - 2026-08-20

### Added

- `payloads.py`: 12 payloads de ataque reais contra `prompt_security`
  (injeção direta PT/EN, jailbreak clássico DAN/developer mode, exfiltração
  de dados sensíveis, ofuscação base64, evasão dedicada — paráfrase,
  homoglifos fullwidth, ofuscação em camadas — e 2 controles benignos).
- `harness.py`: `run_red_team_suite(scan_fn=None, payloads=None) ->
  RedTeamReport`. Roda cada payload de verdade contra `prompt_security.scan`
  real (`scan_fn` parametrizável, usado nos testes estruturais). Nenhum
  resultado é hardcoded — `detected` vem sempre da resposta real do motor.
- Contratos novos em `shared/schemas.py` (`AttackResult`, `RedTeamReport`).
- Suíte de testes pytest (`tests/test_harness.py`, 10 testes): execução real
  contra o motor de produção; controles benignos não geram falso positivo;
  jailbreaks clássicos são detectados; testes estruturais com `scan_fn`
  injetado (sempre seguro / sempre inseguro) validam a matemática do
  relatório independente do comportamento real do `prompt_security`.

### Notes — achado real de red-teaming (não escondido)

Ao rodar `run_red_team_suite()` contra o `prompt_security` real nesta
versão (0.1.0), **4 de 12 payloads divergiram do esperado** (taxa de
detecção medida: 50%): `RT-01` (injeção direta em PT) e `RT-06`
(exfiltração em PT) não eram detectados, e `RT-08`/`RT-09` (evasão por
paráfrase/homoglifos) também não. Isto era o **propósito do módulo**, não
um bug dele: expor gaps reais de cobertura do `prompt_security` para
priorização.

## [0.1.1] - 2026-08-21 — RT-01/RT-06 corrigidos (V5, item 1 do plano de melhorias)

### Fixed
- `core/prompt_security/scanner.py`: os padrões `ignore_previous_instructions`
  e `other_users_data` não previam palavras extras entre o gatilho e o alvo
  em português (`"ignore TODAS AS instruções"`, `"dados PESSOAIS de outros
  usuários"`) — bug de regex real, não limitação fundamental de detecção em
  PT como se suspeitava inicialmente. Corrigido; ver
  `core/prompt_security/CHANGELOG.md` para o detalhe do fix.

### Notes
- Taxa de detecção real, revalidada nesta versão: **10/12 (67%)**, subindo
  de 50%. `RT-08`/`RT-09` (evasão por paráfrase/homoglifos) continuam
  gaps reais e conhecidos — consistentes com a limitação documentada em
  `core/prompt_security/CHANGELOG.md` ("honestamente frágil contra evasão
  dedicada"), não corrigidos nesta rodada (exigiriam heurística mais
  sofisticada ou, para o caso geral, um classificador — decisão consciente
  de manter o motor 100% determinístico).
