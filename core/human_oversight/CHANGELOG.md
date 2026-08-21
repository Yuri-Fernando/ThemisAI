# Changelog — Human Oversight

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Este módulo segue SemVer independente (`core/human_oversight/`).

## [0.1.0] - 2026-08-20

### Added

- `queue.py`: `OversightQueue`, fila real de itens pendentes de revisão
  humana, persistida em JSON (não `.jsonl` append-only como `audit_logs` —
  itens desta fila são **mutáveis**, mudam de `pending` para
  `approved`/`rejected`, então precisam de leitura+escrita completa):
  - `enqueue(subject, reason, risk_level) -> OversightItem`.
  - `list_items(status=None) -> list[OversightItem]`.
  - `get(item_id) -> OversightItem`.
  - `decide(item_id, approve, reviewer, notes=None) -> OversightItem` —
    decisão definitiva (levanta `ValueError` se o item já foi decidido ou não
    existe).
- Contratos novos em `shared/schemas.py` (`OversightItemStatus`,
  `OversightItem`).
- Suíte de testes pytest (`tests/test_queue.py`, 10 testes) contra arquivo
  temporário real: item criado como `pending`; persistência sobrevive a uma
  nova instância de `OversightQueue` sobre o mesmo arquivo (prova que é
  persistência real, não em memória); filtro por status; decisão de
  aprovação/rejeição preenche os campos corretos; decidir duas vezes levanta
  erro; item/decisão desconhecidos levantam erro; fila vazia.

### Notes

- Alimentação típica: qualquer `PolicyDecision` com `status ==
  REQUIRES_HUMAN_REVIEW` (do `policy_engine`, V1) vira um `enqueue(...)` —
  essa integração (`governance_copilot` chamando `enqueue` automaticamente a
  cada RIPD com decisão `REQUIRES_HUMAN_REVIEW`) é um TODO de onda futura;
  este módulo entrega a fila em si, standalone, pronta para ser alimentada.
- Decisão é definitiva por design nesta versão (sem "reabrir" um item já
  decidido) — se for necessário revisar de novo, cria-se um novo item. Fluxo
  de reabertura é um TODO explícito, não uma limitação escondida.
- Sem autenticação/autorização de quem pode decidir (`reviewer` é só uma
  string livre) — mesma decisão de escopo já documentada em
  `governance_copilot/CHANGELOG.md` (V1 é uso local).
