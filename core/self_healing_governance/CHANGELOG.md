# Changelog — Self-Healing Governance

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Este módulo segue SemVer independente (`core/self_healing_governance/`).

## [0.1.0] - 2026-08-20

### Added

- `healer.py`: `check_and_heal(checks: dict[str, bool], incident_log=None) ->
  list[HealingAction]`. Para cada check não-saudável, abre um incidente real
  via `incident_response.IncidentLog.report_incident()` e retorna passos de
  remediação de um catálogo declarativo (`REMEDIATION_CATALOG`) cobrindo
  `audit_chain_integrity`, `checkpoint_chain_integrity`,
  `prompt_security_coverage`, `regulatory_index_freshness`.
- Contrato novo em `shared/schemas.py` (`HealingAction`).
- Suíte de testes pytest (`tests/test_healer.py`, 5 testes): check saudável
  não abre incidente; check não-saudável abre incidente real (severidade
  correta); check desconhecido usa passos default; múltiplos checks mistos;
  **integração real de ponta a ponta** com `blockchain_audit_layer` (cadeia
  íntegra -> sem incidente; cadeia adulterada de verdade -> incidente aberto
  automaticamente).

### Notes

- **Escopo honesto, por design**: "self-healing" aqui é detectar + registrar
  + recomendar — NUNCA modificar código ou dados de produção sozinho.
  Auto-correção literal de uma cadeia de hash adulterada ou de regras de
  política sem revisão humana seria perigosa, não uma feature — fica fora de
  escopo por decisão de risco, não por limitação técnica.
- Não roda os checks sozinho (recebe `checks` já computados) — evita acoplar
  este módulo a todos os módulos possíveis do projeto.
