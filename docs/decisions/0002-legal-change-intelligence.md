# ADR 0002 — Legal Change Intelligence (V7) como motor determinístico

- **Status:** aceita
- **Data:** 2026-09-23
- **Origem:** brainstorm de consolidação "upgrade 2" (vaga de Engenheiro(a) de
  IA em escritório de advocacia) + pedido explícito do dono do projeto de
  implementar a função de análise de alteração normativa desenhada ali.

## Contexto

O ROADMAP fixava V6 como teto, com a regra "V7 só a partir de um novo
documento de estratégia explícito". O documento existe: propõe o Themis como
**cérebro regulatório** de uma vertical jurídica do Conecta AI (SaaS), com
uma função central `analyze_legal_change(previous, current, client_context)`
que detecta alteração de norma e estima impacto em clientes de um escritório.

## Decisão

1. Novo módulo `core/legal_change_intelligence/`, contratos em
   `shared/schemas.py` (aditivo, `SCHEMA_VERSION` 0.5.0).
2. **Decisão por regra, não por LLM** — mesma linha do resto do Themis.
   `impact_level`/`risk_level`/`requires_human_review` saem de uma tabela de
   regras (R0–R8) com evidência por regra. LLM, se usado, só redige resumo
   a jusante.
3. **Diff por dispositivo** (`art-20.par-1`), não por linha: estável quando
   o legislador intercala dispositivo novo (`I-A`), e é a granularidade em
   que advogado raciocina.
4. **Revisão humana obrigatória vira item real** na `OversightQueue`
   existente — reuso, não reimplementação.
5. **Fixtures JSON compartilhadas** com a implementação TypeScript do Conecta
   AI: duas linguagens (Python aqui, Deno/TS na edge do SaaS), um contrato de
   comportamento só.

## Consequências

- (+) Auditável e reproduzível; mesma entrada → mesma saída (testado).
- (+) Reusa `human_oversight` e o padrão de contratos do projeto.
- (−) Sinais lexicais têm recall limitado (documentado no CHANGELOG do módulo).
- (−) Duas implementações para manter em sincronia — mitigado pelas fixtures
  compartilhadas rodando nas duas suítes.
