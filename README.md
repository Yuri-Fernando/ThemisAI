# 🏛️ Themis AI

### Python · FastAPI · Streamlit · LGPD · AI Governance · Privacy Engineering

## Status

🟡 **Em desenvolvimento — núcleo completo e testado localmente (477 testes),
deploy público ainda pendente.**

## Descrição / Contexto

**Pesquisa / P&D — Projeto em desenvolvimento contínuo.**

Plataforma de governança de IA e privacidade sob a LGPD: detecta dados
pessoais/sensíveis, avalia risco regulatório, gera automaticamente o RIPD
(Relatório de Impacto à Proteção de Dados) e audita fairness, segurança de
prompt e privacidade de sistemas de decisão automatizada — motor 100% local
e determinístico, sem chamada a LLM em nenhum ponto de decisão.

Nasceu de uma vaga pública de P&D em Governança de Dados e IA. **Não é
software de nenhuma empresa específica** — é uma plataforma construída
inteiramente como peça de portfólio, para demonstrar competências reais de
engenharia de governança de IA (compliance, fairness, segurança,
privacidade diferencial, verificação formal).

> **Sobre o nome:** o projeto começou como "AthenaGov AI" e foi renomeado
> para **Themis AI** quando o escopo já cobria compliance LGPD, fairness,
> segurança, privacidade diferencial e verificação formal — Têmis, deusa
> grega da lei, da ordem e da justiça, comunica melhor "governança e
> justiça algorítmica" do que o nome original, mantendo a mesma linha
> mitológica grega (Athena → Têmis). Discussão completa (opções
> consideradas, critérios de decisão, execução) em [NAMING.md](NAMING.md).

---

## 🎯 Objetivo

- Automatizar o mapeamento de risco LGPD de projetos de IA, hoje feito
  manualmente;
- Detectar dado pessoal/sensível em texto e documentos de forma
  determinística e auditável;
- Gerar a RIPD automaticamente, compondo os módulos de política, PII,
  segurança e score de confiança;
- Auditar equidade (fairness), segurança de prompt e privacidade de
  sistemas de decisão automatizada com testes estatísticos reais;
- Provar, com testes reais (não simulados), que cada capacidade funciona —
  inclusive quando o teste revela um bug de verdade.

---

## 🔬 Linha de Pesquisa / Desenvolvimento

- Compliance LGPD automatizado (classificação de dado, base legal, RIPD);
- Fairness/equidade algorítmica (disparate impact, Paradoxo de Simpson,
  significância estatística);
- Segurança de prompt e red-teaming (prompt injection, jailbreak,
  exfiltração, ofuscação);
- Privacidade diferencial (mecanismo de Laplace, composição avançada);
- Verificação formal (model checking por enumeração exaustiva);
- Governança multi-agente e federada;
- Grafos de conhecimento regulatório (LGPD).

---

## 🏗️ Arquitetura

```text
Entrada (texto/documento de projeto de IA)
   ↓
PII Detection · Prompt Security · Sensitive Data Scanner
   ↓
Policy Engine (regras declarativas LGPD) · Constitutional AI
   ↓
Trust Score · Explainability · Fairness Audit · Causal Fairness
   ↓
RIPD Engine (compõe os módulos acima em um relatório único)
   ↓
Governance Copilot (API FastAPI: auth, autorização real, métricas, auditoria)
   ↓
Dashboard (Streamlit) / integração externa

Entrada (modelo de decisão automatizada + dados de teste)
   ↓
Adversarial ML  (core/adversarial_ml/)
   ├─ ataques: FGSM · PGD · model extraction · data poisoning
   ├─ defesas: adversarial training · feature squeezing · detecção
   └─ robustez: curva ε×acurácia · min. perturbation budget · risco
   ↓
MODEL SECURITY REPORT  (+ seção de LLM security via prompt_security/red_team_lab)
   ↓
gate de MLOps (ex.: production robustness gate do Argus)
```

Cada camada é um módulo independente (`core/<modulo>/`), com contrato
Pydantic compartilhado em `shared/schemas.py` — nenhum módulo reimplementa
lógica de outro.

---

## ⚙️ Funcionamento

1. O texto/descrição de um projeto de IA entra no sistema;
2. É escaneado por PII/dado sensível e por segurança de prompt;
3. O motor de política (declarativo, YAML) avalia a base legal e as
   categorias de dado envolvidas contra as regras da LGPD;
4. O score de confiança agrega os sinais anteriores, com explicação em
   linguagem natural;
5. O RIPD Engine compõe tudo isso — mais o contexto regulatório recuperado
   via busca semântica — num relatório final;
6. A API (Governance Copilot) expõe cada etapa via REST, com autenticação
   opcional, autorização real por agente, métricas e trilha de auditoria
   com hash-chain verificável.

---

## 🧠 Inteligência / Modelagem

- **Regras declarativas** (YAML) para política e constituição de IA —
  auditável e reproduzível, sem variação entre execuções;
- **NLP determinístico**: regex categorizado por técnica de ataque +
  heurística de nome próprio + spaCy opcional para NER;
- **Busca semântica local**: `sentence-transformers` + ChromaDB, sem API
  paga;
- **Grafos** (`networkx`): relações reais entre artigos da LGPD, extraídas
  do próprio corpus (nenhuma aresta inventada);
- **Estatística real**: teste qui-quadrado de significância, teste
  Kolmogorov-Smirnov para drift, mecanismo de Laplace para privacidade
  diferencial;
- **Verificação formal**: model checking por enumeração exaustiva de
  espaço de estados finito;
- **Deliberadamente sem LLM no motor de decisão** — decisão de arquitetura
  documentada: um sistema que decide risco regulatório precisa ser
  auditável e reproduzível, o que um LLM não garante.

---

## 🧪 Desenvolvimento Experimental

```text
Conceito (núcleo de compliance LGPD)
   ↓
Protótipo (10 módulos, motor local determinístico)
   ↓
Experimentação (expansão para 19 capacidades de AI Governance)
   ↓
Validação (extração real de capacidades de fronteira — verificação formal,
           causal fairness, red-teaming — sempre honestamente reescopadas)
   ↓
Implementação (API real com autenticação, autorização, observabilidade)
   ↓
Evolução (débito técnico priorizado e fechado com achados reais)
```

Três achados reais que aconteceram durante o desenvolvimento (não
plantados): um harness de red-teaming mediu a taxa de detecção real do
scanner de segurança de prompt e encontrou — depois corrigiu — dois bugs de
regex reais; o Paradoxo de Simpson apareceu no primeiro teste do módulo de
fairness causal, exatamente como a literatura prevê; e um compilador de
constituição de IA encontrou 11 conflitos de severidade na constituição
real do projeto, expondo uma limitação do próprio modelo de análise.

---

## 🛠️ Tecnologias

**Linguagens:** Python

**Frameworks:** FastAPI · Streamlit · Pydantic

**IA / ML / Dados:** sentence-transformers · ChromaDB · spaCy · scipy ·
numpy · networkx

**Infraestrutura:** Docker · Docker Compose · GitHub Actions (CI)

**Testes:** pytest · pytest-cov

---

## 📊 Resultados

- **477 testes automatizados** passando, zero mock em módulo de produção;
- **96% de cobertura de linha**;
- **41 capacidades de governança de IA** implementadas com código real e
  testes, cada uma com seu próprio changelog documentando decisões e
  limitações;
- Taxa de detecção de ataques de prompt medida e melhorada com dados reais
  (50% → 67%) via harness de red-team próprio;
- Grafo de conhecimento regulatório construído a partir de menções
  textuais reais no corpus (nenhuma relação fabricada).

---

## 🚀 Aplicações

- Times de compliance/jurídico avaliando risco LGPD de projetos de IA;
- Times de ML precisando auditar fairness/equidade de modelos de decisão;
- Equipes de segurança testando resistência de sistemas de IA a prompt
  injection;
- Automação de RIPD para portfólios de projetos de IA em empresas;
- Aplicações futuras: integração com pipelines de MLOps existentes.

---

## 🔭 Visão de Longo Prazo

```text
Projeto de portfólio
   ↓
Plataforma local de governança de IA
   ↓
API pública documentada
   ↓
Integração com ferramentas de MLOps/compliance existentes
   ↓
Produto de governança de IA para empresas reguladas
```

---

## 🗺️ Roadmap

**Fase 1 — Foundation** ✅ Concluída
Núcleo de compliance LGPD: detecção de PII, motor de política, segurança
de prompt, score de confiança, auditoria com hash-chain, RAG regulatório,
gerador de RIPD, API e dashboard.

**Fase 2 — AI Governance** ✅ Concluída
19 capacidades adicionais: fairness audit, blockchain audit layer,
constitutional AI, grafo de conhecimento regulatório, red-team lab,
privacidade diferencial, governança federada, entre outras.

**Fase 3 — Extração real de capacidades de fronteira** ✅ Concluída
Núcleo genuinamente codificável de verificação formal, causal fairness,
detecção de ataques multi-turno, enforcement de política em runtime e mais
— sempre honestamente reescopado, nunca fingindo a coisa inteira.

**Fase 4 — Débito técnico e deploy-readiness** ✅ Concluída
Autenticação, CORS, autorização real, métricas, correção de bugs reais
encontrados por red-teaming e análise estática.

**Fase 5 — Publicação** 🔄 Em andamento
Deploy público (Docker pronto, build ainda não validado em produção), tag
de release, revisão jurídica do corpus regulatório.

**Fase 6 — Adversarial ML / AI Security** ✅ Núcleo implementado
`core/adversarial_ml/` — motor de segurança de modelos: ataques adversariais
reais (FGSM, PGD, model extraction, data poisoning), defesas (adversarial
training, feature squeezing, detecção estatística) e o **MODEL SECURITY
REPORT** consolidado (`run_security_assessment`). Escopo vindo de um
brainstorm de consolidação de portfólio — Themis passa a ser a plataforma
central de **AI Governance + AI Security + Adversarial ML**, e os demais
projetos (VisionGuard, Credit Score, RL-PID-AGV, Churn) são os casos de uso
que consomem este motor. 15 testes. Ver
[`core/adversarial_ml/CHANGELOG.md`](core/adversarial_ml/CHANGELOG.md) e
`notebooks/adversarial_ml_dev_log.ipynb`.

---

## 🔮 Próximos Passos

- Deploy público da API + dashboard;
- Validar `docker compose up --build` em ambiente limpo;
- Configurar autenticação/CORS antes de expor publicamente;
- Fechar os itens de débito técnico restantes que exigem infraestrutura
  externa (ancoragem de hash, OCR);
- Revisão jurídica profissional do corpus regulatório antes de qualquer
  uso além de portfólio/demonstração.

---

## Status

🟡 **Em desenvolvimento — projeto experimental e de pesquisa aplicada em
desenvolvimento contínuo.**

O código já cobre o roadmap técnico completo (Fases 1 a 4). O que falta
para considerar o projeto encerrado é a publicação (deploy real, tag de
release) e a revisão jurídica do corpus — por isso permanece em
desenvolvimento, não concluído.

---

## Contexto / Observações

- Código 100% público, sem dados/credenciais reais — motor 100% local,
  sem custo de API;
- O corpus regulatório incluído é uma paráfrase ilustrativa da LGPD
  (explicitamente identificada como tal em cada arquivo), não texto oficial
  — não substitui consulta à lei nem assessoria jurídica.

---

## 🔗 Projetos que consomem o Themis

O Themis é a **plataforma central de AI Governance + AI Security + Adversarial
ML** de um portfólio. O motor de `core/adversarial_ml/`
(`run_security_assessment` → `ModelSecurityReport`) é consumido pelos casos
de uso abaixo, e o relatório alimenta o *production robustness gate* do
**Argus** (`ml-platform/adversarial-evaluation/`).

| Projeto | O que ataca/testa | Técnica |
|---|---|---|
| **VisionGuard** | classificador ResNet de visão | FGSM · PGD · adversarial patch · adversarial training |
| **Credit Score (AWS)** | modelo de risco de crédito (tabular) | evasão de perturbação mínima sob *feature constraints* · model extraction |
| **Self-Evolving RL-PID-AGV** | política de controle sob observação corrompida | ataques de estado (ruído/bias/dropout/latência/spoofing) · robust RL |
| **Churn Intelligence** | modelo de churn (tabular, negócio) | robustness testing (perturbação · missing-data · distribution shift · OOD) |
| **Argus** | qualquer modelo antes de produção | gate de MLOps: bloqueia promoção se `overall_risk` / `robust_accuracy` fora do limite |

---

## 🤖 Autor

**Yuri Fernando Dubbern**

Engenharia Elétrica · Ciência da Computação · Inteligência Artificial ·
Data Science · Automação · Sistemas Embarcados · Pesquisa e Desenvolvimento

[LinkedIn](https://www.linkedin.com/in/yuridubbern) · [GitHub](https://github.com/Yuri-Fernando) · [Lattes](http://lattes.cnpq.br/7151392692642166) · [Linktree](https://linktr.ee/yuri.f.dubbern)
