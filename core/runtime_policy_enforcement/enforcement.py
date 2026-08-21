"""Runtime Policy Enforcement — extração REAL do item "Runtime Policy
Enforcement Kernel" do V3, honestamente reescopada para o que é possível em
Python de aplicação.

**O que isto é**: um decorator (`@enforce(agent_id, action)`) que intercepta
DE VERDADE a chamada da função decorada — chama
`multi_agent_governance.authorize()` (V2) ANTES do corpo da função rodar, e
levanta `EnforcementError` sem executar nada do corpo se a ação não for
autorizada. Diferente de `multi_agent_governance.authorize()` sozinho (que é
"consultivo" — quem chama pode ignorar o resultado), este decorator torna a
checagem OBRIGATÓRIA: é estruturalmente impossível a função decorada
executar sem passar pela autorização primeiro.

**O que isto NÃO é** (nome original do V3: "kernel"): não intercepta
syscalls nem roda em nível de sistema operacional (sem eBPF/seccomp/sandbox)
— um código Python mal-intencionado no MESMO processo ainda poderia chamar a
função original não-decorada diretamente, ou importar o módulo de outro
jeito. Enforcement de verdade nesse nível exigiria engenharia de sistemas
fora do escopo deste projeto (aplicação Python) — ver
`docs/architecture/v3-frontier-research.md`. O que este módulo garante é
real dentro do seu escopo honesto: **nenhum código que passe pela API
decorada consegue pular a checagem**.
"""
from __future__ import annotations

import functools
from pathlib import Path
from typing import Any, Callable, TypeVar

from core.multi_agent_governance.registry import authorize

F = TypeVar("F", bound=Callable[..., Any])


class EnforcementError(PermissionError):
    """Levantado quando uma chamada decorada com `@enforce` não é autorizada.

    Subclasse de `PermissionError` (built-in) — captura genérica de
    permissão negada continua funcionando para quem não conhece este tipo
    específico.
    """

    def __init__(self, agent_id: str, action: str, reason: str) -> None:
        self.agent_id = agent_id
        self.action = action
        self.reason = reason
        super().__init__(f"Ação '{action}' negada para o agente '{agent_id}': {reason}")


def enforce(agent_id: str, action: str, registry_path: str | Path | None = None) -> Callable[[F], F]:
    """Decorator: bloqueia a execução da função decorada se `agent_id` não
    estiver autorizado a executar `action` (via `multi_agent_governance.authorize`).

    Exemplo:
        @enforce(agent_id="red_teamer", action="red_team_lab.run_suite")
        def run_attack_suite():
            return run_red_team_suite()

        run_attack_suite()  # roda normalmente, red_teamer tem essa ação
    """

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = authorize(agent_id, action, registry_path)
            if not result.authorized:
                raise EnforcementError(agent_id, action, result.reason)
            return fn(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
