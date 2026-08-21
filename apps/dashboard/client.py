"""Cliente HTTP fino para a API do Governance Copilot (`core/governance_copilot`).

O dashboard NUNCA importa `core/governance_copilot` diretamente — o backend é
construído em paralelo por outro agente e pode nem existir no disco durante o
desenvolvimento deste módulo. Toda a comunicação é feita via HTTP contra o
contrato de API documentado no `docs/decisions/` / prompt do módulo, usando
`httpx`. Os payloads de resposta seguem exatamente os modelos Pydantic de
`shared/schemas.py` (serialização padrão do FastAPI/Pydantic) — por isso
fazemos o parse de volta para esses tipos aqui, dando type-safety ao resto do
dashboard sem redefinir nenhum contrato.

Endpoints cobertos (ver contrato completo no README do módulo):
    GET  /health
    POST /api/v1/pii/detect
    POST /api/v1/prompt-security/scan
    POST /api/v1/policy/evaluate
    POST /api/v1/ripd/generate
    GET  /api/v1/audit/verify
    GET  /api/v1/audit/events
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import httpx

# Garante que `shared` é importável mesmo quando este módulo é executado fora
# do contexto de `python -m pytest` a partir da raiz do repo (ex.: via
# `streamlit run apps/dashboard/app.py`, que não adiciona a raiz ao sys.path).
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from shared.schemas import (  # noqa: E402
    AuditEvent,
    PIIDetectionResult,
    PolicyDecision,
    PromptSecurityResult,
    RIPDReport,
)

DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_TIMEOUT_SECONDS = 15.0
ENV_VAR_BASE_URL = "THEMIS_API_URL"


class GovernanceCopilotError(Exception):
    """Erro genérico ao comunicar com a API do Governance Copilot."""


class GovernanceCopilotConnectionError(GovernanceCopilotError):
    """A API está indisponível: conexão recusada, timeout ou DNS falhou.

    É o caso que a UI precisa tratar com uma mensagem clara em vez de deixar
    o Streamlit quebrar (ex.: backend ainda não subiu / não existe ainda).
    """


class GovernanceCopilotHTTPError(GovernanceCopilotError):
    """A API respondeu, mas com um status HTTP de erro (4xx/5xx)."""

    def __init__(self, status_code: int, detail: str, url: str) -> None:
        self.status_code = status_code
        self.detail = detail
        self.url = url
        super().__init__(f"HTTP {status_code} em {url}: {detail}")


class GovernanceCopilotClient:
    """Cliente HTTP fino para a API do Governance Copilot.

    Parameters
    ----------
    base_url:
        URL base da API. Se omitido, usa a env var `THEMIS_API_URL`; se
        também ausente, usa `DEFAULT_BASE_URL` (http://localhost:8000).
    timeout:
        Timeout (segundos) aplicado a todas as chamadas.
    transport:
        Transporte `httpx` customizado — usado pelos testes para injetar um
        `httpx.MockTransport` e simular a API sem rede real. Nunca usado em
        produção (fica `None`, e o `httpx.Client` usa o transporte padrão).
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        resolved = base_url or os.environ.get(ENV_VAR_BASE_URL) or DEFAULT_BASE_URL
        self.base_url = resolved.rstrip("/")
        self._timeout = timeout
        self._transport = transport

    # -- infraestrutura interna ------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        try:
            with httpx.Client(
                base_url=self.base_url, timeout=self._timeout, transport=self._transport
            ) as client:
                response = client.request(method, path, json=json, params=params)
        except httpx.ConnectError as exc:
            raise GovernanceCopilotConnectionError(
                f"Não foi possível conectar à API do Governance Copilot em "
                f"{self.base_url}. Verifique se o backend está rodando."
            ) from exc
        except httpx.TimeoutException as exc:
            raise GovernanceCopilotConnectionError(
                f"Tempo esgotado ao chamar {url} (timeout={self._timeout}s)."
            ) from exc
        except httpx.HTTPError as exc:
            # Qualquer outro erro de transporte (ex.: erro de rede genérico).
            raise GovernanceCopilotConnectionError(
                f"Falha de comunicação com a API do Governance Copilot em {url}: {exc}"
            ) from exc

        if response.is_error:
            detail = response.text
            try:
                body = response.json()
                detail = body.get("detail", detail) if isinstance(body, dict) else detail
            except ValueError:
                pass
            raise GovernanceCopilotHTTPError(response.status_code, str(detail), url)

        return response.json()

    # -- endpoints ---------------------------------------------------------

    def health(self) -> dict[str, Any]:
        """GET /health -> {"status": "ok"}"""
        return self._request("GET", "/health")

    def detect_pii(self, text: str) -> PIIDetectionResult:
        """POST /api/v1/pii/detect"""
        data = self._request("POST", "/api/v1/pii/detect", json={"text": text})
        return PIIDetectionResult.model_validate(data)

    def scan_prompt_security(self, prompt: str) -> PromptSecurityResult:
        """POST /api/v1/prompt-security/scan"""
        data = self._request(
            "POST", "/api/v1/prompt-security/scan", json={"prompt": prompt}
        )
        return PromptSecurityResult.model_validate(data)

    def evaluate_policy(
        self,
        data_categories: list[str],
        legal_basis: str,
        context: dict[str, Any] | None = None,
    ) -> list[PolicyDecision]:
        """POST /api/v1/policy/evaluate"""
        payload = {
            "data_categories": data_categories,
            "legal_basis": legal_basis,
            "context": context,
        }
        data = self._request("POST", "/api/v1/policy/evaluate", json=payload)
        return [PolicyDecision.model_validate(item) for item in data]

    def generate_ripd(
        self,
        project_name: str,
        project_description: str,
        data_categories: list[str],
        legal_basis: str,
        context: dict[str, Any] | None = None,
    ) -> RIPDReport:
        """POST /api/v1/ripd/generate"""
        payload = {
            "project_name": project_name,
            "project_description": project_description,
            "data_categories": data_categories,
            "legal_basis": legal_basis,
            "context": context,
        }
        data = self._request("POST", "/api/v1/ripd/generate", json=payload)
        return RIPDReport.model_validate(data)

    def verify_audit(self) -> dict[str, Any]:
        """GET /api/v1/audit/verify -> {"valid": bool}"""
        return self._request("GET", "/api/v1/audit/verify")

    def get_audit_events(self, limit: int = 50) -> list[AuditEvent]:
        """GET /api/v1/audit/events?limit=50"""
        data = self._request("GET", "/api/v1/audit/events", params={"limit": limit})
        return [AuditEvent.model_validate(item) for item in data]
