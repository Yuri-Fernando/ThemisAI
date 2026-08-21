"""Testes do Causal Fairness — inclusive um caso clássico real (estilo
Berkeley) de Paradoxo de Simpson construído para o teste."""
from __future__ import annotations

import pytest

from core.causal_fairness.stratified import stratified_fairness_audit
from shared.schemas import StratifiedFairnessResult


def _berkeley_style_dataset():
    """Constrói o exemplo clássico: agregado parece injusto contra 'F', mas
    dentro de cada departamento 'F' tem taxa igual ou maior que 'M'."""
    records = []
    # Depto A: fácil (a maioria admite). M concentra aqui (90 candidatos).
    records += [{"gender": "M", "dept": "A", "admitted": i < 80} for i in range(90)]
    records += [{"gender": "F", "dept": "A", "admitted": i < 9} for i in range(10)]
    # Depto B: difícil (poucos admitem). F concentra aqui (90 candidatos).
    records += [{"gender": "M", "dept": "B", "admitted": i < 1} for i in range(10)]
    records += [{"gender": "F", "dept": "B", "admitted": i < 10} for i in range(90)]
    return records


def test_simpsons_paradox_detected_in_classic_example():
    records = _berkeley_style_dataset()
    result = stratified_fairness_audit(
        records, outcome_key="admitted", protected_attribute_key="gender",
        confound_key="dept", favorable_outcome=True,
    )
    assert isinstance(result, StratifiedFairnessResult)
    # Agregado: M ~81%, F ~19% -- bem abaixo da regra dos 80%, injusto.
    assert result.aggregate.overall_fair is False
    # Mas em cada departamento, F tem taxa igual/maior -- justo.
    for stratum in result.strata:
        assert stratum.fairness.overall_fair is True
    assert result.simpsons_paradox_detected is True
    assert "Paradoxo de Simpson DETECTADO" in result.summary


def test_no_paradox_when_strata_agree_with_aggregate():
    # Disparidade real e consistente em todos os estratos -- sem paradoxo.
    records = (
        [{"gender": "M", "dept": "A", "admitted": True} for _ in range(50)]
        + [{"gender": "F", "dept": "A", "admitted": False} for _ in range(50)]
        + [{"gender": "M", "dept": "B", "admitted": True} for _ in range(50)]
        + [{"gender": "F", "dept": "B", "admitted": False} for _ in range(50)]
    )
    result = stratified_fairness_audit(records, "admitted", "gender", "dept", favorable_outcome=True)
    assert result.aggregate.overall_fair is False
    assert all(s.fairness.overall_fair is False for s in result.strata)
    assert result.simpsons_paradox_detected is False


def test_strata_count_matches_confound_values():
    records = _berkeley_style_dataset()
    result = stratified_fairness_audit(records, "admitted", "gender", "dept")
    strata_names = {s.stratum for s in result.strata}
    assert strata_names == {"A", "B"}


def test_sample_sizes_correct_per_stratum():
    records = _berkeley_style_dataset()
    result = stratified_fairness_audit(records, "admitted", "gender", "dept")
    sizes = {s.stratum: s.sample_size for s in result.strata}
    assert sizes["A"] == 100
    assert sizes["B"] == 100


def test_empty_records_raises():
    with pytest.raises(ValueError):
        stratified_fairness_audit([], "admitted", "gender", "dept")


def test_single_stratum_still_works():
    records = [
        {"gender": "M", "dept": "A", "admitted": True},
        {"gender": "F", "dept": "A", "admitted": False},
    ]
    result = stratified_fairness_audit(records, "admitted", "gender", "dept")
    assert len(result.strata) == 1
    assert result.simpsons_paradox_detected is False  # só 1 estrato, nada pra divergir
