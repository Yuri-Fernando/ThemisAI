# Changelog — Memory Governance

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Este módulo segue SemVer independente (`core/memory_governance/`).

## [0.1.0] - 2026-08-20

### Added

- `store.py`: `MemoryStore` — `store(content, ttl_days=None) -> MemoryItem`
  escaneia `content` de verdade via `pii_detection.detect()` e redige
  (`[REDACTED:TIPO]`) qualquer PII encontrada ANTES de persistir — o texto
  original com PII nunca toca o disco quando há achado. `list_active()`
  (exclui expirados) e `purge_expired()` (remove permanentemente,
  retorna contagem).
- Contrato novo em `shared/schemas.py` (`MemoryItem`).
- Suíte de testes pytest (`tests/test_store.py`, 8 testes): conteúdo sem PII
  não é redigido; CPF real é redigido (span removido, resto do texto
  preservado); conteúdo sensível marca categoria correta; TTL define/não
  define expiração; `list_active` exclui expirados; `purge_expired` remove
  do disco e retorna a contagem correta.

### Notes

- Redação é o comportamento padrão e único (não configurável/opcional) —
  decisão de design deliberada: memória de longo prazo é exatamente a
  superfície onde PII vaza sem ninguém perceber se não houver um portão
  automático, obrigatório.
- Não reimplementa nada de `pii_detection` — só orquestra `detect()` real e
  aplica a redação sobre os spans retornados.
