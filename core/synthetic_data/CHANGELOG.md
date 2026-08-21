# Changelog — Synthetic Data

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Este módulo segue SemVer independente (`core/synthetic_data/`).

## [0.1.0] - 2026-08-20

### Added

- `generator.py`:
  - `generate_cpf(rng=None) -> str` — CPF sintético com dígito verificador
    módulo 11 REAL (estruturalmente válido, mas nunca corresponde a pessoa
    real).
  - `generate_person_record(seed=None) -> SyntheticPersonRecord` — nome
    (pool fictício), CPF, e-mail (domínio `.test`), telefone. Determinístico
    por `seed`.
  - `generate_dataset(n, seed=None) -> list[SyntheticPersonRecord]`.
- Contrato novo em `shared/schemas.py` (`SyntheticPersonRecord`, campo
  `synthetic: bool = True` fixo — impossível confundir com PII real por
  engano).
- Suíte de testes pytest (`tests/test_generator.py`, 11 testes), incluindo
  **round-trip real contra `pii_detection.detect()`**: o CPF sintético é
  reconhecido pelo motor real com confiança >= 0.9 (prova de que o dígito
  verificador é estruturalmente válido, não só "parece" um CPF); dataset
  inteiro tem CPF e e-mail detectados por texto composto real.

### Notes

- Sem dependência de `Faker` (não é dependência do projeto) — pool de nomes
  pequeno e deliberadamente fictício, e-mails sempre em domínio `.test`
  (reservado pela IANA para uso não-produtivo, nunca resolve de verdade).
- Uso pretendido: alimentar `fairness_audit`/`pii_detection`/testes de outros
  módulos sem precisar de dado pessoal real em nenhum ponto do
  desenvolvimento.
