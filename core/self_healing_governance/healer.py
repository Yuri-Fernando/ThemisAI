"""Self-Healing Governance — "auto-cura" honesta: detecta falha de um check
de saúde (`checks: dict[str, bool]`, resultado de checks REAIS já rodados por
outros módulos — ex. `blockchain_audit_layer.verify_checkpoint_chain()`),
abre um incidente automaticamente via `incident_response.IncidentLog`, e
sugere passos de remediação de um catálogo declarativo.

**Escopo honesto**: "self-healing" aqui significa detectar + registrar +
recomendar, NUNCA modificar código ou dados de produção sozinho. Um sistema
que "auto-corrige" uma cadeia de hash adulterada ou reescreve regras de
política sem revisão humana seria perigoso, não uma feature — esse tipo de
remediação automática de verdade fica fora de escopo desta versão, por
design, não por limitação técnica.
"""
from __future__ import annotations

from core.incident_response.log import IncidentLog
from shared.schemas import HealingAction, RiskLevel

# Catálogo declarativo: nome do check -> (severidade sugerida, passos de remediação).
REMEDIATION_CATALOG: dict[str, dict] = {
    "audit_chain_integrity": {
        "severity": RiskLevel.CRITICAL,
        "steps": [
            "Isolar o arquivo de log imediatamente (cópia read-only para investigação).",
            "Identificar o primeiro evento cuja verificação falhou (bisseção manual em audit_logs.verify_chain).",
            "Levantar quem teve acesso de escrita ao arquivo no período suspeito.",
            "Abrir incidente CRITICAL e seguir o runbook de incident_response.",
        ],
    },
    "checkpoint_chain_integrity": {
        "severity": RiskLevel.CRITICAL,
        "steps": [
            "Mesma investigação de audit_chain_integrity, aplicada à cadeia de checkpoints Merkle.",
            "Verificar se algum merkle_root publicado externamente (se houver) diverge do local.",
        ],
    },
    "prompt_security_coverage": {
        "severity": RiskLevel.MEDIUM,
        "steps": [
            "Rodar core.red_team_lab.run_red_team_suite() para localizar os payloads que falharam.",
            "Priorizar os gaps por categoria (injection > exfiltration > jailbreak > obfuscation).",
            "Adicionar/ajustar padrões de detecção em prompt_security e revalidar com o mesmo suite.",
        ],
    },
    "regulatory_index_freshness": {
        "severity": RiskLevel.LOW,
        "steps": [
            "Rodar core.regulatory_auto_update.diff_against_manifest() para ver o que mudou.",
            "Revisar as mudanças manualmente (nunca reindexar automaticamente sem revisão).",
            "Reconstruir o índice com core.regulatory_rag.build_index() após aprovação.",
        ],
    },
}

_DEFAULT_STEPS = ["Investigar manualmente — nenhum runbook declarado para este check."]


def check_and_heal(
    checks: dict[str, bool],
    incident_log: IncidentLog | None = None,
) -> list[HealingAction]:
    """Para cada check com resultado `False` (não saudável), abre um
    incidente real em `incident_response` e retorna a ação de "cura"
    sugerida (detecção + registro + recomendação, nunca correção automática
    de dados/código).

    Args:
        checks: mapa `nome_do_check -> saudável?` — resultado de checks já
            executados por outros módulos (ex.
            `{"audit_chain_integrity": logger.verify_chain()}`). Este módulo
            não roda os checks sozinho, para não acoplar a todos os módulos
            possíveis — recebe o resultado já computado.
        incident_log: `IncidentLog` a usar (default: instância nova apontando
            para o armazenamento padrão de `incident_response`).

    Returns:
        Uma `HealingAction` por check, saudável ou não (checks saudáveis têm
        `incident_id=None` e `suggested_steps=[]`).
    """
    incident_log = incident_log or IncidentLog()
    actions: list[HealingAction] = []

    for check_name, healthy in checks.items():
        if healthy:
            actions.append(HealingAction(check_name=check_name, healthy=True, incident_id=None, suggested_steps=[]))
            continue

        catalog_entry = REMEDIATION_CATALOG.get(check_name)
        severity = catalog_entry["severity"] if catalog_entry else RiskLevel.MEDIUM
        steps = catalog_entry["steps"] if catalog_entry else _DEFAULT_STEPS

        incident = incident_log.report_incident(
            title=f"Check de saúde falhou: {check_name}",
            description=(
                f"O check '{check_name}' retornou não-saudável (False). "
                f"Aberto automaticamente por self_healing_governance.check_and_heal()."
            ),
            severity=severity,
        )
        actions.append(
            HealingAction(
                check_name=check_name,
                healthy=False,
                incident_id=incident.incident_id,
                suggested_steps=steps,
            )
        )

    return actions
