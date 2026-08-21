# ROADMAP — Themis AI

Documento mestre de escopo. Todas as 40 capacidades concebidas no brainstorm original
(`docs/origin/rascunho.md`) estão preservadas aqui — nenhuma foi descartada, apenas
sequenciada em fases realistas. "Inviável agora" ≠ "fora do projeto": é V3/V4.

Critério de fase: **V1 é implementado com engenharia real (código + testes + notebook
de dev-log), sem simulações.** V2 evolui o mesmo padrão. V3/V4 permanecem como
arquitetura documentada (ADR + design doc) até que haja um ciclo dedicado a elas —
não serão criadas pastas com código stub fingindo implementação.

Estado de cada capacidade é rastreado também em `status/*.json` (uma por módulo)
e agregado por `notebooks/00_master_pipeline.ipynb`.

## V1 — Foundation (EM EXECUÇÃO AGORA)

Núcleo operacional real, com testes, rodando localmente (sem custo de API — motor
de IA local: sentence-transformers + FAISS/Chroma + regras/NER).

| # | Capacidade | Pasta | Status |
|---|-----------|-------|--------|
| 1 | Policy Engine | `core/policy_engine/` | ✅ done (25 testes) |
| 2 | PII Detection | `core/pii_detection/` | ✅ done (25 testes) |
| 3 | Prompt Security (injection/jailbreak) | `core/prompt_security/` | ✅ done (39 testes) |
| 4 | Explainability | `core/explainability/` | ✅ done (12 testes) |
| 5 | AI Trust Score | `core/trust_score/` | ✅ done (20 testes) |
| 6 | Audit Logs (hash-chain) | `core/audit_logs/` | ✅ done (6 testes) |
| 7 | Regulatory RAG (base local LGPD) | `core/regulatory_rag/` | ✅ done (14 testes) |
| 8 | RIPD Engine (gerador automático) | `core/ripd_engine/` | ✅ done (10 testes) |
| 9 | Governance Copilot (orquestrador + API) | `core/governance_copilot/` | ✅ done (13 testes) |
| 10 | Dashboard | `apps/dashboard/` | ✅ done (49 testes) |

Legenda: ⏳ planejado · 🔄 em andamento · ✅ concluído com testes verdes · ⚠️ bloqueado

**V1 completo: os 10 itens acima estão implementados com testes reais.** Falta
apenas a etapa manual de tag/publicação — ver "Pendências para fechar o V1"
logo abaixo — que fica reservada para o usuário (Fase 2 operacional, não é
trabalho de engenharia).

### Pendências para fechar o V1 (reservadas — ação do usuário)

Estas ações não são código: dependem de decisão/execução do dono do projeto
(credenciais, publicação, deploy) e ficam **exclusivamente para a Fase 2**,
já preparadas para serem feitas quando ele quiser:

- Criar a tag git `v1.0.0` (todo o trabalho de código está pronto; falta só
  o comando `git tag v1.0.0 && git push origin v1.0.0`, quando o usuário
  decidir publicar).
- Subir o backend (`uvicorn core.governance_copilot:app`) e o dashboard
  (`streamlit run apps/dashboard/app.py`) num ambiente persistente
  (local sempre disponível, container, ou serviço cloud) — hoje ambos rodam
  só sob demanda na máquina de desenvolvimento.
- Decidir se/quando publicar o repositório (visibilidade, licença) — o
  `README.md` e o `CHANGELOG.md` já estão prontos para isso.
- Revisão jurídica humana do conteúdo do `regulatory_rag/corpus` (paráfrases
  da LGPD) antes de qualquer uso além de portfólio/demonstração — o próprio
  corpus já se identifica como paráfrase ilustrativa, não texto oficial, mas
  uso real em produção exige validação por um profissional jurídico.

## V2 — AI Governance (EM EXECUÇÃO AGORA)

Mesmo critério de qualidade do V1: cada capacidade é implementada com código real +
testes + notebook de dev-log, sem stub. GraphRAG e Regulatory Knowledge Graph foram
consolidados num único módulo (`regulatory_knowledge_graph`) por serem, na prática, a
mesma capacidade (grafo de conhecimento sobre o corpus regulatório) — nenhuma das 20
linhas do brainstorm original foi descartada, só desduplicada. Sequenciado em 4 ondas
por dependência/risco (mesmo padrão da Onda 1/Onda 2 do V1).

| # | Capacidade | Pasta | Onda | Status |
|---|-----------|-------|------|--------|
| 1 | Fairness Audit | `core/fairness_audit/` | 1 | ✅ done (10 testes) |
| 2 | Blockchain Audit Layer (evolução do hash-chain do Audit Logs) | `core/blockchain_audit_layer/` | 1 | ✅ done (13 testes) |
| 3 | Sensitive Data Scanner (evolução do PII Detection p/ documentos) | `core/sensitive_data_scanner/` | 1 | ✅ done (9 testes) |
| 4 | AI Observability (traces/metrics reais) | `core/ai_observability/` | 1 | ✅ done (7 testes) |
| 5 | Constitutional AI (regras declarativas → políticas executáveis) | `core/constitutional_ai/` | 2 | ✅ done (10 testes) |
| 6 | Regulatory Knowledge Graph (GraphRAG) | `core/regulatory_knowledge_graph/` | 2 | ✅ done (12 testes) |
| 7 | Human Oversight (fila/decisão de revisão humana) | `core/human_oversight/` | 2 | ✅ done (10 testes) |
| 8 | Traceability (proveniência entre eventos/decisões) | `core/traceability/` | 2 | ✅ done (7 testes) |
| 9 | Red Team Lab (harness de ataques contra os módulos V1) | `core/red_team_lab/` | 3 | ✅ done (10 testes) |
| 10 | AI Incident Response | `core/incident_response/` | 3 | ✅ done (12 testes) |
| 11 | Regulatory Sandbox (simulação what-if de cenários) | `core/regulatory_sandbox/` | 3 | ✅ done (7 testes) |
| 12 | Regulatory Auto-Update (versionamento/diff do corpus) | `core/regulatory_auto_update/` | 3 | ✅ done (9 testes) |
| 13 | Multi-Agent Governance | `core/multi_agent_governance/` | 4 | ✅ done (7 testes) |
| 14 | Agent Tribunal | `core/agent_tribunal/` | 4 | ✅ done (7 testes) |
| 15 | Memory Governance | `core/memory_governance/` | 4 | ✅ done (8 testes) |
| 16 | Self-Healing Governance | `core/self_healing_governance/` | 4 | ✅ done (5 testes) |
| 17 | Synthetic Data | `core/synthetic_data/` | 4 | ✅ done (11 testes) |
| 18 | Differential Privacy | `core/differential_privacy/` | 4 | ✅ done (13 testes) |
| 19 | Federated Governance | `core/federated_governance/` | 4 | ✅ done (8 testes) |

**V2 completo: as 19 capacidades acima estão implementadas com testes reais**
(175 testes) — mesmo rigor do V1: composição real dos motores V1 sem mocks,
limitações documentadas honestamente (ver o `CHANGELOG.md` de cada módulo),
e ao menos um achado real e não-trivial durante o desenvolvimento (ex.
`red_team_lab` mediu 50% de taxa de detecção real do `prompt_security` e
abriu um incidente de verdade em `incident_response` a partir disso).

### Onda 1 — extensões diretas de módulos V1 (baixo risco, sem infra nova)

Cada item evolui um módulo V1 já existente ou é estatística/observabilidade
determinística — sem dependência de infraestrutura externa nova.

- **Fairness Audit**: métricas de equidade determinísticas (disparate impact / regra
  dos 80%, diferença de paridade demográfica) sobre um conjunto de decisões +
  atributo protegido. Puro `numpy`/estatística, sem ML.
- **Blockchain Audit Layer**: evolui `audit_logs` com checkpoints Merkle sobre a
  hash-chain existente (prova de inclusão local, sem depender de blockchain pública
  — mesma honestidade de escopo já documentada em `audit_logs/CHANGELOG.md`).
- **Sensitive Data Scanner**: evolui `pii_detection` para escanear documentos
  (`.txt`/`.pdf`/`.docx`), extraindo texto e reaplicando o motor de detecção já
  existente — nenhuma lógica de PII duplicada.
- **AI Observability**: decorator/context manager determinístico que envolve
  chamadas aos módulos V1 e produz métricas estruturadas (latência, contagem,
  status) — formato compatível com scraping OpenTelemetry/Prometheus, sem exigir um
  coletor rodando para os testes passarem.

### Onda 2 — camada de governança declarativa e proveniência

- **Constitutional AI**: constituição declarativa (YAML) de princípios → compilada
  em checks executáveis, mesmo padrão declarativo do `policy_engine`.
- **Regulatory Knowledge Graph (GraphRAG)**: grafo de artigos/relações da LGPD
  (`networkx`) construído a partir do corpus já existente do `regulatory_rag`,
  navegável além da busca por similaridade pura.
- **Human Oversight**: fila determinística de decisões que exigem revisão humana
  (alimentada por `PolicyDecisionStatus.REQUIRES_HUMAN_REVIEW`), com fluxo de
  aprovação/rejeição registrado.
- **Traceability**: encadeia eventos de auditoria relacionados (ex. todos os passos
  de um mesmo RIPD) numa cadeia de proveniência consultável.

### Onda 3 — resiliência e simulação regulatória

- **Red Team Lab**, **AI Incident Response**, **Regulatory Sandbox**,
  **Regulatory Auto-Update**.

### Onda 4 — multi-agente e privacidade avançada (maior complexidade/infra)

- **Multi-Agent Governance**, **Agent Tribunal**, **Memory Governance**,
  **Self-Healing Governance**, **Synthetic Data**, **Differential Privacy**,
  **Federated Governance**.

Legenda: ⏳ planejado · 🔄 em andamento · ✅ concluído com testes verdes · ⚠️ bloqueado

### Pendências para fechar o V2 (reservadas — ação do usuário)

Mesmo padrão do V1: nada de código pendente, só decisões/execução do dono do
projeto, reservadas para a Fase 2:

- Tag git `v2.0.0` (ou incluir o V2 na mesma `v1.0.0` se o usuário preferir
  publicar tudo de uma vez — decisão dele, não técnica).

~~Achado real de `red_team_lab` (gaps de detecção do `prompt_security` em
português) — corrigido em V5, ver `core/prompt_security/CHANGELOG.md`
`[0.1.1]`.~~

## V3 — Frontier Research (longo prazo, ciclo dedicado)

Estas exigem disciplinas fora de engenharia de software convencional
(lógica formal, teoria de prova). Ver
**[docs/architecture/v3-frontier-research.md](docs/architecture/v3-frontier-research.md)**
para o design completo de cada uma. **Onda 5 (2026-08-21)**: extraído e
implementado — com o mesmo rigor de código+testes+notebook do V1/V2 — o
núcleo realmente codificável de 6 dos 8 itens, honestamente reescopado
(nunca fingindo a coisa inteira):

| Item original | Status | Extração real |
|---|---|---|
| Formal Verification Layer (TLA+/Alloy/Coq) | ✅ extraído (6 testes) | `core/formal_verification/` — model checking por enumeração exaustiva (não prova simbólica) |
| AI Constitution Compiler | ✅ extraído (10 testes) | `core/constitution_compiler/` — detecção estática de conflitos |
| Neuro-Symbolic Governance | ⏳ só design | exigiria treinar modelo real, quebra o determinismo do projeto |
| Causal AI Governance | ✅ extraído (6 testes) | `core/causal_fairness/` — disparate impact estratificado, Paradoxo de Simpson |
| Behavioral Monitoring | ✅ extraído (6 testes) | `core/behavioral_monitoring/` — drift real via teste KS (`scipy`) |
| Cognitive Attack Detection | ✅ extraído (7 testes) | `core/cognitive_attack_detection/` — scan multi-turno com reassemblagem |
| Cognitive Architecture Governance | ⏳ só design | exige um framework de agente com loop de raciocínio que o projeto não tem |
| Runtime Policy Enforcement Kernel | ✅ extraído (7 testes) | `core/runtime_policy_enforcement/` — enforcement de aplicação (decorator), não kernel/eBPF |

## V4 — Systemic / Civilizational (aspiracional, documentação de visão)

Ver **[docs/architecture/v4-systemic-civilizational.md](docs/architecture/v4-systemic-civilizational.md)**
para a visão completa de cada item. **Onda 5**: extraído o núcleo real de 2
dos 4 itens:

| Item original | Status | Extração real |
|---|---|---|
| Meta-Governance Layer | ✅ extraído (8 testes) | `core/meta_governance/` — compliance de checks entre nós de uma federação |
| AGI & Civilization Risk Governance | ⏳ só design | sem metodologia de risco estabelecida para ancorar (V4 permanece aspiracional) |
| Regulatory Simulation Sandbox | ✅ extraído (7 testes) | `core/regulatory_simulation/` — impacto em cascata de mudança operacional hipotética (não simula mudança na lei em si) |
| AI Diplomacy & International Governance | ⏳ só design | exigiria corpus jurídico real de múltiplas jurisdições + validação humana |

**Onda 5 completa: 8 módulos extraídos, 57 testes novos.** Total do projeto:
**445 testes passando** (`pytest core/ apps/`). Os 4 itens que permanecem só
como design (`Neuro-Symbolic Governance`, `Cognitive Architecture
Governance`, `AGI & Civilization Risk Governance`, `AI Diplomacy &
International Governance`) continuam assim por decisão de honestidade
técnica, não por preguiça — ver a justificativa de cada um nos respectivos
docs de arquitetura.

## V5 — Melhorias e débito técnico

**10 dos 15 itens resolvidos em 2026-08-21** (código real + testes, mesmo
rigor do resto do projeto) — ver `CHANGELOG.md` raiz `[0.6.0]` e
**[docs/architecture/future-improvements.md](docs/architecture/future-improvements.md)**
para o mapeamento completo item→fix. 1 item parcialmente resolvido (health
check sob demanda existe; falta só o disparador externo periódico, que é
configuração de deploy, não código). 4 itens continuam em aberto — 2 exigem
infraestrutura externa (ancoragem do Merkle, OCR), 2 são limites de escopo
deliberados (classificador multi-turno quebraria o determinismo do projeto;
fonte externa de LGPD exige validação jurídica antes de automatizar).

**32 testes novos nesta rodada.** Total do projeto: **477 testes passando**
(`pytest core/ apps/`).

## Teto do projeto — não há V6/V7 de capacidade nova

Confirmado explicitamente (a pedido do usuário, registrado em `WORKLOG.md`
2026-08-21): **V1 + V2 + V3/V4 (extração real) + V5 é o teto do escopo
técnico do projeto.** As 41 capacidades rastreadas cobrem 100% do brainstorm
original (`docs/origin/rascunho.md`); os itens que faltam em V3/V4/V5 são
deliberadamente não-implementados (design ou decisão de risco), não dívida
esquecida. Inventar uma "V6" de capacidades novas violaria o próprio
princípio que sustentou o rigor do projeto até aqui — o que resta depois
disto é polimento (portfólio, deploy) e, se necessário, fechar os 4 itens
ainda em aberto do próprio V5 — nunca mais capacidade nova sem vir de um
achado real.

## Convenção de versionamento

- SemVer por módulo (`core/<modulo>/CHANGELOG.md`, começa em `0.1.0`).
- Tag git `v1.0.0` quando os 10 itens do V1 estiverem ✅ (código pronto — ver
  "Pendências para fechar o V1"). Tag `v2.0.0` quando o usuário decidir
  publicar o V2 (código também já pronto — ver "Pendências para fechar o V2").
- Todo bump de versão é registrado no `CHANGELOG.md` raiz (Keep a Changelog).
- Decisões de arquitetura ficam em `docs/decisions/NNNN-titulo.md` (formato ADR);
  design de V3/V4 (sem decisão de implementação ainda) fica em `docs/architecture/`.
