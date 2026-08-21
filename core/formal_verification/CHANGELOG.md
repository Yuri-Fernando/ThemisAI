# Changelog — Formal Verification

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Este módulo segue SemVer independente (`core/formal_verification/`).

## [0.1.0] - 2026-08-21

### Added

- Extração real do item "Formal Verification Layer (TLA+/Alloy/Coq)" do V3
  (ver `docs/architecture/v3-frontier-research.md`), honestamente reescopada
  para o que é possível sem um solver SAT/SMT: **model checking por
  enumeração exaustiva de espaço de estados finito**.
- `checker.py`: `verify_invariant(property_name, domain, check_fn,
  describe_fn=None) -> VerificationResult` — verificador genérico.
- `tribunal_properties.py`: `verify_tribunal_deny_precedence(max_decisions=3)`
  — verificação REAL, não sintética: prova exaustivamente que
  `agent_tribunal.adjudicate()` (V2) sempre escolhe `DENY` quando presente
  na entrada, sobre TODAS as 4.368 combinações possíveis de até 3
  `PolicyDecision` na grade completa de 4 status x 4 níveis de risco.
- Contratos novos em `shared/schemas.py` (`Counterexample`,
  `VerificationResult`).
- Suíte de testes pytest (`tests/test_checker.py`, 6 testes): propriedade
  verdadeira se sustenta; contraexemplo real encontrado; domínio vazio;
  `describe_fn` customizado; verificação exaustiva real de 2 e 3 decisões
  concorrentes contra `agent_tribunal.adjudicate()`.

### Notes

- **Escopo honesto**: isto NÃO é uma prova simbólica (TLA+/Alloy/Coq
  cobririam espaços de estados infinitos via lógica de predicados) — é
  enumeração de força bruta sobre um domínio FINITO. Funciona perfeitamente
  aqui porque o domínio de `(PolicyDecisionStatus, RiskLevel)` é pequeno e
  fechado; não escalaria para propriedades sobre domínios contínuos ou
  combinatorialmente explosivos.
