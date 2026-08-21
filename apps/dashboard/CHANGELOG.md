# Changelog — Dashboard

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
versionamento [SemVer](https://semver.org/lang/pt-BR/).

## [0.1.0] - 2026-08-19

### Added

- `apps/dashboard/client.py` — `GovernanceCopilotClient`: cliente HTTP fino
  (via `httpx`) para a API do `core/governance_copilot`, com um método por
  endpoint do contrato: `health()`, `detect_pii()`, `scan_prompt_security()`,
  `evaluate_policy()`, `generate_ripd()`, `verify_audit()`,
  `get_audit_events()`. `base_url` configurável por parâmetro ou pela env var
  `THEMIS_API_URL`, com fallback para `http://localhost:8000`.
- Respostas da API são parseadas de volta para os tipos Pydantic de
  `shared/schemas.py` (`PIIDetectionResult`, `PromptSecurityResult`,
  `list[PolicyDecision]`, `RIPDReport`, `list[AuditEvent]`) — nenhum tipo
  redefinido localmente, dando type-safety ao resto do dashboard.
- Hierarquia de exceções própria (`GovernanceCopilotError` →
  `GovernanceCopilotConnectionError` / `GovernanceCopilotHTTPError`) que
  distingue "API fora do ar / timeout" de "API respondeu com erro HTTP" —
  usada pela UI para mostrar uma mensagem clara em vez de quebrar.
- `apps/dashboard/app.py` — app Streamlit com 5 seções via sidebar:
  1. **Visão geral**: lê `status/*.json` da raiz do repo direto do disco
     (sem depender da API) e mostra o progresso agregado do V1 do ROADMAP
     (contagem por status, % concluído, total de testes verdes agregado).
  2. **Gerador de RIPD**: formulário (nome, descrição, categorias de dado,
     base legal) que chama `POST /api/v1/ripd/generate` e mostra o
     `RIPDReport` formatado (trust score, decisões de política, mitigações,
     resumo executivo, JSON completo).
  3. **Scanner de PII**: textarea que chama `POST /api/v1/pii/detect`.
  4. **Scanner de Prompt Security**: textarea que chama
     `POST /api/v1/prompt-security/scan`.
  5. **Auditoria**: mostra `GET /api/v1/audit/verify` e a lista de
     `GET /api/v1/audit/events`.
- Toda chamada à API na UI é envolvida em `try/except` sobre as exceções do
  client, com mensagem amigável via `describe_client_error()` — a API fora
  do ar nunca derruba o app.
- Lógica de negócio extraída em funções puras e testáveis, separadas do
  código que chama `streamlit.*`: `load_status_file`, `load_all_statuses`,
  `compute_v1_progress`, `status_badge`, `build_overview_rows`,
  `pii_findings_to_rows`, `prompt_security_findings_to_rows`,
  `policy_decisions_to_rows`, `audit_events_to_rows`, `ripd_report_summary`,
  `parse_multiline_categories`, `describe_client_error`.
- Suíte de testes pytest (`apps/dashboard/tests/`), 49 testes, 100%
  desacoplada de rede real:
  - `test_client.py`: todas as chamadas de `GovernanceCopilotClient` via
    `httpx.MockTransport` (payload enviado, parsing da resposta), resolução
    de `base_url` (param > env var > default), e tratamento de erro
    (`ConnectError`, `TimeoutException`, erro HTTP genérico do transporte,
    status HTTP 4xx/5xx com e sem corpo JSON).
  - `test_app.py`: todas as funções puras de leitura de `status/*.json` e
    de formatação das respostas da API.

### Notes

- Este módulo **nunca importa `core/governance_copilot` diretamente** — toda
  comunicação é via HTTP, contra o contrato de API documentado. Isso
  permitiu construir e testar o dashboard inteiro em paralelo ao backend,
  que estava sendo implementado por outro agente e ainda não existia no
  disco durante este ciclo.
- Nenhum tipo redefinido localmente — todos os contratos vêm de
  `shared/schemas.py`.
- Ver limitações conhecidas e roadmap V2 em
  `notebooks/dashboard_dev_log.ipynb` (seção Handoff Summary).
