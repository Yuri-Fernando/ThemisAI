"""Testes do Formal Verification — verificador exaustivo genérico +
verificação real de uma propriedade de agent_tribunal (V2), sem mock."""
from __future__ import annotations

from core.formal_verification.checker import verify_invariant
from core.formal_verification.tribunal_properties import verify_tribunal_deny_precedence
from shared.schemas import VerificationResult


def test_verify_invariant_holds_for_true_property():
    result = verify_invariant("todos pares", range(0, 20, 2), lambda n: n % 2 == 0)
    assert isinstance(result, VerificationResult)
    assert result.holds is True
    assert result.total_cases_checked == 10
    assert result.counterexample is None


def test_verify_invariant_finds_counterexample():
    result = verify_invariant("todos positivos", [1, 2, 3, -4, 5], lambda n: n > 0)
    assert result.holds is False
    assert result.counterexample is not None
    assert result.total_cases_checked == 4  # para na primeira falha (o -4, 4º elemento)


def test_verify_invariant_empty_domain_holds_vacuously():
    result = verify_invariant("vazio", [], lambda n: False)
    assert result.holds is True
    assert result.total_cases_checked == 0


def test_verify_invariant_custom_describe_fn():
    result = verify_invariant(
        "descricao customizada", [{"x": 1}, {"x": -1}], lambda d: d["x"] > 0, describe_fn=lambda d: f"x={d['x']}"
    )
    assert result.holds is False
    assert "x=-1" in result.summary


def test_tribunal_deny_precedence_holds_exhaustively():
    # Verificação REAL contra core.agent_tribunal.adjudicate (V2) -- não é
    # uma propriedade sintética isolada, é uma invariante de segurança real
    # do módulo. max_decisions=2 já é rápido o bastante para o suite normal.
    result = verify_tribunal_deny_precedence(max_decisions=2)
    assert result.holds is True
    assert result.total_cases_checked == 16 + 16**2  # 272 combinações
    assert result.counterexample is None


def test_tribunal_deny_precedence_three_decisions_still_holds():
    result = verify_tribunal_deny_precedence(max_decisions=3)
    assert result.holds is True
    assert result.total_cases_checked == 16 + 16**2 + 16**3
