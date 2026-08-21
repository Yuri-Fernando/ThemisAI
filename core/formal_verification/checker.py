"""Formal Verification — extração REAL e honesta do item "Formal Verification
Layer (TLA+/Alloy/Coq)" do V3.

**O que isto é**: verificação de invariante por enumeração exaustiva de um
espaço de estados FINITO (model checking por força bruta) — para todo
`caso` no domínio finito informado, `check_fn(caso)` precisa ser verdadeiro;
se algum caso falhar, o contraexemplo é retornado. Isso é uma técnica de
verificação formal real e estabelecida (bounded model checking), só que sem
um SAT/SMT solver por trás — funciona perfeitamente quando o espaço de
estados é finito e pequeno o bastante para enumerar (nosso caso: número
finito de combinações de `PolicyDecisionStatus`/`RiskLevel`).

**O que isto NÃO é**: uma prova simbólica em TLA+/Alloy/Coq, que verificaria
espaços de estados infinitos via lógica de predicados. Se o domínio não
puder ser enumerado (contínuo, ou finito mas astronomicamente grande),
`verify_invariant` simplesmente não é a ferramenta certa — essa é a honestidade
de escopo documentada em `CHANGELOG.md` e em `docs/architecture/v3-frontier-research.md`.
"""
from __future__ import annotations

from typing import Any, Callable, Iterable

from shared.schemas import Counterexample, VerificationResult


def verify_invariant(
    property_name: str,
    domain: Iterable[Any],
    check_fn: Callable[[Any], bool],
    describe_fn: Callable[[Any], str] | None = None,
) -> VerificationResult:
    """Verifica `check_fn(caso) == True` para TODO `caso` em `domain`.

    Args:
        property_name: nome legível da propriedade sendo verificada.
        domain: iterável FINITO de casos a testar (o "espaço de estados").
            Precisa ser finito — este verificador não termina (nem faz
            sentido) sobre um domínio infinito.
        check_fn: função que recebe um caso e retorna `True` se a invariante
            se sustenta para aquele caso.
        describe_fn: opcional, formata um caso em texto legível para o
            contraexemplo (default: `repr(caso)`).

    Returns:
        `VerificationResult.holds = True` se `check_fn` retornou `True` para
        TODOS os casos; caso contrário `False`, com o PRIMEIRO contraexemplo
        encontrado (não necessariamente o "menor" — enumeração para na
        primeira falha, não busca o contraexemplo mínimo).
    """
    describe_fn = describe_fn or repr
    total = 0
    for case in domain:
        total += 1
        if not check_fn(case):
            counterexample = Counterexample(
                inputs={"case": describe_fn(case)},
                description=f"Caso {total} viola a propriedade '{property_name}'.",
            )
            return VerificationResult(
                property_name=property_name,
                total_cases_checked=total,
                holds=False,
                counterexample=counterexample,
                summary=(
                    f"Propriedade '{property_name}' VIOLADA após verificar {total} caso(s). "
                    f"Contraexemplo: {describe_fn(case)}"
                ),
            )

    return VerificationResult(
        property_name=property_name,
        total_cases_checked=total,
        holds=True,
        counterexample=None,
        summary=f"Propriedade '{property_name}' se sustenta em TODOS os {total} caso(s) do espaço de estados enumerado.",
    )
