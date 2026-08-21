"""AI Constitution Compiler — extração REAL do item "AI Constitution
Compiler" do V3.

**O que isto é**: análise estática sobre uma lista de artigos no MESMO
formato de `constitutional_ai/constitution.yaml` (`id`, `principle`,
`description`, `forbidden_when.context`, `severity`), detectando 4 classes
reais de conflito ANTES de qualquer contexto ser avaliado em runtime:

1. **`duplicate_condition`**: dois artigos com condição idêntica — um deles
   é redundante (ou um erro de cópia/cola do autor da constituição).
   Bloqueante.
2. **`overlapping_condition_different_severity`**: duas condições
   COMPATÍVEIS que compartilham ao menos uma chave de contexto (existe um
   contexto real que satisfaz ambas, e as duas condições falam do mesmo
   sinal operacional) mas com severidades diferentes — ambíguo: qual
   severidade vale quando os dois artigos disparam juntos?
   `constitutional_ai.check_constitution` (V2) simplesmente retorna as duas
   violações (não escolhe), então isso não quebra em runtime, mas é um sinal
   real de autoria descuidada. Bloqueante.
3. **`vacuous_overlap_different_severity`**: mesma situação do item 2, mas
   as duas condições NÃO compartilham nenhuma chave de contexto — são
   compatíveis só "por vacuidade" (nenhuma chave em comum para contradizer).
   Sinal bem mais fraco (ver nota abaixo sobre o achado real que motivou
   separar isto do item 2). Informativo, não bloqueante.
4. **`subsumption`**: a condição de um artigo é um subconjunto estrito da
   condição de outro — o mais específico SEMPRE dispara junto com o mais
   genérico. Não é necessariamente um erro, mas é informação estrutural real
   sobre a constituição (ex.: um artigo "todo dado sensível" e outro "dado
   sensível de saúde" sempre disparam juntos para dado de saúde).
   Informativo, não bloqueante.

**Histórico (V5, item 2 do plano de melhorias)**: a primeira versão deste
módulo (0.1.0) não distinguia os itens 2 e 3 — qualquer par de condições sem
contradição direta virava `overlapping_condition_different_severity`
bloqueante. Rodado contra a constituição real de produção (6 artigos),
isso gerou **11 conflitos**, quase todos por vacuidade (nenhum par de
artigos reais compartilha exatamente as mesmas chaves de contexto). O tipo
`vacuous_overlap_different_severity` foi introduzido para separar sinal
fraco de sinal forte — ver `CHANGELOG.md` para o antes/depois exato.

**O que isto NÃO é**: um solver de satisfatibilidade lógica geral (SAT/SMT)
capaz de reconhecer conflitos com negações, disjunções, ou expressões
booleanas arbitrárias — as condições de `constitutional_ai` são só
conjunções de igualdades (`context[chave] == valor`), então comparação
direta de dicionários já cobre 100% do espaço de conflitos possível nesse
formato restrito. Um DSL mais expressivo exigiria um solver de verdade.
"""
from __future__ import annotations

from itertools import combinations
from typing import Any

from shared.schemas import ConstitutionCompileResult, ConstitutionConflict


def _condition_items(article: dict[str, Any]) -> frozenset:
    condition = article.get("forbidden_when", {}).get("context", {}) or {}
    return frozenset(condition.items())


def _compatible(items_a: frozenset, items_b: frozenset) -> bool:
    """Duas condições são compatíveis se, para toda chave presente em
    ambas, o valor exigido é o mesmo (ou seja, existe um contexto que
    satisfaz as duas simultaneamente)."""
    dict_b = dict(items_b)
    for key, value in items_a:
        if key in dict_b and dict_b[key] != value:
            return False
    return True


def compile_constitution(articles: list[dict[str, Any]]) -> ConstitutionCompileResult:
    """Compila (valida + analisa estaticamente) uma lista de artigos no
    formato de `constitutional_ai/constitution.yaml`.

    Args:
        articles: lista de dicts, cada um com `id`, `principle`,
            `forbidden_when.context` (dict de igualdades) e `severity`.

    Returns:
        `ConstitutionCompileResult` com todos os conflitos encontrados
        (pode haver zero) e `valid = (nenhum conflito de tipo
        duplicate_condition ou overlapping_condition_different_severity)` —
        `subsumption` sozinho não invalida a constituição, é só informativo.
    """
    conflicts: list[ConstitutionConflict] = []

    for a, b in combinations(articles, 2):
        items_a, items_b = _condition_items(a), _condition_items(b)
        if not items_a or not items_b:
            continue  # condição vazia não conflita com nada (não dispara sozinha)

        if items_a == items_b:
            conflicts.append(
                ConstitutionConflict(
                    article_a=a["id"],
                    article_b=b["id"],
                    conflict_type="duplicate_condition",
                    explanation=f"Artigos '{a['id']}' e '{b['id']}' têm exatamente a mesma condição — um dos dois é redundante.",
                )
            )
            continue

        dict_a, dict_b = dict(items_a), dict(items_b)
        if dict_a.items() <= dict_b.items() or dict_b.items() <= dict_a.items():
            more_specific, more_general = (a, b) if len(dict_a) > len(dict_b) else (b, a)
            conflicts.append(
                ConstitutionConflict(
                    article_a=a["id"],
                    article_b=b["id"],
                    conflict_type="subsumption",
                    explanation=(
                        f"Condição de '{more_specific['id']}' é um caso especial de '{more_general['id']}' — "
                        f"sempre que '{more_specific['id']}' dispara, '{more_general['id']}' também dispara."
                    ),
                )
            )
            continue

        if _compatible(items_a, items_b) and a.get("severity") != b.get("severity"):
            shared_keys = {k for k, _ in items_a} & {k for k, _ in items_b}
            if shared_keys:
                # Overlap real: as duas condições compartilham pelo menos uma
                # chave de contexto E concordam no valor dela -- sinal forte
                # de que tratam do mesmo sinal operacional com severidades
                # divergentes. Bloqueante.
                conflicts.append(
                    ConstitutionConflict(
                        article_a=a["id"],
                        article_b=b["id"],
                        conflict_type="overlapping_condition_different_severity",
                        explanation=(
                            f"Condições de '{a['id']}' (severidade={a.get('severity')}) e '{b['id']}' "
                            f"(severidade={b.get('severity')}) compartilham a(s) chave(s) "
                            f"{sorted(shared_keys)} e podem disparar simultaneamente com severidades diferentes."
                        ),
                    )
                )
            else:
                # Compatibilidade por VACUIDADE (nenhuma chave em comum para
                # contradizer) -- tecnicamente as duas condições PODEM ser
                # satisfeitas ao mesmo tempo, mas não têm nada de contexto
                # em comum, então é um sinal muito mais fraco. Reportado como
                # informativo, não bloqueante -- ver CHANGELOG.md (V5, item 2)
                # e o achado real na constituição de produção que motivou
                # esta distinção (11 falsos-positivos antes deste fix).
                conflicts.append(
                    ConstitutionConflict(
                        article_a=a["id"],
                        article_b=b["id"],
                        conflict_type="vacuous_overlap_different_severity",
                        explanation=(
                            f"Condições de '{a['id']}' (severidade={a.get('severity')}) e '{b['id']}' "
                            f"(severidade={b.get('severity')}) não compartilham nenhuma chave de contexto "
                            f"— compatíveis só por vacuidade, sinal fraco, não bloqueante."
                        ),
                    )
                )

    blocking = [c for c in conflicts if c.conflict_type not in ("subsumption", "vacuous_overlap_different_severity")]
    valid = len(blocking) == 0

    if not conflicts:
        summary = f"{len(articles)} artigo(s) compilados, nenhum conflito detectado."
    else:
        summary = (
            f"{len(articles)} artigo(s) compilados, {len(conflicts)} conflito(s) detectado(s) "
            f"({len(blocking)} bloqueante(s), {len(conflicts) - len(blocking)} informativo(s))."
        )

    return ConstitutionCompileResult(
        article_count=len(articles),
        conflicts=conflicts,
        valid=valid,
        summary=summary,
    )
