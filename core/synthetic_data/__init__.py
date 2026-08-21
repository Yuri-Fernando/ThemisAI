"""Synthetic Data — geração determinística de dados sintéticos (nunca PII real) para testes (V2)."""
from __future__ import annotations

from core.synthetic_data.generator import generate_cpf, generate_dataset, generate_person_record

__all__ = ["generate_cpf", "generate_dataset", "generate_person_record"]
