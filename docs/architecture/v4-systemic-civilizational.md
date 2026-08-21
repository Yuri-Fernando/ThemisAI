# V4 — Systemic / Civilizational: documentação de visão (sem código)

As 4 capacidades do V4 são deliberadamente **aspiracionais** — o próprio
`ROADMAP.md` as classifica como "documentação de visão", não trabalho de
engenharia planejável em sprints. Este documento existe para que elas não
sejam esquecidas nem confundidas com escopo codificável — são o horizonte
que justifica por que o projeto foi desenhado do jeito que foi (motor 100%
local e determinístico, contratos compartilhados únicos, auditoria
verificável), mesmo que essas 4 nunca virem código neste projeto específico.

---

## 1. Meta-Governance Layer

**Visão**: uma camada que governa os próprios sistemas de governança — se o
Themis AI (ou qualquer conjunto de ferramentas de governança de IA
similares) começasse a ser adotado por múltiplas organizações, quem
audita se a implementação de cada uma está correta? Governança de
governanças, recursivamente.

**Por que V4, não V3**: não é um problema técnico resolvível por uma
organização isolada — pressupõe um ecossistema de múltiplos adotantes já
maduro, algo que só faz sentido perguntar depois que ferramentas como o
próprio Themis AI já estiverem em uso real e testado por terceiros.

**Ligação com o que já existe**: `federated_governance` (V2) já entrega o
primitivo técnico mais próximo disso — agregação entre "nós" sem centralizar
dado bruto — mas numa escala organizacional (filiais da mesma empresa), não
inter-organizacional.

---

## 2. AGI & Civilization Risk Governance

**Visão**: extensão dos princípios de `constitutional_ai`/`agent_tribunal`
(V2) para sistemas de capacidade muito além do que qualquer módulo deste
projeto avalia hoje — cenários onde o "risco" não é mais
"vazamento de PII" ou "decisão discriminatória", mas risco sistêmico de
escala civilizacional.

**Por que V4**: o próprio conceito de "risco de nível AGI" é objeto de
debate ativo na comunidade de segurança de IA, sem consenso metodológico
estabelecido — não há um `RiskLevel.CRITICAL` bem definido para esse
domínio ainda, ao contrário do `RiskLevel` do LGPD (V1), que tem base legal
concreta (Art. 5º/20º) para se ancorar.

---

## 3. Regulatory Simulation Sandbox

**Visão**: uma evolução de `regulatory_sandbox` (V2, que simula um cenário
de tratamento de dados contra o `policy_engine` atual) para simular
**mudanças na própria regulação** — "o que aconteceria com o ecossistema de
IA brasileiro se o Art. 20 da LGPD fosse emendado desta forma?" — nível de
política pública, não de conformidade de um projeto individual.

**Por que V4**: `regulatory_sandbox` (V2) responde "e se eu mudasse minha
base legal?"; isto responderia "e se a própria lei mudasse?" — precisa de
modelagem de todo um ecossistema de agentes regulados, não de um único
sistema de IA.

**Ligação com o que já existe**: `regulatory_knowledge_graph` (V2) já
modela as relações entre artigos da LGPD — pré-requisito estrutural para
simular o efeito em cascata de uma mudança num artigo sobre os demais.

---

## 4. AI Diplomacy & International Governance

**Visão**: harmonização entre regimes regulatórios de IA de diferentes
países/blocos (LGPD, GDPR, AI Act europeu, etc.) — um "tradutor" de
requisitos entre jurisdições, e simulação de como decisões de governança
tomadas numa jurisdição afetam operações em outra.

**Por que V4**: o corpus regulatório deste projeto (`regulatory_rag`, V1) é
explicitamente só LGPD, com disclaimer de que é paráfrase ilustrativa, não
texto oficial — expandir para múltiplas jurisdições reais exigiria validação
jurídica humana especializada em cada uma delas antes de qualquer linha de
código, o mesmo tipo de risco já documentado como fora de escopo em
`regulatory_auto_update/CHANGELOG.md` (V2) para uma única jurisdição.

---

## Nota de convenção

Nenhuma dessas 4 capacidades ganha ADR numerado em `docs/decisions/` — ADRs
são para decisões de arquitetura de algo que está sendo construído. Este
documento é o registro correto para elas: visão preservada, sem fingir que
existe uma decisão de design a ser tomada agora.
