# Changelog — Governance Copilot

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Este módulo segue SemVer independente (`core/governance_copilot/`).

## [0.2.0] - 2026-08-21 — Deploy-ready: fecha os itens de Alta/Média prioridade do V5

Fecha 6 dos 15 itens de `docs/architecture/future-improvements.md` (3, 4, 6,
7, 8, 14) + versão honesta do item 5 — as limitações que bloqueavam qualquer
deploy real além da máquina de desenvolvimento.

### Added
- `auth.py`: `require_api_key` — autenticação por `X-API-Key`, **desabilitada
  por padrão** (retrocompatível: `THEMIS_API_KEY` indefinida = sem auth,
  igual ao V1/V2), ativa quando o operador define a env var. (Item 3.)
- CORS via `CORSMiddleware`, origens configuráveis por `THEMIS_CORS_ORIGINS`
  (CSV), `*` por padrão. (Item 3.)
- `ripd_store.py`: `RIPDStore` — persiste todo RIPD gerado (JSON, mesmo
  padrão de `human_oversight`). Novos endpoints `GET /api/v1/ripd` (lista
  resumida) e `GET /api/v1/ripd/{ripd_id}` (relatório completo). Toda
  resposta de `POST /api/v1/ripd/generate` ganha o header `X-RIPD-Id`.
  (Item 14.)
- `POST /api/v1/ripd/generate` agora enfileira automaticamente em
  `human_oversight` toda `PolicyDecision` com `REQUIRES_HUMAN_REVIEW` —
  header `X-Human-Review-Item-Ids` lista os itens criados. (Item 4.)
- `pii/detect`, `prompt-security/scan` e `policy/evaluate` — que antes NÃO
  geravam nenhum evento de auditoria — agora registram um evento real por
  chamada, com um `trace_id` novo no payload. Novo endpoint
  `GET /api/v1/audit/trace/{trace_id}` (usa `traceability.trace_by_correlation_key`
  por baixo, via `trace_events`) correlaciona os eventos de um mesmo
  `trace_id`. (Item 6.)
- Todo endpoint decorado com `@enforce(agent_id, action)`
  (`runtime_policy_enforcement`, V3) — a autorização declarada em
  `multi_agent_governance/agents.yaml` deixa de ser só consultiva: a chamada
  real é estruturalmente bloqueada se o agente não estiver autorizado.
  `agents.yaml` ganhou as ações `ripd_engine.generate_ripd` e
  `governance_copilot.ripd_store` (`ripd_generator`) e
  `ai_observability.export`/`self_healing_governance.check_and_heal`
  (`auditor`). (Item 7.)
- `GET /metrics`: `ai_observability.export_prometheus_text()` real sobre um
  `ObservabilityRecorder` de processo — `pii/detect`, `prompt-security/scan`,
  `policy/evaluate` e `ripd/generate` são envolvidos em `traced(...)`.
  (Item 8.)
- `POST /api/v1/health-check/run`: roda `self_healing_governance.check_and_heal()`
  sobre os checks informados pelo chamador. **Não há scheduler/cron
  embutido** — versão honesta do item 5: um disparador externo periódico
  (cron, GitHub Actions agendado) precisa chamar este endpoint para virar
  automação de verdade.
- 17 testes novos (`tests/test_api_v5.py`): auth desabilitada por padrão /
  exigida quando configurada / chave errada rejeitada / `/health` sempre
  livre; CORS; todos os endpoints continuam autorizados pelos agentes
  default (prova de que o enforcement não quebrou nada existente);
  `/metrics` reflete chamada real; `pii/detect`/`prompt-security/scan`/
  `policy/evaluate` geram evento real rastreável por `trace_id`; `trace_id`
  desconhecido retorna 404; RIPD de alto risco enfileira revisão humana
  automaticamente (baixo risco não); RIPD persistido e recuperável por id
  e por lista; id desconhecido retorna 404; health-check real.

### Fixed
- **Poluição de dados de produção pelos próprios testes**: `_ripd_store` e a
  fila de revisão humana usada por `_auto_enqueue_human_review` apontavam
  para os caminhos padrão de produção mesmo quando chamados via
  `TestClient` nos testes — cada rodada de `pytest` gravava RIPDs/itens de
  revisão de teste em `core/governance_copilot/data/` e
  `core/human_oversight/data/` reais. Corrigido: os dois viraram
  instâncias de módulo (`api._ripd_store`, `api._oversight_queue`)
  monkeypatchable, e `tests/conftest.py` (novo) as substitui por instâncias
  em `tmp_path` automaticamente (`autouse=True`) para toda a suíte deste
  módulo. Os arquivos já poluídos por sessões anteriores foram apagados.

### Notes
- Todos os 13 testes da v0.1.0 (`tests/test_api.py`) continuam passando sem
  alteração — a suíte anterior nunca precisou saber de auth/enforcement/
  observabilidade para continuar válida, prova de retrocompatibilidade real.
- `@enforce` funciona de forma transparente com a introspecção de assinatura
  do FastAPI (via `functools.wraps`, que preserva `__wrapped__` e é seguido
  por `inspect.signature`) — confirmado empiricamente, sem workaround
  necessário.
- Itens 9 (ancoragem externa do Merkle) e 10 (OCR) do plano de melhorias
  continuam fora de escopo — infraestrutura externa real que este ciclo não
  cobriu. Itens 13 e 15 permanecem deliberadamente não implementados (ver
  justificativa em `docs/architecture/future-improvements.md`).

## [0.1.0] - 2026-08-20

### Added

- `api.py`: aplicação FastAPI que expõe os módulos da Onda 1 como serviço
  HTTP — casca fina de validação/tradução de exceções, nenhuma lógica de
  domínio reimplementada. 7 endpoints:
  - `GET /health` — healthcheck.
  - `POST /api/v1/pii/detect` → `pii_detection.detect`.
  - `POST /api/v1/prompt-security/scan` → `prompt_security.scan`.
  - `POST /api/v1/policy/evaluate` → `policy_engine.evaluate`.
  - `POST /api/v1/ripd/generate` → `ripd_engine.generate_ripd` (o endpoint
    que de fato compõe os 7 módulos da Onda 1 ponta a ponta).
  - `GET /api/v1/audit/verify` → `audit_logs.default_logger().verify_chain()`.
  - `GET /api/v1/audit/events?limit=N` → `audit_logs.default_logger().read_events()`,
    truncado aos `N` mais recentes.
- Modelos de request Pydantic locais (`PIIDetectRequest`,
  `PromptSecurityScanRequest`, `PolicyEvaluateRequest`, `RIPDGenerateRequest`)
  — os únicos tipos definidos neste módulo; toda resposta usa diretamente os
  tipos de `shared/schemas.py` (`response_model=...`), sem redefinição.
- `__init__.py`: reexporta `app` para `uvicorn core.governance_copilot:app`.
- Suíte de testes de integração real (`tests/test_api.py`, 13 testes) via
  `fastapi.testclient.TestClient` — chama a aplicação ASGI real em processo,
  sem mockar nenhuma rota nem nenhum módulo por trás delas (inclusive
  `ripd_engine`, que por sua vez chama de verdade os 7 módulos da Onda 1).
  Cobertura:
  - Healthcheck.
  - PII: CPF válido detectado; texto vazio não gera achados.
  - Prompt Security: prompt de injeção sinalizado; prompt neutro seguro.
  - Policy: dado sensível de saúde retorna decisões; sem `context` não
    quebra; enum inválido retorna `422` (validação Pydantic da API, não do
    `policy_engine`).
  - RIPD: projeto de baixo risco gera relatório coerente; projeto de alto
    risco (biometria + decisão automatizada sem revisão humana) resulta em
    `risk_level == "critical"` e ao menos uma `PolicyDecision` `deny` — real,
    vindo do `policy_engine`/`trust_score`, não hardcoded no teste; geração de
    RIPD grava evento de auditoria real e a cadeia de hash permanece válida.
  - Auditoria: `/audit/verify` retorna `valid: true` numa cadeia íntegra;
    `/audit/events?limit=N` respeita o truncamento.

### Notes

- Este é o módulo que fecha a Onda 2 do V1: com ele, `apps/dashboard` (que já
  falava exclusivamente com este contrato de API via
  `GovernanceCopilotClient`, desenvolvido em paralelo contra um backend que
  ainda não existia) passa a ter um backend real por trás.
- `/api/v1/ripd/generate` depende do índice do Regulatory RAG já construído
  (`core/regulatory_rag/data/`). Em produção local isso já existe (gerado
  pelo próprio módulo `regulatory_rag`); os testes deste módulo reconstroem o
  índice automaticamente se ausente (mesmo padrão do `ripd_engine`).
- CORS não é configurado nesta versão (V1 assume dashboard e API rodando na
  mesma máquina, uso local) — se o dashboard precisar rodar num host
  diferente da API, isso é um TODO de V2, junto com autenticação (nenhum
  endpoint desta versão exige credenciais — uso interno/local apenas).
- Nenhuma paginação real em `/api/v1/audit/events` além do `limit` simples
  (trunca os N mais recentes lendo o arquivo inteiro em memória) — aceitável
  para o volume de eventos de uma cadeia local de demonstração; não escala
  para produção com milhões de eventos (V2/V3: persistência indexada).
