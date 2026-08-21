# WORKLOG — Themis AI

Log de trabalho por sessão/onda, complementar ao `CHANGELOG.md` (que é
orientado a release/versão). Aqui o registro é cronológico e operacional:
o que foi feito, o que ficou pendente, e por quê — para retomar contexto
rápido numa sessão futura sem precisar reler todo o histórico de commits.

## 2026-08-20 — Sessão de recuperação + V2 completo + extração V3/V4

### Contexto inicial
Sessão anterior caiu no meio da Onda 2 do V1 (`core/governance_copilot`
existia só como pasta `tests/` vazia; `core/ripd_engine` sem
`status/ripd_engine.json` nem notebook). Recuperação:

1. Construído `core/governance_copilot` (API FastAPI) do zero — 13 testes.
2. Recuperadas as lacunas do `ripd_engine` (status.json + notebook).
3. **V1 fechado**: 10/10 itens, 213 testes.

### V2 completo — AI Governance, 4 ondas, 19 capacidades, 175 testes
Ver `CHANGELOG.md` seção `[0.3.0]` para a lista completa por onda. Achado
real de destaque: `red_team_lab` mediu 50% de taxa de detecção do
`prompt_security` (gaps reais em PT) e abriu um incidente de exemplo real em
`incident_response`.

**Total após V2: 388 testes passando** (`pytest core/ apps/`).

### V3/V4 — decisão de escopo
O ROADMAP original marca V3/V4 como "design documentado, não código stub" —
correto para a maioria dos 12 itens (ex. `AGI & Civilization Risk
Governance` não tem implementação de software responsável). Mas alguns itens
têm um núcleo real extraível sem fingir a coisa inteira. Decisão (com o
usuário, ver `AskUserQuestion` desta sessão): extrair e implementar com o
mesmo rigor (código + testes + notebook) só a parte realmente codificável de
cada item; o resto continua em `docs/architecture/v3-*.md`/`v4-*.md`.

**Mapeamento de extração (Onda 5):**

| Item original (V3/V4) | Extração real codificada | Pasta |
|---|---|---|
| Formal Verification Layer | Verificação exaustiva de invariantes em espaço de estados finito (model checking por enumeração, não prova simbólica) | `core/formal_verification/` |
| AI Constitution Compiler | Detecção estática de conflitos entre artigos de `constitution.yaml` | `core/constitution_compiler/` |
| Causal AI Governance | Disparate impact estratificado por variável confundidora (detecção de Paradoxo de Simpson) | `core/causal_fairness/` |
| Behavioral Monitoring | Detecção de drift real via teste KS (`scipy.stats.ks_2samp`) sobre séries de `trust_score`/observability | `core/behavioral_monitoring/` |
| Cognitive Attack Detection | Scan multi-turno de conversas (reassembla payloads divididos entre turnos, re-varre com `prompt_security`) | `core/cognitive_attack_detection/` |
| Runtime Policy Enforcement Kernel | Enforcement real em nível de aplicação (decorator que bloqueia a chamada da função se não autorizada) — não kernel/eBPF | `core/runtime_policy_enforcement/` |
| Meta-Governance Layer | Auditoria de compliance entre múltiplos nós de uma federação (governança sobre governança) | `core/meta_governance/` |
| Regulatory Simulation Sandbox | Simulação de impacto em cascata de uma mudança regulatória hipotética, via grafo de conhecimento + sandbox | `core/regulatory_simulation/` |

**Continuam só como design doc (nenhuma implementação responsável possível
sem infraestrutura/pesquisa que o projeto não tem)**:
- Neuro-Symbolic Governance — exigiria treinar um modelo real, quebra o
  determinismo 100% documentado do projeto.
- Cognitive Architecture Governance — exige um framework de agente com loop
  de raciocínio próprio, que não existe neste projeto.
- AGI & Civilization Risk Governance — sem metodologia de risco estabelecida
  para ancorar (ao contrário da LGPD, que tem base legal concreta).
- AI Diplomacy & International Governance — exigiria corpus jurídico real de
  múltiplas jurisdições + validação jurídica humana antes de qualquer linha
  de código.

### Onda 5 — status: ✅ COMPLETA

8 módulos implementados, 57 testes, 445 no total do projeto. Ver
`CHANGELOG.md` seção `[0.4.0]` para a lista completa e os achados reais
(destaque: `constitution_compiler` encontrou 11 conflitos de severidade na
constituição de produção, mais do que o esperado — achado real, documentado,
não escondido).

### Rebrand: AthenaGov AI → Themis AI

A pedido do usuário ("cria um nome que reflita a todas essas capacidades"),
o projeto foi renomeado. Aplicado em 28 arquivos (README, CHANGELOG,
ROADMAP, docstrings) via find-replace controlado — `docs/origin/rascunho.md`
e `rascunho.md` (raiz) preservados verbatim, por serem registro histórico do
brainstorm original sob o nome antigo.

### Plano de melhorias futuras registrado

`docs/architecture/future-improvements.md` consolida os 15 itens de
débito técnico/melhoria identificados ao longo de todo o desenvolvimento
(V1 até Onda 5) — nada foi perdido, tudo priorizado (Alta/Média/Baixa) e
pronto para retomar quando o usuário quiser, sem precisar reler todo o
histórico.

### Estado final desta sessão

- **445 testes passando** (`pytest core/ apps/`).
- **41 módulos** em `core/` (9 V1 + 19 V2 + 8 extração V3/V4 + `apps/dashboard`).
- **V1 e V2 completos.** V3/V4: núcleo real extraído (8/12 itens); 4 itens
  permanecem design-only por decisão técnica explícita.
- **Nada pendente de código** desta rodada — só decisões de publicação
  reservadas ao usuário (ver ROADMAP.md) e o plano de melhorias futuras
  (não implementado, documentado).
- Todo o trabalho está commitado localmente; push fica a critério do
  usuário (nunca feito automaticamente nesta sessão).

## 2026-08-21 (continuação) — Discussão de naming + polimento de portfólio

### Registro do rename

Usuário pediu para o processo de decisão do nome (Themis AI) ficar
registrado formalmente, não só o resultado. Criado `NAMING.md` (raiz) com
contexto, opções consideradas, critérios e execução. `README.md` ganhou nota
apontando pra lá.

### Pergunta: "só falta isso ou tem V6/V7?"

Resposta dada e registrada aqui: **não existe V6/V7 planejado** — o teto do
projeto é V1+V2+V3/V4(extração real)+V5(débito técnico, já mapeado). Inventar
mais fases violaria o próprio princípio de "nada é inventado sem vir de algum
lugar concreto" que sustentou o projeto até aqui. 41 capacidades rastreadas
cobrem 100% do brainstorm original.

### Polimento de portfólio (a pedido do usuário, exceto item 1)

Usuário pediu para implementar as sugestões de portfólio, com a demo pública
(item 1) reservada para ele mesmo fazer depois:

1. **Demo pública** — NÃO implementado, é trabalho do usuário (ver
   `PARA_VOCE_FAZER.md`).
2. **Notebook capstone** (`notebooks/99_capstone_full_pipeline.ipynb`) — os
   36 módulos de `core/` encadeados num único cenário fictício (`TrustLend
   AI`), execução real capturada. Reproduziu ao vivo, no mesmo cenário, os
   dois achados reais já conhecidos (gap do `prompt_security` em PT; delta
   zero do `regulatory_sandbox` quando o cenário já parte com
   `human_review=True`).
3. **CI real** (`.github/workflows/tests.yml`) — roda `pytest core/ apps/`
   a cada push/PR, sem segredos.
4. **`Dockerfile` + `docker-compose.yml`** — API + Dashboard com um comando.
   **Build não validado nesta sessão** (Docker Desktop não estava rodando no
   ambiente) — ver `PARA_VOCE_FAZER.md` item 1.
5. **`CASE_STUDY.md`** — decisões de engenharia reais, os 3 achados
   (gap do `prompt_security`, Paradoxo de Simpson, 11 conflitos na
   constituição), números de rigor.
6. **Relatório de cobertura** — gerado via `pytest-cov` (`htmlcov/`, não
   commitado — artefato regenerável, comando documentado em
   `PARA_VOCE_FAZER.md`).

### Rename adicional encontrado durante o polimento

`ATHENAGOV_API_URL` (env var) e o prefixo de métrica `athenagov_` em
`core/ai_observability` não tinham sido pegos pelo find-replace original
(case diferente de "AthenaGov"). Renomeados para `THEMIS_API_URL` e
`themis_` respectivamente — testes atualizados e revalidados (56/56).

### Novo arquivo raiz: `PARA_VOCE_FAZER.md`

Fonte única de verdade do que é exclusivamente trabalho do usuário (demo,
tags, licença, revisão jurídica, priorização do V5) — separado do
`docs/architecture/future-improvements.md` (que é débito técnico, trabalho
meu quando ele pedir).

## 2026-08-21 (continuação 2) — V5 completa: fecha 10 dos 15 itens de débito técnico

Usuário pediu explicitamente para fechar o V5 e terminar tudo para deixar o
projeto pronto para subir. Resolvido, com código real + testes:

1. **`prompt_security`** (item 1): achado real — os 2 gaps que `red_team_lab`
   mediu (RT-01, RT-06) eram bugs de regex reais (palavra extra entre
   gatilho e alvo), não limitação fundamental de PT. Corrigidos. Taxa de
   detecção real: 50% → 67%.
2. **`constitution_compiler`** (item 2): distingue overlap real (bloqueante)
   de overlap por vacuidade (informativo). Constituição de produção: 11
   falsos-positivos → 2 conflitos reais.
3. **`governance_copilot`** (itens 3, 4, 6, 7, 8, 14 + versão honesta do 5):
   reescrito com auth opcional (`X-API-Key`), CORS configurável, fila de
   revisão humana automática, trilha de auditoria por `trace_id` para
   endpoints que antes não geravam evento nenhum, `@enforce` real em todo
   endpoint, `GET /metrics` real, RIPDs persistidos e consultáveis,
   `POST /api/v1/health-check/run` sob demanda (sem scheduler embutido —
   documentado, não fingido). 17 testes novos, os 13 antigos inalterados.
4. **`differential_privacy`** (item 11): `advanced_composition_epsilon()` —
   teorema real de Dwork/Rothblum/Vadhan 2010.
5. **`fairness_audit`** (item 12): `chi_square_significance()` — teste
   qui-quadrado real via scipy.

**32 testes novos, 477 no total.** Itens 9 (ancoragem externa), 10 (OCR)
ficam abertos (infraestrutura externa real); 13 e 15 continuam
deliberadamente não implementados (decisão de risco/escopo).

`docs/architecture/future-improvements.md`, `ROADMAP.md`, `CHANGELOG.md`
raiz, `README.md` e `PARA_VOCE_FAZER.md` todos atualizados para refletir o
estado atual — nada ficou desatualizado apontando gaps já corrigidos.

### Confirmação registrada: teto do projeto

Perguntado se falta V6/V7 — resposta registrada em `ROADMAP.md` (seção "Teto
do projeto"): não há capacidade nova planejada. V1+V2+V3/V4(real)+V5 é o
teto. As 41 capacidades cobrem 100% do brainstorm original.

<!-- ONDA5_STATUS_MARKER -->
