# V5 — Plano de Melhorias e Débito Técnico

Consolidação de melhoria/débito técnico encontrado durante o desenvolvimento
do V1, V2, extração real de V3/V4 (Onda 5) e da própria V5. **10 dos 15
itens originais foram resolvidos em 2026-08-21** (código real + testes,
mesmo rigor do resto do projeto) — ver detalhes em cada `CHANGELOG.md` de
módulo. Este arquivo encolheu, como pretendido desde a v1 dele.

Formato por item: **o que é**, **por que importa**, **onde foi resolvido /
por que continua aberto**.

---

## Resolvidos em 2026-08-21 (V5)

| # | Item | Onde ver o fix |
|---|---|---|
| 1 | Gaps de detecção do `prompt_security` em português (RT-01, RT-06) | `core/prompt_security/CHANGELOG.md` `[0.1.1]` — bug de regex real corrigido, taxa de detecção 50%→67% |
| 2 | Ruído no `constitution_compiler` por compatibilidade vacuidade | `core/constitution_compiler/CHANGELOG.md` `[0.2.0]` — 11 falsos-positivos → 2 conflitos reais + 9 informativos |
| 3 | `governance_copilot` sem autenticação/CORS | `core/governance_copilot/CHANGELOG.md` `[0.2.0]` — `X-API-Key` opcional + CORS configurável |
| 4 | Fila de revisão humana não alimentada automaticamente | `core/governance_copilot/CHANGELOG.md` `[0.2.0]` — auto-enqueue em `POST /ripd/generate` |
| 6 | `traceability` sem propagação de correlação | `core/governance_copilot/CHANGELOG.md` `[0.2.0]` — `trace_id` real + `GET /audit/trace/{id}` |
| 7 | `@enforce` não aplicado a nenhum endpoint real | `core/governance_copilot/CHANGELOG.md` `[0.2.0]` — todo endpoint decorado |
| 8 | `ai_observability` sem coletor real | `core/governance_copilot/CHANGELOG.md` `[0.2.0]` — `GET /metrics` real |
| 11 | `differential_privacy`: composição de orçamento simples | `core/differential_privacy/CHANGELOG.md` `[0.2.0]` — `advanced_composition_epsilon()` real (Dwork et al. 2010) |
| 12 | `fairness_audit`: sem teste de significância estatística | `core/fairness_audit/CHANGELOG.md` `[0.2.0]` — `chi_square_significance()` real (scipy) |
| 14 | `governance_copilot`: RIPDs não persistidos/consultáveis | `core/governance_copilot/CHANGELOG.md` `[0.2.0]` — `ripd_store.py` + endpoints |

## Parcialmente resolvido

### 5. `incident_response`/`self_healing_governance` sem disparo periódico
**Resolvido parcialmente**: `POST /api/v1/health-check/run` (`governance_copilot`
`[0.2.0]`) permite rodar `check_and_heal()` sob demanda via HTTP. **Continua
em aberto**: nenhum scheduler/cron real está embutido — um disparador
externo (cron do SO, GitHub Actions agendado, etc.) precisa chamar esse
endpoint periodicamente para virar automação de verdade. Configurar esse
disparador é operação de deploy, não código — ver `PARA_VOCE_FAZER.md`.

---

## Ainda em aberto

### 9. `blockchain_audit_layer` sem ancoragem externa
**O que**: os `merkle_root` de cada checkpoint nunca são publicados fora do
controle de quem escreve o log.
**Por que continua aberto**: exige escolher e integrar um mecanismo de
ancoragem real (timestamping notarial, repositório git separado, blockchain
pública) — decisão de infraestrutura externa, não coberta nesta rodada.
**Onde**: `core/blockchain_audit_layer/CHANGELOG.md`.

### 10. `sensitive_data_scanner` sem OCR
**O que**: PDFs escaneados (imagem, sem texto extraível) são detectados mas
não processados.
**Por que continua aberto**: exigiria integrar Tesseract (binário do SO, não
só um pacote pip) ou um serviço de OCR externo — dependência de
infraestrutura que este ambiente de desenvolvimento não garante ter
disponível.
**Onde**: `core/sensitive_data_scanner/CHANGELOG.md`.

### 13. `cognitive_attack_detection`: só captura fragmentação de payload reconhecível
**O que**: não detecta manipulação psicológica multi-turno sem nenhum
fragmento de padrão conhecido.
**Por que continua aberto — deliberadamente**: exigiria um classificador
treinado, decisão consciente de quebrar o determinismo 100% do projeto
(mesma discussão de "Neuro-Symbolic Governance" em
`docs/architecture/v3-frontier-research.md`). Não é dívida técnica no
sentido usual — é um limite de escopo intencional.
**Onde**: `core/cognitive_attack_detection/CHANGELOG.md`.

### 15. `regulatory_auto_update`: sem fonte externa (decisão deliberada, não bug)
**O que**: não busca o texto oficial da LGPD em nenhuma fonte externa.
**Por que continua assim**: exigiria validação jurídica humana antes de
qualquer automação — risco real de erro regulatório grave se malfeito. Fica
aqui só para registro, não é "esquecimento".

---

## Como usar este documento

Escolher itens por prioridade, abrir uma "Onda" nova (mesmo padrão de
V1/V2/Onda 5/V5 — código real + testes + notebook), e mover o item concluído
daqui para o `CHANGELOG.md` raiz. Os itens 9, 10 e 13 exigem uma decisão de
infraestrutura/escopo explícita antes de codificar (não são só "escrever
mais código") — vale discutir antes de abrir a próxima onda.
