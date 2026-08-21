# ADR 0001 — Escopo do V1 e tratamento das capacidades de fronteira

**Status:** Aceito · **Data:** 2026-08-19

## Contexto

O brainstorm original (`docs/origin/rascunho.md`) expandiu o projeto para 40
capacidades em 18 camadas ("Themis AI"), incluindo itens de pesquisa de
fronteira (Formal Verification com Coq/TLA+, Neuro-Symbolic Governance,
AGI & Civilization Risk Governance). Construir tudo isso como código
funcional em um único ciclo não é viável nem honesto: viraria pastas vazias
com nomes grandiosos, o que enfraquece o projeto numa entrevista técnica.

## Decisão

1. **V1** (10 módulos: Policy Engine, PII Detection, Prompt Security,
   Explainability, Trust Score, Audit Logs, Regulatory RAG, RIPD Engine,
   Governance Copilot, Dashboard) é implementado com engenharia real:
   código + testes automatizados + notebook de dev-log por módulo.
2. Motor de IA 100% local (sentence-transformers + Chroma + spaCy/regex),
   sem dependência de chave de API paga — reprodutibilidade garantida.
3. **V2** segue o mesmo padrão de rigor, em ciclos futuros.
4. **V3/V4** (formal verification, neuro-symbolic, causal AI, meta-governance,
   AGI/civilizational risk) permanecem como **documentação de arquitetura e
   pesquisa** em `docs/architecture/` — não como stub de código. Essas
   capacidades dependem de disciplinas (lógica formal, pesquisa acadêmica)
   fora do que um agente de codificação pode "implementar" de forma genuína;
   quando houver ciclo dedicado a elas, a decisão será revisitada.
5. Nada do escopo original é descartado — está todo mapeado em `ROADMAP.md`.

## Consequências

- O projeto cresce em ondas rastreáveis via `CHANGELOG.md` + `status/*.json`.
- Cada módulo é testável e demonstrável isoladamente (bom para portfólio/entrevista).
- V3/V4 exigem input humano direto (você) quando chegar a vez delas.
