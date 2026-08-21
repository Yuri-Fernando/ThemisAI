"""Causal Fairness — extração REAL do item "Causal AI Governance" do V3.

**O que isto é**: `fairness_audit` (V2) mede correlação bruta (taxa de
seleção por grupo do atributo protegido) — mas uma disparidade agregada pode
sumir, inverter, ou ser causada inteiramente por uma terceira variável
(o confundidor). Este módulo estratifica a auditoria de equidade por um
`confound_key` e compara o veredito agregado contra o veredito
dentro-de-cada-estrato — a técnica real e estabelecida chamada **Paradoxo de
Simpson**: quando a direção/magnitude da disparidade muda ao condicionar
numa terceira variável.

Reusa 100% o motor real de `fairness_audit.audit_fairness()` — não
reimplementa nenhuma estatística, só chama a função uma vez por estrato mais
uma vez no agregado, e compara.

**O que isto NÃO é**: inferência causal completa (grafos causais/DAG,
matching, variáveis instrumentais) — isso exigiria especificar o modelo
causal do domínio, que é conhecimento de negócio, não só estatística. O que
este módulo entrega é o PRIMEIRO sintoma real que motivaria uma investigação
causal mais profunda: "a disparidade observada sobrevive ao controlar por
esta variável, ou desaparece?" — ver `docs/architecture/v3-frontier-research.md`
para a extensão completa (não implementada).
"""
from __future__ import annotations

from typing import Any

from core.fairness_audit.engine import audit_fairness
from shared.schemas import StratifiedFairnessResult, StratumResult


def stratified_fairness_audit(
    records: list[dict[str, Any]],
    outcome_key: str,
    protected_attribute_key: str,
    confound_key: str,
    favorable_outcome: Any = True,
    threshold: float = 0.8,
) -> StratifiedFairnessResult:
    """Audita equidade agregada E dentro de cada estrato de `confound_key`,
    e detecta se o veredito muda entre os dois (Paradoxo de Simpson).

    Levanta `ValueError` se `records` estiver vazio (mesma validação de
    `audit_fairness`).
    """
    aggregate = audit_fairness(
        records, outcome_key=outcome_key, protected_attribute_key=protected_attribute_key,
        favorable_outcome=favorable_outcome, threshold=threshold,
    )

    strata_values: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        stratum = str(record.get(confound_key))
        strata_values.setdefault(stratum, []).append(record)

    strata_results: list[StratumResult] = []
    for stratum, stratum_records in sorted(strata_values.items()):
        # Estratos com só 1 grupo protegido não têm o que comparar --
        # audit_fairness já trata isso como "justo por vacuidade" (documentado
        # no próprio fairness_audit), então não precisamos filtrar aqui.
        stratum_fairness = audit_fairness(
            stratum_records, outcome_key=outcome_key, protected_attribute_key=protected_attribute_key,
            favorable_outcome=favorable_outcome, threshold=threshold,
        )
        strata_results.append(
            StratumResult(stratum=stratum, sample_size=len(stratum_records), fairness=stratum_fairness)
        )

    # Paradoxo de Simpson: o agregado diz "justo" mas algum estrato diz
    # "injusto" (ou vice-versa) -- a conclusão muda de direção ao condicionar.
    strata_with_comparison = [s for s in strata_results if s.fairness.metrics]
    paradox = any(s.fairness.overall_fair != aggregate.overall_fair for s in strata_with_comparison)

    if paradox:
        summary = (
            f"Paradoxo de Simpson DETECTADO: o veredito agregado ({'justo' if aggregate.overall_fair else 'injusto'}) "
            f"diverge do veredito em pelo menos um estrato de '{confound_key}' — a disparidade observada pode ser "
            f"causada (ou mascarada) por essa variável confundidora, não pelo atributo protegido em si."
        )
    else:
        summary = (
            f"Nenhum Paradoxo de Simpson detectado: o veredito agregado ({'justo' if aggregate.overall_fair else 'injusto'}) "
            f"é consistente com todos os {len(strata_with_comparison)} estrato(s) de '{confound_key}' com comparação possível."
        )

    return StratifiedFairnessResult(
        protected_attribute=protected_attribute_key,
        confound_attribute=confound_key,
        aggregate=aggregate,
        strata=strata_results,
        simpsons_paradox_detected=paradox,
        summary=summary,
    )
