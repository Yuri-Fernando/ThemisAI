"""Isolamento de teste para os armazenamentos de estado do processo da API
(`RIPDStore`, `OversightQueue`) — sem isto, rodar a suíte gravaria RIPDs e
itens de revisão humana de teste no caminho de produção real
(`core/governance_copilot/data/`, `core/human_oversight/data/`), poluindo
dados que deveriam refletir uso real, não execução de `pytest`.
"""
from __future__ import annotations

import pytest

from core.governance_copilot import api
from core.governance_copilot.ripd_store import RIPDStore
from core.human_oversight.queue import OversightQueue


@pytest.fixture(autouse=True)
def _isolate_process_state(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Substitui os armazenamentos de módulo (`api._ripd_store`,
    `api._oversight_queue`) por instâncias apontando para `tmp_path`, só
    para a duração de cada teste — nunca toca os arquivos de produção reais.
    """
    monkeypatch.setattr(api, "_ripd_store", RIPDStore(storage_path=tmp_path / "ripd_reports.json"))
    monkeypatch.setattr(api, "_oversight_queue", OversightQueue(storage_path=tmp_path / "oversight_queue.json"))
