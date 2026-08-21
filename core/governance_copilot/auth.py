"""Governance Copilot — autenticação por API key (V5, item 3).

**Escopo honesto**: autenticação simples de API key via header, não
OAuth2/JWT completo — suficiente para bloquear acesso não autorizado num
deploy de portfólio/demonstração, não para um ambiente multiusuário com
diferentes níveis de permissão por chamador (isso seria um projeto de
autenticação próprio, fora de escopo aqui).

**Retrocompatível por padrão**: se a env var `THEMIS_API_KEY` não estiver
definida, a autenticação fica DESABILITADA (todo request passa) — o mesmo
comportamento do V1/V2 (uso local, sem credenciais). Só quando o operador
define `THEMIS_API_KEY` no ambiente é que o endpoint passa a exigir o header
`X-API-Key` com o valor correspondente. Isso preserva `docker compose up`
local funcionando sem configuração extra, e dá o botão real de "exigir
autenticação" para quando o serviço for exposto publicamente.
"""
from __future__ import annotations

import os

from fastapi import Header, HTTPException

ENV_VAR_API_KEY = "THEMIS_API_KEY"


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Dependency do FastAPI: valida `X-API-Key` contra `THEMIS_API_KEY`.

    Não faz nada (autenticação desabilitada) se `THEMIS_API_KEY` não estiver
    definida no ambiente. Levanta `HTTPException(401)` se estiver definida e
    o header `X-API-Key` não bater.
    """
    expected = os.environ.get(ENV_VAR_API_KEY)
    if not expected:
        return  # autenticação desabilitada (uso local/dev, comportamento V1/V2)

    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="X-API-Key ausente ou inválida.")
