# CHANGELOG

Este é o **documento mestre de histórico** do Themis AI. Segue o formato
[Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/) e [SemVer](https://semver.org/lang/pt-BR/).

Cada módulo também mantém seu próprio `core/<modulo>/CHANGELOG.md` local (para os
agentes registrarem trabalho em paralelo sem conflito de merge); este arquivo raiz
é a consolidação oficial, atualizada pelo orquestrador após cada onda de trabalho.

Ver também: [ROADMAP.md](ROADMAP.md) (escopo/fases) e `docs/decisions/` (ADRs).

## [Unreleased]

### Pendente (reservado para o usuário — Fase 2, ver PARA_VOCE_FAZER.md e ROADMAP.md)
- Demo pública (Dockerfile/docker-compose já prontos, build não validado
  nesta sessão — Docker Desktop indisponível no ambiente).
- Tag git `v1.0.0`/`v2.0.0`/`v3.0.0`/`v6.0.0` e push.
- Decisão de publicação do repositório (visibilidade/licença).
- Revisão jurídica humana do corpus do `regulatory_rag` antes de uso além de
  portfólio/demonstração.
- Configurar um disparador externo (cron/GitHub Actions agendado) para
  `POST /api/v1/health-check/run` se quiser automação periódica de verdade
  (ver `docs/architecture/future-improvements.md`, item 5).
- 5 itens de débito técnico ainda em aberto (9, 10, 13, 15 deliberado — ver
  [docs/architecture/future-improvements.md](docs/architecture/future-improvements.md)).

## [0.6.0] - 2026-08-21 — V5: fecha 10 dos 15 itens de débito técnico, projeto deploy-ready

**10 dos 15 itens do plano de melhorias resolvidos** — código real + testes,
mesmo rigor do resto do projeto. **32 testes novos** (`pytest core/ apps/`
cobre agora **477 no total**). Ver `docs/architecture/future-improvements.md`
para o mapeamento completo item→fix.

### Fixed
- **`prompt_security`** (item 1): dois bugs de regex reais corrigidos
  (`ignore_previous_instructions` não previa `"todas as"`;
  `other_users_data` não previa palavra extra entre "dados" e "de outros
  usuários"). Taxa de detecção real medida por `red_team_lab` subiu de 50%
  para 67% (10/12).
- **`constitution_compiler`** (item 2): distingue overlap real (chaves em
  comum, bloqueante) de overlap por vacuidade (sem chaves em comum,
  informativo). Na constituição de produção: 11 falsos-positivos → 2
  conflitos reais + 9 informativos.

### Added
- **`governance_copilot`** (itens 3, 4, 6, 7, 8, 14 + versão honesta do 5):
  autenticação opcional (`X-API-Key`/`THEMIS_API_KEY`), CORS configurável,
  fila de revisão humana alimentada automaticamente, trilha de auditoria
  por `trace_id` para endpoints que antes não geravam nenhum evento,
  autorização real via `@enforce` em todo endpoint, `GET /metrics` real,
  RIPDs persistidos e consultáveis (`GET /api/v1/ripd`,
  `GET /api/v1/ripd/{id}`), `POST /api/v1/health-check/run` sob demanda.
  Ver `core/governance_copilot/CHANGELOG.md` `[0.2.0]` para o detalhe
  completo — 17 endpoints novos de teste, 13 testes da v0.1.0 inalterados.
- **`differential_privacy`** (item 11): `advanced_composition_epsilon()` —
  teorema de composição avançada real (Dwork, Rothblum, Vadhan 2010),
  cresce `O(sqrt(k))` contra `O(k)` da composição sequencial simples.
- **`fairness_audit`** (item 12): `chi_square_significance()` — teste
  qui-quadrado real (`scipy.stats.chi2_contingency`), fecha a lacuna de
  significância estatística documentada desde a v0.1.0.

### Notes
- `multi_agent_governance/agents.yaml` ganhou as ações necessárias para o
  `governance_copilot` decorar todos os seus endpoints com `@enforce` sem
  quebrar nenhum fluxo — ver `core/multi_agent_governance/CHANGELOG.md`
  `[0.1.1]`.
- Itens 9 (ancoragem externa do Merkle) e 10 (OCR) permanecem fora de
  escopo — infraestrutura externa real. Itens 13 e 15 permanecem
  deliberadamente não implementados (decisão de risco/escopo, não
  esquecimento) — justificativa completa em
  `docs/architecture/future-improvements.md`.

## [0.5.0] - 2026-08-21 — Polimento de portfólio + registro de naming

### Added
- `NAMING.md` (raiz): registro completo da discussão de rename para Themis
  AI (opções consideradas, critérios, execução).
- `notebooks/99_capstone_full_pipeline.ipynb`: os 36 módulos de `core/`
  encadeados num único cenário fictício (`TrustLend AI`, score de crédito
  automatizado), execução real de ponta a ponta — reproduz ao vivo os
  achados reais já conhecidos (gap do `prompt_security` em PT; comportamento
  correto do `regulatory_sandbox` quando o cenário já parte com revisão
  humana).
- `.github/workflows/tests.yml`: CI real rodando `pytest core/ apps/` a
  cada push/PR (sem segredos — motor 100% local).
- `Dockerfile` + `docker-compose.yml` + `.dockerignore`: API +
  Dashboard sobem com `docker compose up --build`. **Build não validado
  nesta sessão** (Docker Desktop indisponível no ambiente) — ver
  `PARA_VOCE_FAZER.md`.
- `CASE_STUDY.md`: decisões de engenharia reais, os 3 achados que
  aconteceram no meio do caminho (gap do `prompt_security`, Paradoxo de
  Simpson no `causal_fairness`, 11 conflitos no `constitution_compiler`),
  números que sustentam o rigor do projeto.
- `PARA_VOCE_FAZER.md` (raiz): fonte única de verdade do que fica
  exclusivamente com o usuário (demo pública, tags, licença, revisão
  jurídica, priorização do V5) — separado do débito técnico de engenharia.

### Changed
- Rename residual corrigido: env var `ATHENAGOV_API_URL` → `THEMIS_API_URL`
  (`apps/dashboard/client.py`) e prefixo de métrica Prometheus `athenagov_`
  → `themis_` (`core/ai_observability/observability.py`) — não pegos pelo
  find-replace original por diferença de maiúsculas/minúsculas. Testes
  atualizados e revalidados.

### Notes
- Confirmado nesta sessão (registro para não reabrir a pergunta): **não há
  V6/V7 planejado**. O teto do projeto é V1+V2+V3/V4(extração
  real)+V5(débito técnico já mapeado) — 41 capacidades rastreadas cobrem
  100% do brainstorm original (`docs/origin/rascunho.md`).

## [0.4.0] - 2026-08-21 — Rebrand para Themis AI + extração real de V3/V4 (Onda 5)

### Changed
- **Projeto renomeado de "AthenaGov AI" para "Themis AI"** — Têmis, deusa
  grega da lei/ordem/justiça, mantém a linha mitológica de "Athena" mas
  migra o significado para governança, refletindo o escopo real do projeto
  hoje (V1 compliance LGPD + 19 capacidades de AI Governance V2 + extração
  real de V3/V4). Aplicado em README/CHANGELOG/ROADMAP/WORKLOG/docstrings de
  todo o código (28 arquivos) — `docs/origin/rascunho.md` e `rascunho.md`
  preservados verbatim como registro histórico do nome original.

### Added — Onda 5: extração real do núcleo codificável de V3/V4
**8 módulos novos, 57 testes** (`pytest core/` cobre agora **445 no total**
do projeto). Decisão de escopo (com o usuário): em vez de fingir
implementação completa de capacidades como "AGI Risk Governance" ou "Formal
Verification Layer" (que exigiriam pesquisa/infraestrutura fora do alcance
responsável do projeto), extraído e implementado — com o mesmo rigor de
código+testes+notebook — só o núcleo genuinamente codificável de 8 dos 12
itens de V3/V4, honestamente reescopado em cada um.

- **Formal Verification** (`core/formal_verification`, 6 testes) — model
  checking por enumeração exaustiva (não prova simbólica TLA+/Alloy/Coq).
  Verifica exaustivamente (4.368 combinações) que `agent_tribunal.adjudicate()`
  sempre escolhe `DENY` quando presente na entrada.
- **AI Constitution Compiler** (`core/constitution_compiler`, 10 testes) —
  detecção estática de conflitos entre artigos de `constitution.yaml`.
  **Achado real**: 11 conflitos de severidade sobreposta na constituição de
  produção (mais do que esperado — expôs limitação real do modelo de
  compatibilidade, documentada e não mascarada).
- **Causal Fairness** (`core/causal_fairness`, 6 testes) — disparate impact
  estratificado por variável confundidora, detecção de Paradoxo de Simpson
  (validado contra o exemplo clássico estilo Berkeley).
- **Behavioral Monitoring** (`core/behavioral_monitoring`, 6 testes) —
  detecção de drift real via teste de Kolmogorov-Smirnov (`scipy`).
- **Cognitive Attack Detection** (`core/cognitive_attack_detection`, 7
  testes) — scan multi-turno de conversas com reassemblagem de payloads
  fragmentados. Achado empírico real usado nos testes (fragmentos safe
  individualmente, payload real quando concatenados).
- **Runtime Policy Enforcement** (`core/runtime_policy_enforcement`, 7
  testes) — decorator `@enforce` que bloqueia estruturalmente a execução de
  uma função não autorizada (enforcement de aplicação, não kernel/eBPF).
- **Meta-Governance Layer** (`core/meta_governance`, 8 testes) — auditoria
  de compliance de checks de saúde entre nós de uma federação.
- **Regulatory Simulation Sandbox** (`core/regulatory_simulation`, 7 testes)
  — impacto em cascata de mudança operacional hipotética via grafo de
  conhecimento + sandbox regulatório.

### Notes
- `shared/schemas.py`: `SCHEMA_VERSION` `0.2.0` → `0.3.0`, ~20 contratos
  novos.
- Os 4 itens sem extração real (`Neuro-Symbolic Governance`, `Cognitive
  Architecture Governance`, `AGI & Civilization Risk Governance`,
  `AI Diplomacy & International Governance`) permanecem só como design em
  `docs/architecture/` — nenhuma implementação responsável possível sem
  pesquisa/infraestrutura que o projeto não tem (decisão explícita, não
  omissão).
- `WORKLOG.md` (novo): log cronológico de trabalho por sessão, complementar
  a este CHANGELOG.

## [0.3.0] - 2026-08-20 — V2 completo: 4 ondas, 19 capacidades de AI Governance

**As 19 capacidades do V2 estão implementadas com testes reais** — 175
testes novos (`pytest core/` cobre 388 no total do projeto: 213 do V1 + 175
do V2). GraphRAG e Regulatory Knowledge Graph foram consolidados num único
módulo (mesma capacidade, nenhuma das 20 linhas do ROADMAP original
descartada). Mesmo rigor do V1: composição real dos motores existentes, sem
mocks nos módulos de produção, limitações documentadas honestamente.

### Added — Onda 1 (extensões diretas de módulos V1)
- **Fairness Audit** (`core/fairness_audit`, 10 testes) — disparate impact
  (regra dos 80%) e diferença de paridade demográfica, 100% estatístico.
- **Blockchain Audit Layer** (`core/blockchain_audit_layer`, 13 testes) —
  checkpoints Merkle sobre a hash-chain do `audit_logs`, com provas de
  inclusão verificáveis.
- **Sensitive Data Scanner** (`core/sensitive_data_scanner`, 9 testes) —
  evolui `pii_detection` para escanear `.txt`/`.pdf`/`.docx`.
- **AI Observability** (`core/ai_observability`, 7 testes) — métricas reais
  de latência/status por chamada, exportáveis em formato Prometheus.

### Added — Onda 2 (governança declarativa e proveniência)
- **Constitutional AI** (`core/constitutional_ai`, 10 testes) — 6 princípios
  declarativos ("linhas vermelhas") compilados em checks executáveis.
- **Regulatory Knowledge Graph / GraphRAG** (`core/regulatory_knowledge_graph`,
  12 testes) — grafo real de artigos da LGPD (`networkx`), arestas extraídas
  por regex de menções textuais reais no corpus, não fabricadas.
- **Human Oversight** (`core/human_oversight`, 10 testes) — fila real de
  revisão humana (`pending -> approved/rejected`).
- **Traceability** (`core/traceability`, 7 testes) — agrupa eventos de
  auditoria correlacionados numa cadeia de proveniência consultável.

### Added — Onda 3 (resiliência e simulação regulatória)
- **Red Team Lab** (`core/red_team_lab`, 10 testes) — harness de 12 ataques
  reais contra `prompt_security`. **Achado real**: taxa de detecção medida
  de 50% (gaps em injeção/exfiltração diretas em português e evasão por
  paráfrase/homoglifos) — documentado, não escondido, e virou um incidente
  de exemplo real em `incident_response`.
- **AI Incident Response** (`core/incident_response`, 12 testes) — registro
  real de incidentes + runbook declarativo por severidade (referenciando
  LGPD Art. 48).
- **Regulatory Sandbox** (`core/regulatory_sandbox`, 7 testes) — simulação
  what-if via `policy_engine`+`trust_score` reais, sem gravar em
  `audit_logs`.
- **Regulatory Auto-Update** (`core/regulatory_auto_update`, 9 testes) —
  manifesto de hashes + diff determinístico do corpus local (não busca fonte
  externa — decisão de risco deliberada).

### Added — Onda 4 (multi-agente e privacidade avançada)
- **Multi-Agent Governance** (`core/multi_agent_governance`, 7 testes) —
  registro declarativo de agentes e ações permitidas.
- **Agent Tribunal** (`core/agent_tribunal`, 7 testes) — adjudica um
  veredito único entre `PolicyDecision` concorrentes (fecha TODO real do
  `policy_engine` V1).
- **Memory Governance** (`core/memory_governance`, 8 testes) — redação
  automática de PII real antes de persistir memória de longo prazo.
- **Self-Healing Governance** (`core/self_healing_governance`, 5 testes) —
  detecta falha + abre incidente real + sugere remediação (nunca corrige
  dados/código sozinho, por decisão de risco).
- **Synthetic Data** (`core/synthetic_data`, 11 testes) — CPF sintético com
  dígito verificador módulo 11 real, validado por round-trip contra
  `pii_detection.detect()`.
- **Differential Privacy** (`core/differential_privacy`, 13 testes) —
  mecanismo de Laplace real (`numpy`) + `PrivacyBudget`.
- **Federated Governance** (`core/federated_governance`, 8 testes) —
  agregação entre nós sem centralizar `TrustScoreResult` bruto.

### Added — Documentação
- `shared/schemas.py`: `SCHEMA_VERSION` `0.1.0` → `0.2.0`, ~25 contratos
  novos (um bloco por capacidade V2).
- `docs/architecture/v3-frontier-research.md` e
  `docs/architecture/v4-systemic-civilizational.md` — design real (não
  stub) das 12 capacidades V3/V4, incluindo por que cada uma não é V2 e sua
  ligação com os módulos V1/V2 já existentes.
- `notebooks/<modulo>_dev_log.ipynb` (19 novos) com outputs de execução
  real capturados, mesmo padrão do V1.

## [0.2.0] - 2026-08-20 — V1 completo: Onda 2 (RIPD Engine, Dashboard, Governance Copilot)

**Os 10 itens do V1 estão implementados com testes reais** — 213 testes
passando (`pytest core/ apps/`): 141 da Onda 1 + 10 do RIPD Engine + 49 do
Dashboard + 13 do Governance Copilot.

### Added
- **RIPD Engine** (`core/ripd_engine`, 10 testes) — primeiro módulo do
  projeto a COMPOR de verdade os 7 módulos da Onda 1 (nenhum mock): escaneia
  a própria descrição do projeto em busca de PII vazada, avalia políticas
  LGPD aplicáveis, roda scan opcional de prompt security, recupera contexto
  regulatório via RAG, fecha o ciclo de injeção de dependência
  `trust_score` → `explainability`, agrega mitigações e monta um resumo
  executivo 100% determinístico (nunca LLM). Registra evento de auditoria
  real a cada geração. `generate_ripd(project_name, project_description,
  data_categories, legal_basis, context=None) -> RIPDReport`. Bug de
  estabilidade em Windows corrigido (access violation intermitente no
  primeiro carregamento do `sentence-transformers`, causada por
  materialização paralela de pesos em múltiplas threads).
- **Dashboard** (`apps/dashboard`, 49 testes) — app Streamlit com 5 seções
  (Visão geral, Gerador de RIPD, Scanner de PII, Scanner de Prompt Security,
  Auditoria) e `GovernanceCopilotClient`, cliente HTTP fino (httpx) contra o
  contrato de API do `governance_copilot`, desenvolvido em paralelo antes do
  backend existir e validado via `httpx.MockTransport`. Lógica de negócio
  extraída em funções puras testáveis, desacopladas de `streamlit.*`.
- **Governance Copilot** (`core/governance_copilot`, 13 testes) — aplicação
  FastAPI que expõe os módulos da Onda 1 como serviço HTTP: `GET /health`,
  `POST /api/v1/pii/detect`, `POST /api/v1/prompt-security/scan`,
  `POST /api/v1/policy/evaluate`, `POST /api/v1/ripd/generate`,
  `GET /api/v1/audit/verify`, `GET /api/v1/audit/events`. Nenhuma lógica de
  domínio reimplementada — cada endpoint é uma casca fina sobre a função
  pública real do módulo correspondente, com respostas tipadas diretamente
  pelos modelos de `shared/schemas.py`. Fecha o contrato que o Dashboard já
  consumia desde seu próprio ciclo de dev. Testado via
  `fastapi.testclient.TestClient` em processo, sem mocks — inclusive
  `/api/v1/ripd/generate`, que aciona de verdade os 7 módulos da Onda 1.

### Notes
- Sem autenticação e sem CORS no `governance_copilot` nesta versão (V1 é uso
  local, dashboard e API na mesma máquina) — TODO explícito de V2.
- `notebooks/00_master_pipeline.ipynb` atualizado: a demonstração ponta a
  ponta agora chama a aplicação FastAPI real (`core.governance_copilot.api`)
  em vez de importar `core/ripd_engine` diretamente, replicando o caminho de
  produção usado pelo Dashboard.

## [0.1.0] - 2026-08-19 — V1 Onda 1: núcleo de módulos independentes

**141 testes passando** em 7 módulos construídos em paralelo por agentes, cada um
consumindo os contratos compartilhados de `shared/schemas.py`. Cada módulo achou e
corrigiu pelo menos um bug real durante o próprio desenvolvimento (documentado nos
CHANGELOGs locais e nos notebooks de dev-log) — não é código que só "compilou".

### Added
- Estrutura inicial do repositório (`core/`, `apps/`, `shared/`, `notebooks/`,
  `status/`, `docs/`), contratos Pydantic compartilhados, `ROADMAP.md` com as 40
  capacidades mapeadas em V1–V4, ADR 0001, brainstorm original preservado em
  `docs/origin/rascunho.md`.
- **Policy Engine** (`core/policy_engine`, 25 testes) — motor declarativo de 9
  políticas LGPD reais (YAML), suporta múltiplas decisões simultâneas.
  `evaluate(data_categories, legal_basis, context=None, policies_path=None) -> list[PolicyDecision]`.
- **PII Detection** (`core/pii_detection`, 25 testes) — regex determinístico
  (CPF/CNPJ/RG/e-mail/telefone/CEP/data nascimento) + heurística de nome +
  enriquecimento opcional via spaCy. Bug corrigido: matcher de palavra sensível
  não pegava texto sem acento (accent-folding).
  `detect(text) -> PIIDetectionResult`.
- **Prompt Security** (`core/prompt_security`, 39 testes) — scanner heurístico de
  prompt injection/jailbreak/exfiltração/ofuscação. Pesos de severidade
  recalibrados para fail-cautious (qualquer achado MEDIUM+ já marca inseguro).
  `scan(prompt) -> PromptSecurityResult`.
- **Explainability** (`core/explainability`, 12 testes) — motor genérico
  determinístico de narrativa a partir de fatores ponderados, standalone (usado
  via injeção de dependência pelos outros módulos).
  `explain(factors, subject, narrative_template=None) -> ExplainabilityResult`.
- **Trust Score** (`core/trust_score`, 20 testes) — agregador de AI Trust Score
  (base 100, penalidades por PII sensível/política/prompt inseguro, DENY = veto).
  `compute_trust_score(pii_result, policy_decisions, prompt_security=None, explanation=None) -> TrustScoreResult`.
- **Audit Logs** (`core/audit_logs`, 6 testes) — hash-chain local estilo
  blockchain simplificado, com teste de detecção de adulteração. Bug corrigido:
  hash calculado sobre `isoformat()` mas persistido via serialização Pydantic
  (`Z` vs `+00:00`) causava falso negativo de integridade.
  `AuditLogger.record_event(...)`, `.verify_chain() -> bool`, `default_logger()`.
- **Regulatory RAG** (`core/regulatory_rag`, 14 testes) — 12 resumos/paráfrases
  (explicitamente identificados como tal, não texto oficial) dos principais
  artigos da LGPD, embeddings locais (sentence-transformers) + ChromaDB. Ajuste
  de engenharia: disclaimer repetido em todo chunk dominava a similaridade de
  cosseno — embedding agora exclui o disclaimer, distância trocada para cosine.
  `build_index(persist_dir=None) -> int`, `query(text, k=3) -> RAGQueryResult`.

### Infra
- Ambiente Python movido de `.venv/` (dentro do repo, num drive sincronizado
  pelo Google Drive Desktop — muito lento para I/O de pacotes) para
  `C:/Users/Yuri_/.venvs/athenagov-ai` (disco local). `requirements.txt` dividido
  em `requirements-core.txt`/`requirements-heavy.txt` para instalação mais rápida.
