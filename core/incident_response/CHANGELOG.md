# Changelog — AI Incident Response

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Este módulo segue SemVer independente (`core/incident_response/`).

## [0.1.0] - 2026-08-20

### Added

- `runbooks.yaml`: runbook declarativo real de resposta a incidentes por
  severidade (critical/high/medium/low) — passos de conter, preservar
  evidência, avaliar impacto, notificar (referenciando LGPD Art. 48),
  escalar para `human_oversight`, post-mortem.
- `log.py`:
  - `IncidentLog` — registro real de incidentes, persistido em JSON mutável
    (mesmo padrão de `human_oversight`): `report_incident`, `list_incidents`,
    `update_status` (ciclo `open -> investigating -> resolved`, resolução
    exige `resolution_notes`, incidente resolvido não pode ser reaberto),
    `get`.
  - `get_runbook(severity, runbooks_path=None) -> list[str]`.
- Contratos novos em `shared/schemas.py` (`IncidentStatus`, `Incident`).
- Suíte de testes pytest (`tests/test_log.py`, 12 testes) contra arquivo
  temporário real: criação, persistência entre instâncias, transições de
  status, exigência de notas na resolução, proibição de reabertura,
  filtragem por status, `related_event_ids`, runbook por severidade.

### Notes

- `related_event_ids` liga um incidente a eventos reais de
  `core.audit_logs` — a integração automática (`red_team_lab` ou
  `blockchain_audit_layer.verify_checkpoint_chain() == False` abrindo um
  incidente sozinho) é TODO de onda futura; este módulo entrega o registro
  em si, pronto para ser alimentado.
- Runbook é conteúdo de referência real (passos padrão de resposta a
  incidente adaptados ao contexto de IA/LGPD), não gerado dinamicamente —
  cada organização real precisaria adaptar os passos ao seu próprio processo.
