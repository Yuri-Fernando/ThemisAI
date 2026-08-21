# Changelog — Blockchain Audit Layer

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Este módulo segue SemVer independente (`core/blockchain_audit_layer/`).

## [0.1.0] - 2026-08-20

### Added

- `engine.py`: evolução honesta do `core/audit_logs` com checkpoints Merkle:
  - `merkle_root(leaves) -> str` e prova de inclusão (`_merkle_proof_path`/
    `_verify_proof_path`, internas) — árvore de Merkle padrão (duplica o
    último nó em nível ímpar).
  - `create_checkpoint(logger=None, checkpoint_path=None) -> MerkleCheckpoint`
    — agrupa os eventos gravados desde o último checkpoint num Merkle root,
    encadeado ao checkpoint anterior via hash-chain própria (mesmo padrão de
    `audit_logs.AuditLogger`, arquivo `.jsonl` separado). Levanta `ValueError`
    se não houver eventos novos.
  - `get_proof(event_hash, ...) -> MerkleProof` — localiza o checkpoint que
    cobre o evento, reconstrói a árvore local e gera+verifica uma prova de
    inclusão `O(log n)`.
  - `verify_checkpoint_chain(checkpoint_path=None) -> bool` — recalcula a
    cadeia de checkpoints do zero para detectar adulteração.
- Contratos novos em `shared/schemas.py` (`MerkleCheckpoint`,
  `MerkleProofStep`, `MerkleProof`).
- Suíte de testes pytest (`tests/test_engine.py`, 13 testes) sobre uma
  `AuditLogger` real isolada em arquivo temporário (nunca toca o log de
  produção): raiz de Merkle determinística e sensível à ordem; número ímpar
  de folhas; primeiro/segundo checkpoint cobrindo os ranges corretos;
  encadeamento entre checkpoints; erro quando não há evento novo; detecção
  de adulteração do `merkle_root`; prova de inclusão válida para todo evento
  de um checkpoint, inclusive árvore de 1 folha; erro para evento
  desconhecido; provas cruzando múltiplos checkpoints.

### Notes

- **Escopo honesto (ver docstring do módulo)**: isto reduz — mas não elimina
  — a limitação já documentada em `core/audit_logs/CHANGELOG.md` (um atacante
  com escrita no arquivo E capacidade de rodar a verificação pode recalcular
  tudo do zero). O `merkle_root` de cada checkpoint é o dado pequeno que
  **seria** publicado externamente (git separado, timestamping notarial,
  blockchain pública) para virar uma âncora de verdade contra esse cenário —
  mas nenhuma dessas integrações externas está implementada nesta versão.
  TODO explícito de onda futura.
- Nenhuma lógica de `audit_logs` é reimplementada — este módulo só lê eventos
  via `AuditLogger.read_events()` e escreve sua própria cadeia de
  checkpoints, num arquivo `.jsonl` separado (`core/blockchain_audit_layer/data/checkpoints.jsonl`
  por padrão).
