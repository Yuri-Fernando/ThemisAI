# NAMING — De "AthenaGov AI" a "Themis AI"

Registro da discussão e decisão de renomear o projeto, para ficar
documentado como parte do processo (não só o resultado). Ver também
[WORKLOG.md](WORKLOG.md) (2026-08-21) para o contexto cronológico dessa
sessão.

## Contexto

O projeto nasceu com o nome **AthenaGov AI** (`docs/origin/rascunho.md`,
brainstorm original, preservado intacto). Na época do nome original, o
escopo concebido era o V1: um núcleo de compliance LGPD (PII, política,
RIPD). "Athena" — deusa grega da sabedoria e estratégia — fazia sentido
para uma ferramenta que ajuda a pensar estrategicamente sobre risco
regulatório.

Depois de V1 e V2 completos (10 + 19 capacidades) e da extração real de 8
itens de V3/V4 (Onda 5), o projeto virou uma **plataforma de governança de
IA abrangente**: compliance LGPD, fairness/equidade, red-teaming de
segurança, privacidade diferencial, governança federada, verificação
formal, e mais. O nome "AthenaGov" (sabedoria + governo) não comunicava mais
o centro de gravidade real do projeto, que é **governança e justiça
algorítmica**, não só estratégia.

## Pedido do usuário

> "e cria um nome que reflita a todas essas capacidades"

Seguido de confirmação de que era para renomear o projeto inteiro (não só
apelidar um subconjunto de módulos).

## Opções consideradas

Apresentadas via pergunta direta ao usuário, com recomendação e trade-offs
explícitos:

| Opção | Racional | Trade-off |
|---|---|---|
| **Themis AI** (escolhida) | Têmis é a deusa grega da lei, da ordem e da justiça divina — mantém a mesma linha mitológica grega de "Athena" (sabedoria/estratégia), mas migra o significado para governança/justiça, que é exatamente o que o projeto virou. Curto, pronunciável, fácil de virar domínio/pacote (`themis-ai`). | Menos "óbvio" para quem não conhece a mitologia grega — exige uma linha explicando a origem (este documento existe por isso). |
| Aegis Governance | Aegis = escudo protetor (também mitologia grega, ligado a Athena/Zeus). Comunica proteção/defesa — encaixaria bem com `audit_logs`, `blockchain_audit_layer`, `red_team_lab`, `incident_response`. | Lê mais como "plataforma de segurança" do que "plataforma de compliance/governança" — sub-representa `fairness_audit`, `constitutional_ai`, `regulatory_rag`, que são o núcleo real do projeto. |
| Nenhum dos dois / outras opções | Oferecido como terceira via, caso nenhuma das duas conversasse com a visão do usuário. | Não escolhido — o usuário confirmou "Themis AI" na primeira rodada. |

## Decisão

**Themis AI.** Critérios que pesaram:
1. Continuidade simbólica com o nome original (linha mitológica grega
   preservada, não uma ruptura de identidade).
2. Precisão semântica: "governança" e "justiça algorítmica" (fairness,
   constitutional AI, verificação formal, red-team) descrevem melhor o que
   o projeto faz hoje do que "segurança" isoladamente.
3. Simplicidade de marca: nome curto, sem hífen/abreviação forçada.

## Execução

Aplicado via find-replace controlado em 28 arquivos (`README.md`,
`CHANGELOG.md`, `ROADMAP.md`, `WORKLOG.md`, docstrings de módulos,
`shared/schemas.py`, arquivos `.yaml` de configuração declarativa) —
"AthenaGov AI" → "Themis AI", "AthenaGov" → "Themis". **Exceções
deliberadas**: `docs/origin/rascunho.md` e `rascunho.md` (raiz) foram
mantidos **verbatim**, porque são o registro histórico do brainstorm
original sob o nome antigo — reescrever a história para "corrigir" o nome
retroativamente destruiria o valor do registro.

Nenhum identificador técnico foi afetado por este rename: o projeto nunca
teve um nome de pacote Python nem um caminho de import literal `athenagov`
(todo código usa `core.<modulo>`), então a mudança de marca não quebrou
nenhuma importação, teste, ou contrato de API. O ambiente virtual local
(`C:/Users/Yuri_/.venvs/athenagov-ai`) manteve o nome antigo por ser só um
caminho de infraestrutura de desenvolvimento, sem significado de marca —
renomeá-lo não traz benefício e teria custo de recriar o venv.

## Registro para o encerramento do projeto

Quando o projeto for formalmente encerrado/publicado, esta seção deve ser
revisitada para confirmar que o nome final (Themis AI) segue fazendo
sentido, e que nenhuma menção residual a "AthenaGov" ficou em lugar
user-facing (README, título de release, descrição de repositório no
GitHub/GitLab) — a checagem técnica (`grep -r AthenaGov`, excluindo os dois
`rascunho.md`) deve retornar vazio antes do tag `v1.0.0`/`v2.0.0`/`v3.0.0`.
