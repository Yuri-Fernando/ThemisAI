# V3 — Frontier Research: design de arquitetura (sem código)

Documento de arquitetura para as 8 capacidades do V3 do `ROADMAP.md`. Por
decisão explícita de escopo (ver `ROADMAP.md` e `docs/decisions/0001-scope-v1.md`),
**nenhuma delas ganha pasta em `core/` nem código stub** até que haja um
ciclo dedicado — cada uma exige disciplina fora de engenharia de software
convencional (lógica formal, teoria de prova, pesquisa em segurança
cognitiva). O que existe aqui é o design real: o que a capacidade faria, por
que ela não é V2, quais pré-requisitos técnicos já existem no V1/V2, e quais
lacunas de conhecimento/ferramental precisam ser fechadas antes de codificar.

---

## 1. Formal Verification Layer (TLA+/Alloy/Coq)

**O que seria**: especificar formalmente as invariantes de
`constitutional_ai`/`policy_engine` (ex. "nunca existe um `PolicyDecision`
com `status=ALLOW` quando `context.audit_logging_enabled=False`") em TLA+ ou
Alloy, e verificar mecanicamente que a implementação Python nunca viola essas
invariantes — não é teste (amostra de casos), é prova (cobre o espaço
inteiro de estados).

**Por que não é V2**: exige aprender uma linguagem de especificação formal e
uma disciplina de modelagem completamente diferente de "escrever testes
pytest". O ganho só compensa o custo em componentes com consequência legal
severa se errarem (ex. o motor de decisão `DENY`/`ALLOW` do
`policy_engine`/`agent_tribunal`).

**Pré-requisito já pronto no V1/V2**: as invariantes já estão documentadas em
linguagem natural em `constitutional_ai/constitution.yaml` — a tradução para
TLA+ parte de um alvo já explícito, não de zero.

**Abertura de escopo**: começar pequeno — especificar só a regra de
precedência do `agent_tribunal` (a função mais simples e mais crítica do V2)
em Alloy, como prova de conceito, antes de tentar `policy_engine` inteiro.

---

## 2. AI Constitution Compiler

**O que seria**: um compilador de verdade — não o `constitutional_ai`
(V2, que já interpreta YAML declarativo em runtime) — que traduz uma
constituição de alto nível (linguagem controlada, próxima de português
jurídico) para o YAML executável de `constitutional_ai`, com checagem
estática de conflitos entre princípios (ex. dois artigos que nunca podem
ambos ser satisfeitos simultaneamente).

**Por que não é V2**: `constitutional_ai` (V2) já resolve "regras
declarativas → checks executáveis" da forma simples pedida no ROADMAP
original. Um *compilador* com análise estática de conflitos é um problema de
linguagens formais (satisfiability), não de engenharia de regras.

**Dependência**: `constitutional_ai/constitution.yaml` (V2) é o formato de
saída-alvo do compilador — já existe e está testado.

---

## 3. Neuro-Symbolic Governance

**O que seria**: combinar um componente neural (ex. um classificador de
risco treinado, não regras) com o motor simbólico determinístico que já
existe (`policy_engine`, `constitutional_ai`) — o componente neural sugere,
o simbólico valida/veta, nunca o contrário.

**Por que não é V2**: o V1/V2 inteiro é deliberadamente 100% determinístico,
sem treinamento de modelo (decisão de arquitetura documentada em
`CHANGELOG.md` raiz). Introduzir um componente treinado quebra essa garantia
de auditabilidade determinística — precisa de um ciclo dedicado com dataset
de treino, avaliação de fairness do próprio classificador (`fairness_audit`,
V2, já dá a ferramenta para isso) e um argumento explícito de por que vale a
pena abrir mão de determinismo total nesse ponto específico.

---

## 4. Causal AI Governance

**O que seria**: em vez de correlação (o que `fairness_audit`, V2, mede —
disparidade de taxa de seleção entre grupos), inferência causal: a
disparidade observada é causada pelo atributo protegido, ou por uma variável
confundidora legítima (ex. renda correlacionada com região, que por sua vez
correlaciona com raça)? Exige um grafo causal explícito (DAG) e métodos como
matching ou variáveis instrumentais.

**Por que não é V2**: `fairness_audit` (V2) já documenta essa limitação
explicitamente ("não controla variáveis confundidoras... TODO de onda
futura"). Inferência causal é uma disciplina estatística própria — exige
especificar o DAG causal do domínio (ex. quais variáveis afetam quais em um
processo de concessão de crédito), que é conhecimento de domínio, não só
código.

**Dependência direta**: evolução natural de `core/fairness_audit` (V2).

---

## 5. Behavioral Monitoring

**O que seria**: detectar mudança de comportamento de um sistema de IA ao
longo do tempo (model drift, mudança na distribuição de decisões) comparando
snapshots sucessivos de `ai_observability` (V2) e `trust_score` — não é
"observabilidade" (que já existe no V2), é análise estatística de séries
temporais sobre essa observabilidade.

**Por que não é V2**: `ai_observability` (V2) entrega a captura de métricas;
análise de drift exige escolher e validar testes estatísticos de mudança de
distribuição (ex. teste de Kolmogorov-Smirnov, PSI) — decisão metodológica
que merece ciclo próprio, não uma extensão apressada.

**Dependência direta**: `core/ai_observability` (V2) já é a fonte de dados.

---

## 6. Cognitive Attack Detection

**O que seria**: detectar ataques mais sofisticados que os cobertos por
`prompt_security`/`red_team_lab` (V1/V2) — ataques de manipulação psicológica
em múltiplos turnos de conversa (não um único prompt), que nenhum regex de
mensagem isolada consegue capturar.

**Por que não é V2**: `red_team_lab` (V2) já mediu empiricamente que o
`prompt_security` atual é frágil até contra evasão de turno único
(paráfrase, homoglifos) — endurecer detecção multi-turno antes de fechar os
gaps de turno único seria construir sobre uma fundação sabidamente furada.
TODO sequencial: primeiro fechar os gaps achados por `red_team_lab` (onda de
manutenção do V2), depois abrir a frente multi-turno como V3.

---

## 7. Cognitive Architecture Governance

**O que seria**: governança sobre a arquitetura cognitiva de um agente de IA
(que memórias ele mantém, que ferramentas pode invocar, em que ordem
raciocina) — um nível acima de `memory_governance`/`multi_agent_governance`
(V2, que governam persistência e autorização de ação, respectivamente), mas
sobre o *processo de raciocínio* em si.

**Por que não é V2**: exige um framework de agente real rodando (loop de
raciocínio, ferramentas, memória de trabalho) para ter algo a governar — o
Themis AI V1/V2 é um conjunto de motores determinísticos chamados sob
demanda, não um agente autônomo com loop próprio. Pré-requisito de
infraestrutura que ainda não existe no projeto.

---

## 8. Runtime Policy Enforcement Kernel

**O que seria**: um kernel que intercepta TODA chamada de um sistema de IA a
qualquer recurso (rede, disco, API externa) e aplica `policy_engine`/
`constitutional_ai` em tempo real, no nível do sistema operacional/sandbox —
não uma checagem que o código da aplicação decide chamar (como
`multi_agent_governance.authorize()`, V2), mas uma que não pode ser
contornada pelo código da aplicação.

**Por que não é V2**: `multi_agent_governance` (V2) documenta essa limitação
explicitamente ("checagem declarativa explícita, não interceptor real").
Construir um kernel de enforcement de verdade é engenharia de sistemas
(syscall interception, sandboxing, eBPF/seccomp em Linux) — uma disciplina
completamente diferente do resto do projeto (que é Python de aplicação).

**Dependência direta**: evolução de `core/multi_agent_governance` (V2).
