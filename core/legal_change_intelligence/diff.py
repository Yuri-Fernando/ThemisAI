"""Diff estrutural entre duas versões de uma norma — por dispositivo, não por linha.

Comparar por `unit_id` (art-20.par-1...) em vez de diff de texto corrido é o
que permite dizer "o § 1º do Art. 20 mudou" em vez de "a linha 1.254 mudou" —
e o que mantém o resultado estável quando um dispositivo novo é inserido no
meio (um diff de linhas veria tudo abaixo como deslocado).
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher

from shared.schemas import LegalChangeType, LegalUnit, LegalUnitChange

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def comparable_text(text: str) -> str:
    """Normalização para comparação: caixa, espaços e pontuação final não
    contam como alteração material."""
    return " ".join(_TOKEN_RE.findall(text.lower()))


def textual_change_score(before: str | None, after: str | None) -> float:
    """0.0 = idêntico, 1.0 = totalmente diferente (ou dispositivo novo/removido).

    `1 - ratio` do `SequenceMatcher` sobre tokens (não caracteres): trocar
    "30 dias" por "15 dias" pesa 1 token, não 2 caracteres. É uma medida
    LEXICAL, deliberadamente — materialidade jurídica é avaliada à parte pelos
    sinais determinísticos (`signals.py`), não por esta distância.
    """
    if not before and not after:
        return 0.0
    if not before or not after:
        return 1.0
    a, b = _TOKEN_RE.findall(before.lower()), _TOKEN_RE.findall(after.lower())
    return round(1.0 - SequenceMatcher(None, a, b, autojunk=False).ratio(), 4)


def structural_diff(before: list[LegalUnit], after: list[LegalUnit]) -> list[LegalUnitChange]:
    """Classifica cada dispositivo em added/removed/modified/revoked/annotation_only.

    Dispositivos inalterados não aparecem na saída. A ordem segue o texto
    atual, com removidos intercalados na posição em que estavam.
    """
    before_by_id = {u.unit_id: u for u in before}
    after_by_id = {u.unit_id: u for u in after}
    changes: list[LegalUnitChange] = []

    def emit(unit: LegalUnit, change_type: LegalChangeType, old: LegalUnit | None, new: LegalUnit | None) -> None:
        old_text = (old.text or None) if old else None
        new_text = (new.text or None) if new else None
        new_acts = [a for a in (new.amended_by if new else []) if not old or a not in old.amended_by]
        changes.append(
            LegalUnitChange(
                unit_id=unit.unit_id,
                article=unit.article,
                unit_type=unit.unit_type,
                change_type=change_type,
                before=old_text,
                after=new_text,
                textual_change_score=0.0 if change_type == LegalChangeType.ANNOTATION_ONLY else textual_change_score(old_text, new_text),
                amended_by=new_acts,
            )
        )

    # Ordem do texto atual; cada removido entra logo após o último vizinho
    # anterior (na versão antiga) que continua existindo.
    removed_after: dict[str | None, list[str]] = {}
    anchor: str | None = None
    for unit in before:
        if unit.unit_id in after_by_id:
            anchor = unit.unit_id
        else:
            removed_after.setdefault(anchor, []).append(unit.unit_id)
    ordered_ids: list[str] = list(removed_after.get(None, []))
    for unit in after:
        ordered_ids.append(unit.unit_id)
        ordered_ids.extend(removed_after.get(unit.unit_id, []))

    seen: set[str] = set()
    for uid in ordered_ids:
        if uid in seen:
            continue
        seen.add(uid)
        old, new = before_by_id.get(uid), after_by_id.get(uid)
        if old is None and new is not None:
            emit(new, LegalChangeType.REVOKED if new.revoked else LegalChangeType.ADDED, None, new)
        elif new is None and old is not None:
            emit(old, LegalChangeType.REMOVED, old, None)
        elif old is not None and new is not None:
            if new.revoked and not old.revoked:
                emit(new, LegalChangeType.REVOKED, old, new)
            elif comparable_text(old.text) != comparable_text(new.text) or old.vetoed != new.vetoed:
                emit(new, LegalChangeType.MODIFIED, old, new)
            elif set(new.amended_by) - set(old.amended_by):
                emit(new, LegalChangeType.ANNOTATION_ONLY, old, new)
    return changes
