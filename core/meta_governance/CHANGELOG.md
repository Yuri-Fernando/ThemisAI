# Changelog — Meta-Governance Layer

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Este módulo segue SemVer independente (`core/meta_governance/`).

## [0.1.0] - 2026-08-21

### Added

- Extração real do item "Meta-Governance Layer" do V4.
- `audit.py`: `audit_federation_health(node_health, compliance_threshold=1.0)
  -> MetaGovernanceReport` — governança sobre governança: audita se cada nó
  de uma federação está executando seus próprios checks de saúde/compliance
  corretamente (complementar a `federated_governance`, V2, que agrega
  métricas de DECISÃO, não de compliance de processo).
- Contratos novos em `shared/schemas.py` (`NodeComplianceReport`,
  `MetaGovernanceReport`).
- Suíte de testes pytest (`tests/test_audit.py`, 8 testes): compliance
  total; nó não-compliant; limiar customizável; taxa da federação ponderada
  por número de checks (não média simples entre nós); validações de
  entrada; **integração real com `self_healing_governance.check_and_heal()`**
  (V2) para construir `node_health` a partir de checks de verdade.

### Notes

- Mesmo princípio de fronteira mínima do `federated_governance`: nunca
  precisa dos dados brutos por trás de cada check, só do resultado booleano
  já computado por cada nó.
