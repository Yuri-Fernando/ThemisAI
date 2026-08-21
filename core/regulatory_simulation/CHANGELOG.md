# Changelog — Regulatory Simulation Sandbox

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Este módulo segue SemVer independente (`core/regulatory_simulation/`).

## [0.1.0] - 2026-08-21

### Added

- Extração real do item "Regulatory Simulation Sandbox" do V4, honestamente
  reescopada: simula o impacto em cascata de uma mudança OPERACIONAL
  hipotética associada a um artigo (não uma mudança na lei em si).
- `impact.py`: `simulate_regulatory_change(article_number, context_override,
  test_scenarios, graph=None) -> RegulatoryChangeImpact` — composição real
  de `regulatory_knowledge_graph.find_related()` (identifica artigos
  relacionados) + `regulatory_sandbox.compare_scenarios()` (mede o impacto
  real no trust score de cada cenário de teste antes/depois).
- Contrato novo em `shared/schemas.py` (`RegulatoryChangeImpact`).
- Suíte de testes pytest (`tests/test_impact.py`, 7 testes): mudança que
  força revisão humana melhora cenário de biometria de verdade; artigos
  relacionados vêm do grafo real (`38 -> 11, 20`, mesmo achado de
  `regulatory_knowledge_graph/tests`); override sem efeito real gera zero
  mudança de score; múltiplos cenários avaliados independentemente;
  validação de entrada; artigo desconhecido; resumo.

### Notes

- **Escopo honesto**: não simula mudança na LEI em si (exigiria modelar um
  ecossistema regulatório inteiro, ver `docs/architecture/v4-systemic-civilizational.md`,
  item "Regulatory Simulation Sandbox" completo) — simula o efeito de um
  `context_override` operacional hipotético sobre cenários de teste reais.
