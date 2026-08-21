"""Testes do AI Constitution Compiler — análise estática real, inclusive
sobre a constituição real de `core/constitutional_ai/constitution.yaml`."""
from __future__ import annotations

import yaml

from core.constitution_compiler.compiler import compile_constitution
from shared.schemas import ConstitutionCompileResult


def _article(id_, context, severity="medium"):
    return {"id": id_, "principle": "teste", "description": "d", "forbidden_when": {"context": context}, "severity": severity}


def test_no_conflicts_for_disjoint_conditions():
    articles = [_article("A", {"x": True}), _article("B", {"y": True})]
    result = compile_constitution(articles)
    assert isinstance(result, ConstitutionCompileResult)
    assert result.conflicts == []
    assert result.valid is True


def test_duplicate_condition_detected():
    articles = [_article("A", {"x": True, "y": False}), _article("B", {"x": True, "y": False})]
    result = compile_constitution(articles)
    assert len(result.conflicts) == 1
    assert result.conflicts[0].conflict_type == "duplicate_condition"
    assert result.valid is False


def test_subsumption_detected_and_not_blocking():
    articles = [_article("A", {"x": True}), _article("B", {"x": True, "y": False})]
    result = compile_constitution(articles)
    assert len(result.conflicts) == 1
    assert result.conflicts[0].conflict_type == "subsumption"
    assert result.valid is True  # subsumption sozinho não bloqueia


def test_overlapping_condition_different_severity_detected():
    # Compartilham x=True (compatíveis), mas nenhuma é subconjunto da outra
    # (y vs z são chaves diferentes) -- overlap real, não duplicata nem subsunção.
    articles = [
        _article("A", {"x": True, "y": True}, severity="critical"),
        _article("B", {"x": True, "z": True}, severity="low"),
    ]
    result = compile_constitution(articles)
    assert len(result.conflicts) == 1
    assert result.conflicts[0].conflict_type == "overlapping_condition_different_severity"
    assert result.valid is False


def test_vacuous_overlap_different_severity_is_informative_not_blocking():
    # Nenhuma chave em comum -- compatíveis só por vacuidade.
    articles = [
        _article("A", {"x": True}, severity="critical"),
        _article("B", {"y": True}, severity="low"),
    ]
    result = compile_constitution(articles)
    assert len(result.conflicts) == 1
    assert result.conflicts[0].conflict_type == "vacuous_overlap_different_severity"
    assert result.valid is True  # não bloqueia, diferente do overlap real


def test_incompatible_conditions_no_conflict():
    articles = [_article("A", {"x": True}), _article("B", {"x": False})]
    result = compile_constitution(articles)
    assert result.conflicts == []


def test_empty_condition_never_conflicts():
    articles = [_article("A", {}), _article("B", {"x": True})]
    result = compile_constitution(articles)
    assert result.conflicts == []


def test_single_article_no_conflicts():
    result = compile_constitution([_article("A", {"x": True})])
    assert result.conflicts == []
    assert result.article_count == 1


def test_empty_constitution():
    result = compile_constitution([])
    assert result.article_count == 0
    assert result.valid is True


def test_summary_mentions_counts():
    articles = [_article("A", {"x": True}, "high"), _article("B", {"x": True}, "low")]
    result = compile_constitution(articles)
    assert "1 conflito" in result.summary or "conflito(s)" in result.summary


def test_real_production_constitution_yaml():
    # Análise estática real da constituição de produção de constitutional_ai (V2).
    from core.constitutional_ai.engine import _DEFAULT_CONSTITUTION_PATH

    with open(_DEFAULT_CONSTITUTION_PATH, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    articles = data["constitution"]

    result = compile_constitution(articles)
    assert result.article_count == 6

    # Achado real (V5, pós-fix do item 2): só 2 conflitos são REALMENTE
    # bloqueantes -- os pares que de fato compartilham uma chave de contexto.
    real_overlaps = {
        (c.article_a, c.article_b)
        for c in result.conflicts
        if c.conflict_type == "overlapping_condition_different_severity"
    }
    assert real_overlaps == {("CONST-01", "CONST-03"), ("CONST-05", "CONST-06")}

    # Os demais pares (sem chave em comum) viram informativo, não bloqueante.
    vacuous = [c for c in result.conflicts if c.conflict_type == "vacuous_overlap_different_severity"]
    assert len(vacuous) == 9

    blocking = [c for c in result.conflicts if c.conflict_type not in ("subsumption", "vacuous_overlap_different_severity")]
    assert len(blocking) == 2
    assert result.valid is False  # os 2 overlaps reais ainda bloqueiam
