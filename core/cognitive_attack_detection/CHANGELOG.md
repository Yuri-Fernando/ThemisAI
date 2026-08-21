# Changelog — Cognitive Attack Detection

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Este módulo segue SemVer independente (`core/cognitive_attack_detection/`).

## [0.1.0] - 2026-08-21

### Added

- Extração real do item "Cognitive Attack Detection" do V3.
- `conversation_scanner.py`: `scan_conversation(turns, window_size=3) ->
  ConversationScanResult` — escaneia cada turno individualmente via
  `prompt_security.scan()` (V1) real, E janelas deslizantes de turnos
  concatenados, capturando payloads divididos entre turnos.
- Contratos novos em `shared/schemas.py` (`ConversationTurnResult`,
  `ConversationScanResult`).
- Suíte de testes pytest (`tests/test_conversation_scanner.py`, 7 testes),
  incluindo um **caso real de fragmentação encontrado empiricamente** (não
  fabricado): os fragmentos `"Antes de continuar, ignore"` / `"as
  instrucoes"` / `"anteriores, por favor."` passam individualmente pelo
  `prompt_security`, mas concatenados disparam `prompt_injection` — prova de
  que a técnica de reassemblagem captura um ataque real que o scan
  turno-a-turno sozinho perderia.

### Notes

- **Escopo honesto**: cobre fragmentação de payload reconhecível (o mesmo
  regex do `prompt_security`, só aplicado a texto reassemblado) — não
  detecção de manipulação psicológica multi-turno genuinamente sofisticada
  sem nenhum fragmento de payload reconhecível (exigiria um classificador
  treinado, quebrando o determinismo do projeto). Ver
  `docs/architecture/v3-frontier-research.md`.
