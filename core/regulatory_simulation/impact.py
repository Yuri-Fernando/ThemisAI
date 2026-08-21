"""Regulatory Simulation Sandbox — extração REAL do item "Regulatory
Simulation Sandbox" do V4, honestamente reescopada: em vez de simular
mudanças na LEI em si (o que exigiria modelar todo um ecossistema
regulatório — fora de escopo, ver `docs/architecture/v4-systemic-civilizational.md`),
este módulo simula o IMPACTO EM CASCATA de uma mudança operacional
hipotética associada a um artigo específico sobre uma bateria de cenários de
teste — composição real de dois módulos V2 já existentes:

1. `regulatory_knowledge_graph.find_related()` — identifica quais outros
   artigos são diretamente conectados ao artigo que "mudou" (contexto: o que
   mais pode ser afetado).
2. `regulatory_sandbox.compare_scenarios()` — para cada cenário de teste,
   compara o resultado ANTES/DEPOIS de aplicar `context_override` (a mudança
   hipotética, expressa como sinais de `context` que passam a valer sempre),
   usando os motores reais `policy_engine`/`trust_score`.

Exemplo de uso real: "se o Art. 20 passasse a exigir `human_review=True`
sempre, o que muda no trust score dos meus cenários de teste de decisão
automatizada?"
"""
from __future__ import annotations

import networkx as nx

from core.regulatory_knowledge_graph.graph import build_graph, find_related
from core.regulatory_sandbox.sandbox import compare_scenarios
from shared.schemas import RegulatoryChangeImpact, SandboxScenario


def simulate_regulatory_change(
    article_number: str,
    context_override: dict,
    test_scenarios: list[SandboxScenario],
    graph: nx.DiGraph | None = None,
) -> RegulatoryChangeImpact:
    """Simula o impacto de uma mudança regulatória hipotética associada ao
    Art. `article_number` sobre uma bateria de `test_scenarios`.

    Args:
        article_number: número do artigo "alterado" (ex. `"20"`), usado só
            para localizar artigos relacionados no grafo de conhecimento —
            não precisa ter relação direta com `context_override`.
        context_override: sinais de `context` que a mudança hipotética
            passaria a impor em TODOS os cenários (ex.
            `{"human_review": True}`).
        test_scenarios: cenários base a testar antes/depois da mudança.
        graph: grafo já construído (opcional, evita reconstruir se o
            chamador já tem um — ver `regulatory_knowledge_graph.build_graph`).

    Levanta `ValueError` se `test_scenarios` estiver vazio.
    """
    if not test_scenarios:
        raise ValueError("simulate_regulatory_change requer ao menos um cenário em `test_scenarios`.")

    graph = graph if graph is not None else build_graph()
    related = find_related(graph, article_number, max_hops=1)
    directly_affected = [r["article"] or r["id"] for r in related]

    comparisons = []
    for scenario in test_scenarios:
        merged_context = {**(scenario.context or {}), **context_override}
        scenario_after = scenario.model_copy(update={
            "name": f"{scenario.name} (após mudança)",
            "context": merged_context,
        })
        comparison = compare_scenarios(scenario, scenario_after)
        comparisons.append(comparison)

    changed = [c for c in comparisons if c.score_delta != 0.0]

    summary = (
        f"Mudança hipotética no Art. {article_number}º (context_override={context_override}): "
        f"{len(directly_affected)} artigo(s) diretamente relacionado(s) no grafo regulatório "
        f"({', '.join(directly_affected) if directly_affected else 'nenhum'}). "
        f"{len(changed)} de {len(test_scenarios)} cenário(s) de teste tiveram o trust score alterado."
    )

    return RegulatoryChangeImpact(
        changed_article=article_number,
        directly_affected_articles=directly_affected,
        scenarios_evaluated=len(test_scenarios),
        scenarios_with_score_change=len(changed),
        comparisons=comparisons,
        summary=summary,
    )
