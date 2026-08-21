"""Synthetic Data — gerador determinístico (seedável) de dados sintéticos
tipo-PII para testar `pii_detection`, `fairness_audit` e outros módulos sem
usar dado pessoal real. Nenhuma dependência externa (`Faker` não é
dependência do projeto) — nomes vêm de um pool pequeno e explicitamente
fictício; o CPF usa o algoritmo REAL de dígito verificador (módulo 11) só
para os dígitos serem estruturalmente válidos (e por isso reconhecíveis pelo
`pii_detection`), nunca correspondendo a uma pessoa real.

Todo registro gerado tem `synthetic=True` fixo no schema — não há como
confundir com PII real por engano.
"""
from __future__ import annotations

import random

from shared.schemas import SyntheticPersonRecord

_FIRST_NAMES = ["Ana", "Bruno", "Carla", "Daniel", "Elisa", "Fábio", "Gabriela", "Hugo", "Isabela", "João"]
_LAST_NAMES = ["Silva", "Souza", "Oliveira", "Pereira", "Costa", "Rodrigues", "Almeida", "Nascimento", "Lima", "Araújo"]
_EMAIL_DOMAINS = ["exemplo-sintetico.test", "dados-ficticios.test", "synthetic-mail.test"]


def _cpf_check_digit(digits: str) -> str:
    weights = range(len(digits) + 1, 1, -1)
    total = sum(int(d) * w for d, w in zip(digits, weights))
    remainder = (total * 10) % 11
    return "0" if remainder == 10 else str(remainder)


def generate_cpf(rng: random.Random | None = None) -> str:
    """Gera um CPF sintético com dígitos verificadores estruturalmente
    válidos (algoritmo módulo 11 real) — não corresponde a nenhuma pessoa
    real; é só um número que passa na mesma validação que `pii_detection`
    usa para reconhecer um CPF real.
    """
    rng = rng or random
    base = "".join(str(rng.randint(0, 9)) for _ in range(9))
    d1 = _cpf_check_digit(base)
    d2 = _cpf_check_digit(base + d1)
    digits = base + d1 + d2
    return f"{digits[0:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:11]}"


def generate_person_record(seed: int | None = None) -> SyntheticPersonRecord:
    """Gera um registro sintético de pessoa (nome, CPF, e-mail, telefone).

    `seed` torna a geração reprodutível (mesmo `seed` -> mesmo registro) —
    útil para testes determinísticos.
    """
    rng = random.Random(seed)
    first = rng.choice(_FIRST_NAMES)
    last = rng.choice(_LAST_NAMES)
    name = f"{first} {last}"
    cpf = generate_cpf(rng)
    email = f"{first.lower()}.{last.lower()}{rng.randint(1, 999)}@{rng.choice(_EMAIL_DOMAINS)}"
    ddd = rng.choice([11, 21, 31, 41, 51, 61])
    phone = f"({ddd}) 9{rng.randint(1000,9999)}-{rng.randint(1000,9999)}"

    return SyntheticPersonRecord(name=name, cpf=cpf, email=email, phone=phone)


def generate_dataset(n: int, seed: int | None = None) -> list[SyntheticPersonRecord]:
    """Gera `n` registros sintéticos determinísticos (mesmo `seed` -> mesmo
    dataset, útil para testes reprodutíveis de `pii_detection`/`fairness_audit`
    sem precisar de dado pessoal real)."""
    if n < 0:
        raise ValueError("n precisa ser >= 0.")
    base_rng = random.Random(seed)
    return [generate_person_record(seed=base_rng.randint(0, 2**31)) for _ in range(n)]
