"""Blockchain Audit Layer — checkpoints Merkle sobre a hash-chain do Audit Logs.

Evolução honesta do `core/audit_logs` (ver limitações de segurança já
documentadas em `core/audit_logs/CHANGELOG.md`): a hash-chain do Audit Logs já
detecta adulteração de qualquer evento individual, mas um atacante com acesso
de escrita ao arquivo E capacidade de rodar `verify_chain()` pode recalcular a
cadeia inteira do zero. Este módulo não resolve esse problema sozinho (isso
exigiria ancoragem externa de verdade — publicar o `merkle_root` em algum
lugar fora do controle de quem escreve o log, ex. um repositório git separado,
um serviço de timestamping notarial, ou uma blockchain pública — nenhuma
dessas integrações está implementada nesta versão V2).

O que este módulo entrega de real, sem inventar infraestrutura externa que
não existe:
    1. **Checkpoints Merkle**: agrupa lotes de eventos de auditoria já
       gravados em `core/audit_logs` num Merkle root, encadeado ao checkpoint
       anterior (sua própria hash-chain de checkpoints).
    2. **Provas de inclusão (Merkle proofs)**: para qualquer evento já
       coberto por um checkpoint, gera e verifica uma prova compacta
       (`O(log n)` hashes) de que aquele evento pertence ao Merkle root
       daquele checkpoint — sem precisar reler todos os eventos.
    3. **Verificação da própria cadeia de checkpoints**, no mesmo padrão de
       `AuditLogger.verify_chain()`.

Isso é o pré-requisito técnico real para uma futura ancoragem externa (o
`merkle_root` de cada checkpoint é justamente o dado pequeno e resumido que
se publicaria em algum lugar externo) — mas a publicação externa em si fica
fora de escopo desta versão, documentado aqui, não fingido.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.audit_logs.logger import AuditLogger, default_logger
from shared.schemas import AuditEvent, MerkleCheckpoint, MerkleProof, MerkleProofStep

GENESIS_CHECKPOINT_HASH = "0" * 64
DEFAULT_CHECKPOINT_PATH = Path(__file__).parent / "data" / "checkpoints.jsonl"


# ---------------------------------------------------------------------------
# Árvore de Merkle — construção, raiz e prova de inclusão
# ---------------------------------------------------------------------------

def _hash_pair(left: str, right: str) -> str:
    return hashlib.sha256((left + right).encode("utf-8")).hexdigest()


def merkle_root(leaves: list[str]) -> str:
    """Calcula a raiz de Merkle de uma lista de hashes-folha.

    Convenção para nível ímpar de nós: duplica o último hash (padrão comum,
    ex. Bitcoin) em vez de deixá-lo "órfão" sem par.
    """
    if not leaves:
        return hashlib.sha256(b"").hexdigest()

    level = list(leaves)
    while len(level) > 1:
        next_level = []
        for i in range(0, len(level), 2):
            left = level[i]
            right = level[i + 1] if i + 1 < len(level) else level[i]
            next_level.append(_hash_pair(left, right))
        level = next_level
    return level[0]


def _merkle_proof_path(leaves: list[str], index: int) -> list[MerkleProofStep]:
    """Gera a prova de inclusão (caminho de hashes irmãos) para `leaves[index]`."""
    if index < 0 or index >= len(leaves):
        raise IndexError(f"Índice {index} fora do intervalo de {len(leaves)} folhas.")

    proof: list[MerkleProofStep] = []
    level = list(leaves)
    idx = index
    while len(level) > 1:
        next_level = []
        pair_start = idx - (idx % 2)
        for i in range(0, len(level), 2):
            left = level[i]
            right = level[i + 1] if i + 1 < len(level) else level[i]
            if i == pair_start:
                if idx == i:
                    proof.append(MerkleProofStep(sibling_hash=right, position="right"))
                else:
                    proof.append(MerkleProofStep(sibling_hash=left, position="left"))
            next_level.append(_hash_pair(left, right))
        idx //= 2
        level = next_level
    return proof


def _verify_proof_path(leaf_hash: str, proof_path: list[MerkleProofStep], expected_root: str) -> bool:
    current = leaf_hash
    for step in proof_path:
        if step.position == "right":
            current = _hash_pair(current, step.sibling_hash)
        else:
            current = _hash_pair(step.sibling_hash, current)
    return current == expected_root


# ---------------------------------------------------------------------------
# Persistência da cadeia de checkpoints (hash-chain própria, mesmo padrão de
# core/audit_logs/logger.py)
# ---------------------------------------------------------------------------

def _compute_checkpoint_hash(
    prev_hash: str,
    checkpoint_id: str,
    created_at_iso: str,
    event_range_start: int,
    event_range_end: int,
    root: str,
) -> str:
    raw = f"{prev_hash}{checkpoint_id}{created_at_iso}{event_range_start}{event_range_end}{root}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _read_checkpoint_records(checkpoint_path: Path) -> list[dict[str, Any]]:
    if not checkpoint_path.exists():
        return []
    records = []
    with checkpoint_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def create_checkpoint(
    logger: AuditLogger | None = None,
    checkpoint_path: str | Path | None = None,
) -> MerkleCheckpoint:
    """Cria um novo checkpoint Merkle cobrindo os eventos gravados desde o
    último checkpoint (ou desde o início da cadeia, se for o primeiro).

    Levanta `ValueError` se não houver eventos novos desde o último checkpoint.
    """
    logger = logger or default_logger()
    path = Path(checkpoint_path) if checkpoint_path else DEFAULT_CHECKPOINT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    events = logger.read_events()
    checkpoints = _read_checkpoint_records(path)
    range_start = checkpoints[-1]["event_range_end"] if checkpoints else 0
    range_end = len(events)

    if range_end <= range_start:
        raise ValueError(
            "Nenhum evento novo desde o último checkpoint "
            f"(cadeia de auditoria tem {len(events)} eventos, último checkpoint cobre até o índice {range_start})."
        )

    leaves = [e.hash for e in events[range_start:range_end]]
    root = merkle_root(leaves)
    prev_hash = checkpoints[-1]["checkpoint_hash"] if checkpoints else GENESIS_CHECKPOINT_HASH

    checkpoint_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc)
    created_at_iso = created_at.isoformat()
    checkpoint_hash = _compute_checkpoint_hash(
        prev_hash, checkpoint_id, created_at_iso, range_start, range_end, root
    )

    record = {
        "checkpoint_id": checkpoint_id,
        "created_at": created_at_iso,
        "event_range_start": range_start,
        "event_range_end": range_end,
        "event_count": range_end - range_start,
        "merkle_root": root,
        "prev_checkpoint_hash": prev_hash,
        "checkpoint_hash": checkpoint_hash,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    return MerkleCheckpoint(**record)


def verify_checkpoint_chain(checkpoint_path: str | Path | None = None) -> bool:
    """Relê a cadeia de checkpoints e recalcula os hashes para detectar adulteração."""
    path = Path(checkpoint_path) if checkpoint_path else DEFAULT_CHECKPOINT_PATH
    records = _read_checkpoint_records(path)

    expected_prev = GENESIS_CHECKPOINT_HASH
    for record in records:
        if record["prev_checkpoint_hash"] != expected_prev:
            return False
        recalculated = _compute_checkpoint_hash(
            record["prev_checkpoint_hash"],
            record["checkpoint_id"],
            record["created_at"],
            record["event_range_start"],
            record["event_range_end"],
            record["merkle_root"],
        )
        if recalculated != record["checkpoint_hash"]:
            return False
        expected_prev = record["checkpoint_hash"]

    return True


def get_proof(
    event_hash: str,
    logger: AuditLogger | None = None,
    checkpoint_path: str | Path | None = None,
) -> MerkleProof:
    """Gera e verifica uma prova de inclusão de Merkle para um evento já coberto
    por algum checkpoint.

    Levanta `ValueError` se o evento não estiver coberto por nenhum checkpoint
    existente (ex.: checkpoint ainda não foi criado para ele — rode
    `create_checkpoint()` primeiro).
    """
    logger = logger or default_logger()
    path = Path(checkpoint_path) if checkpoint_path else DEFAULT_CHECKPOINT_PATH

    events = logger.read_events()
    checkpoints = _read_checkpoint_records(path)

    for record in checkpoints:
        start, end = record["event_range_start"], record["event_range_end"]
        slice_events: list[AuditEvent] = events[start:end]
        leaves = [e.hash for e in slice_events]
        try:
            local_index = leaves.index(event_hash)
        except ValueError:
            continue

        proof_path = _merkle_proof_path(leaves, local_index)
        valid = _verify_proof_path(event_hash, proof_path, record["merkle_root"])
        return MerkleProof(
            event_hash=event_hash,
            checkpoint_id=record["checkpoint_id"],
            merkle_root=record["merkle_root"],
            proof_path=proof_path,
            valid=valid,
        )

    raise ValueError(
        f"Evento com hash '{event_hash}' não está coberto por nenhum checkpoint existente."
    )
