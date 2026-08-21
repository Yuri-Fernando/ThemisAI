"""Testes do Synthetic Data — inclusive round-trip real contra
pii_detection.detect() (prova de que o CPF sintético é estruturalmente
válido, não só "parece" um CPF)."""
from __future__ import annotations

import random

import pytest

from core.pii_detection.detector import detect
from core.synthetic_data.generator import generate_cpf, generate_dataset, generate_person_record
from shared.schemas import SyntheticPersonRecord


def test_generate_cpf_has_valid_format():
    cpf = generate_cpf(random.Random(42))
    assert len(cpf) == 14  # XXX.XXX.XXX-XX
    assert cpf[3] == "." and cpf[7] == "." and cpf[11] == "-"


def test_generate_cpf_is_recognized_as_valid_by_pii_detection():
    # Round-trip real: o CPF sintético precisa passar pela MESMA validação de
    # dígito verificador que o motor real de pii_detection usa.
    cpf = generate_cpf(random.Random(123))
    result = detect(f"CPF de teste: {cpf}")
    cpf_findings = [f for f in result.findings if f.entity_type == "CPF"]
    assert len(cpf_findings) == 1
    assert cpf_findings[0].confidence >= 0.9  # confiança alta = dígito verificador válido


def test_generate_cpf_deterministic_with_same_rng_seed():
    cpf1 = generate_cpf(random.Random(7))
    cpf2 = generate_cpf(random.Random(7))
    assert cpf1 == cpf2


def test_generate_person_record_deterministic_with_seed():
    r1 = generate_person_record(seed=99)
    r2 = generate_person_record(seed=99)
    assert r1 == r2


def test_generate_person_record_different_seeds_differ():
    r1 = generate_person_record(seed=1)
    r2 = generate_person_record(seed=2)
    assert r1 != r2


def test_generate_person_record_is_marked_synthetic():
    record = generate_person_record(seed=1)
    assert isinstance(record, SyntheticPersonRecord)
    assert record.synthetic is True


def test_generate_person_record_email_domain_is_test_only():
    record = generate_person_record(seed=5)
    assert record.email.endswith(".test")  # nunca um domínio real


def test_generate_dataset_returns_n_records():
    dataset = generate_dataset(10, seed=1)
    assert len(dataset) == 10
    assert all(isinstance(r, SyntheticPersonRecord) for r in dataset)


def test_generate_dataset_deterministic_with_seed():
    d1 = generate_dataset(5, seed=42)
    d2 = generate_dataset(5, seed=42)
    assert [r.cpf for r in d1] == [r.cpf for r in d2]


def test_generate_dataset_negative_n_raises():
    with pytest.raises(ValueError):
        generate_dataset(-1)


def test_generate_dataset_zero_n_returns_empty():
    assert generate_dataset(0) == []


def test_generate_dataset_all_pii_detected_by_real_scanner():
    dataset = generate_dataset(5, seed=10)
    for record in dataset:
        text = f"Nome: {record.name}, CPF: {record.cpf}, e-mail: {record.email}, telefone: {record.phone}"
        result = detect(text)
        entity_types = {f.entity_type for f in result.findings}
        assert "CPF" in entity_types
        assert "EMAIL" in entity_types
