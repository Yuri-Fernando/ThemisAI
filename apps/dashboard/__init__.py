"""Dashboard — módulo V1 do Themis AI.

App Streamlit que consome o Governance Copilot (`core/governance_copilot`,
API FastAPI) via HTTP, através de `GovernanceCopilotClient`. Ver
`apps/dashboard/app.py` (UI) e `apps/dashboard/client.py` (cliente HTTP).
"""
from apps.dashboard.client import GovernanceCopilotClient

__all__ = ["GovernanceCopilotClient"]

__version__ = "0.1.0"
