# Changelog — Runtime Policy Enforcement

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Este módulo segue SemVer independente (`core/runtime_policy_enforcement/`).

## [0.1.0] - 2026-08-21

### Added

- Extração real do item "Runtime Policy Enforcement Kernel" do V3,
  honestamente reescopada para nível de aplicação (não kernel/eBPF).
- `enforcement.py`: `@enforce(agent_id, action, registry_path=None)` —
  decorator que chama `multi_agent_governance.authorize()` (V2) ANTES do
  corpo da função decorada rodar, levantando `EnforcementError` (subclasse
  de `PermissionError`) sem executar nada se não autorizado.
- Contrato novo em `shared/schemas.py` (`EnforcementDenied`).
- Suíte de testes pytest (`tests/test_enforcement.py`, 7 testes): chamada
  autorizada roda normalmente; chamada não autorizada levanta erro E prova
  (via efeito colateral observável) que o corpo NUNCA executa; captura
  genérica por `PermissionError` funciona; contexto do erro preservado;
  `functools.wraps` preserva metadados da função original; args/kwargs
  passam through; registro customizado.

### Notes

- **Diferença real em relação a `multi_agent_governance.authorize()`
  sozinho**: `authorize()` é consultivo (quem chama pode ignorar o
  resultado); `@enforce` torna a checagem estruturalmente obrigatória —
  impossível a função decorada rodar sem passar pela autorização.
- **Escopo honesto**: NÃO é um "kernel" — não intercepta syscalls nem roda
  em nível de SO (sem eBPF/seccomp/sandbox). Código no mesmo processo ainda
  poderia chamar a função original não-decorada por outro caminho. Ver
  `docs/architecture/v3-frontier-research.md` para o que um kernel de
  verdade exigiria.
