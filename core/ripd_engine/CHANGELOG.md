# Changelog — RIPD Engine

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Este módulo segue SemVer independente (`core/ripd_engine/`).

## [0.1.0] - 2026-08-19

### Added

- `generator.py`: função pública `generate_ripd(project_name, project_description,
  data_categories, legal_basis, context=None) -> RIPDReport`. Primeiro módulo do
  projeto a COMPOR de verdade os 7 módulos da Onda 1 — nenhuma lógica de domínio é
  reimplementada aqui, apenas orquestração real (chamadas diretas, sem mock):
  1. `pii_detection.detect(project_description)` — escaneia a própria descrição do
     projeto em busca de PII vazada.
  2. `policy_engine.evaluate(data_categories, legal_basis, context)` — decisões de
     política LGPD aplicáveis (real, incluindo `DENY`/`REQUIRES_HUMAN_REVIEW`).
  3. `prompt_security.scan(context["sample_prompt"])` — opcional, só roda quando
     `context` traz essa chave.
  4. `regulatory_rag.query(...)` — contexto regulatório recuperado com uma query
     composta (descrição do projeto + categorias de dado + base legal em PT-BR),
     mais discriminativa que a descrição crua isolada.
  5. `trust_score.compute_trust_score` chamado DUAS vezes: a primeira para obter
     `components`, que alimentam `explainability.explain(components,
     subject="ripd_trust_score")`; a segunda já com a `ExplainabilityResult` pronta —
     fecha o ciclo de injeção de dependência documentado pelos módulos da Onda 1.
  6. Agregação (dedup, ordem de primeira ocorrência) de todas as `mitigations` das
     `PolicyDecision` aplicáveis.
  7. `executive_summary`: resumo em português 100% determinístico (template fixo +
     interpolação de dados reais dos passos 1-5) — nunca geração livre/LLM.
  8. Registro de um evento `AuditEventType.RIPD_GENERATED` via
     `audit_logs.default_logger().record_event(...)`, com payload serializável
     resumindo o RIPD gerado.
  9. Montagem do `RIPDReport` (shared/schemas.py) totalmente preenchido.
- `__init__.py`: torna `core/ripd_engine` um pacote Python válido e reexporta
  `generate_ripd`.
- Suíte de testes pytest de integração real (`tests/test_generator.py`, 10 testes,
  nenhum mock de outro módulo), cobrindo:
  - Projeto de baixo risco (dado pessoal comum, base legal e finalidade definidas) →
    `POL-009` `ALLOW`, `RiskLevel.LOW`, sem mitigações, sem PII vazada.
  - Dado de saúde sem consentimento explícito → `POL-001`
    `REQUIRES_HUMAN_REVIEW` vindo do `policy_engine` real (não inventado pelo
    `ripd_engine`), com mitigações reais sobre consentimento e RIPD.
  - Dado biométrico em decisão automatizada sem revisão humana → `POL-002` `DENY`
    real, piso do `trust_score` acionado (`score <= 5.0`, `RiskLevel.CRITICAL`).
  - PII vazada na própria descrição do projeto (e-mail) → detectada e refletida no
    `executive_summary`.
  - `context["sample_prompt"]` com tentativa de prompt injection → `prompt_security`
    populado, `is_safe=False`, penalidade refletida no `trust_score` final.
  - Ausência de `sample_prompt` → `report.prompt_security is None`.
  - Coerência interna do `RIPDReport`: `risk_level` sempre presente (rótulo PT-BR +
    valor cru) no `executive_summary`; `mitigations` == agregação exata e
    deduplicada das `policy_decisions`; `trust_score.components["final_score"] ==
    trust_score.score`; `regulatory_context` com chunks reais (score numérico, texto
    não vazio, fonte `.txt`).
  - Evento de auditoria real gravado (`AuditEventType.RIPD_GENERATED`) e
    `AuditLogger.verify_chain()` permanece `True` após a geração.
  - Fixture de sessão que garante o índice do Regulatory RAG construído e faz um
    "warm-up" isolado do modelo de embeddings antes da suíte rodar.

### Fixed

- Estabilidade em Windows (não é bug de lógica de negócio): o primeiro
  carregamento do modelo `sentence-transformers` via `transformers` produzia uma
  "Windows fatal exception: access violation" intermitente, causada pela
  materialização paralela de pesos do modelo em até 4 threads
  (`transformers.core_model_loading.GLOBAL_WORKERS`) neste ambiente. Mitigado
  nos testes deste módulo (não em `core/regulatory_rag`, fora de escopo) fixando
  `GLOBAL_WORKERS = 1` e `OMP_NUM_THREADS=1` / `MKL_NUM_THREADS=1` /
  `TOKENIZERS_PARALLELISM=false` antes de qualquer import pesado, e isolando o
  primeiro carregamento do modelo num warm-up de sessão dedicado.

### Notes

- Motor 100% determinístico e local — nenhuma chamada a LLM em nenhum ponto do
  pipeline. O `executive_summary` é montado por template + interpolação de dados
  já calculados pelos módulos da Onda 1, nunca por geração livre.
- `generate_ripd` sempre grava no log de auditoria REAL do projeto
  (`core/audit_logs/data/audit_log.jsonl`, via `default_logger()`), não num log
  isolado de teste — é o comportamento de produção pretendido; os testes deste
  módulo verificam que a cadeia de hash permanece íntegra após cada geração, mas
  não isolam o arquivo (ver `core/audit_logs/CHANGELOG.md` para as limitações de
  segurança já documentadas dessa cadeia local).
- `regulatory_context` depende do índice do Regulatory RAG já construído
  (`core/regulatory_rag/data/`, gerado pelo próprio módulo `regulatory_rag`); a
  suíte de testes deste módulo reconstrói o índice automaticamente se ele estiver
  ausente, mas não o modifica nem o versiona.
- TODO (V2): agregação de múltiplas `PolicyDecision` concorrentes usa o
  `trust_score` real (que já resolve o caso `DENY` via piso), mas o
  `executive_summary` só destaca as 3 decisões "mais críticas" (por status) e as 3
  fontes regulatórias mais relevantes — truncamento arbitrário, documentado aqui,
  não configurável nesta versão. Nenhuma persistência do `RIPDReport` gerado é
  feita por este módulo (fica para o `governance_copilot`, que decide onde/como
  armazenar e expor RIPDs gerados).
