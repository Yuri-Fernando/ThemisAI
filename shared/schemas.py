"""Contratos compartilhados (Pydantic) do Themis AI — V1.

REGRA DE OURO: todo módulo em core/* e apps/* IMPORTA os tipos daqui.
Nenhum módulo deve redefinir seu próprio PIIFinding, PolicyDecision, etc.
Isso é o que permite ao Governance Copilot compor os módulos sem adapters.

Qualquer mudança neste arquivo é breaking change para todos os módulos:
registre em CHANGELOG.md (seção "Shared Contracts") e suba SCHEMA_VERSION.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

SCHEMA_VERSION = "0.4.0"


# ---------------------------------------------------------------------------
# Enums de domínio (LGPD)
# ---------------------------------------------------------------------------

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DataCategory(str, Enum):
    """LGPD Art. 5º — categorias de dado."""
    PERSONAL = "personal"           # Art. 5º, I
    SENSITIVE = "sensitive"         # Art. 5º, II
    ANONYMIZED = "anonymized"
    NOT_PERSONAL = "not_personal"


class LegalBasis(str, Enum):
    """LGPD Art. 7º/11º — subconjunto ilustrativo de bases legais."""
    CONSENT = "consent"
    LEGITIMATE_INTEREST = "legitimate_interest"
    LEGAL_OBLIGATION = "legal_obligation"
    CONTRACT_EXECUTION = "contract_execution"
    RESEARCH = "research"
    NOT_DETERMINED = "not_determined"


# ---------------------------------------------------------------------------
# PII Detection
# ---------------------------------------------------------------------------

class PIIFinding(BaseModel):
    entity_type: str
    text_span: str
    start: int
    end: int
    category: DataCategory
    confidence: float = Field(ge=0.0, le=1.0)


class PIIDetectionResult(BaseModel):
    findings: list[PIIFinding]
    has_sensitive_data: bool
    summary: str


# ---------------------------------------------------------------------------
# Policy Engine
# ---------------------------------------------------------------------------

class PolicyDecisionStatus(str, Enum):
    ALLOW = "allow"
    ALLOW_WITH_MITIGATION = "allow_with_mitigation"
    DENY = "deny"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"


class PolicyDecision(BaseModel):
    policy_id: str
    status: PolicyDecisionStatus
    rationale: str
    mitigations: list[str] = []
    risk_level: RiskLevel


# ---------------------------------------------------------------------------
# Prompt Security
# ---------------------------------------------------------------------------

class PromptSecurityFinding(BaseModel):
    technique: str  # ex: "prompt_injection", "jailbreak", "pii_exfiltration"
    matched_pattern: str
    severity: RiskLevel


class PromptSecurityResult(BaseModel):
    findings: list[PromptSecurityFinding]
    is_safe: bool
    score: float = Field(ge=0.0, le=1.0, description="1.0 = seguro, 0.0 = altamente suspeito")


# ---------------------------------------------------------------------------
# Explainability / Trust Score
# ---------------------------------------------------------------------------

class ExplainabilityResult(BaseModel):
    subject: str  # o que está sendo explicado (ex: "trust_score", "policy_decision")
    factors: dict[str, float]  # fator -> peso/contribuição
    narrative: str  # explicação em linguagem natural


class TrustScoreResult(BaseModel):
    score: float = Field(ge=0.0, le=100.0)
    risk_level: RiskLevel
    components: dict[str, float]
    explanation: ExplainabilityResult | None = None


# ---------------------------------------------------------------------------
# Audit Logs
# ---------------------------------------------------------------------------

class AuditEventType(str, Enum):
    PII_SCAN = "pii_scan"
    POLICY_EVALUATION = "policy_evaluation"
    PROMPT_SECURITY_SCAN = "prompt_security_scan"
    TRUST_SCORE_COMPUTED = "trust_score_computed"
    RIPD_GENERATED = "ripd_generated"
    RAG_QUERY = "rag_query"


class AuditEvent(BaseModel):
    event_id: str
    event_type: AuditEventType
    timestamp: datetime
    actor: str
    payload: dict[str, Any]
    prev_hash: str
    hash: str


# ---------------------------------------------------------------------------
# Regulatory RAG
# ---------------------------------------------------------------------------

class RegulatoryChunk(BaseModel):
    source: str
    article: str | None = None
    text: str
    score: float


class RAGQueryResult(BaseModel):
    query: str
    chunks: list[RegulatoryChunk]


# ---------------------------------------------------------------------------
# RIPD Report (saída final do Governance Copilot)
# ---------------------------------------------------------------------------

class RIPDReport(BaseModel):
    project_name: str
    generated_at: datetime
    data_categories: list[DataCategory]
    legal_basis: LegalBasis
    pii_result: PIIDetectionResult
    policy_decisions: list[PolicyDecision]
    prompt_security: PromptSecurityResult | None = None
    trust_score: TrustScoreResult
    regulatory_context: list[RegulatoryChunk]
    mitigations: list[str]
    executive_summary: str


# ---------------------------------------------------------------------------
# V2 — Fairness Audit
# ---------------------------------------------------------------------------

class FairnessMetric(BaseModel):
    metric_name: str  # ex.: "disparate_impact", "demographic_parity_difference"
    group: str
    reference_group: str
    value: float
    threshold: float
    passed: bool
    interpretation: str


class FairnessAuditResult(BaseModel):
    protected_attribute: str
    reference_group: str
    sample_sizes: dict[str, int]
    selection_rates: dict[str, float]
    metrics: list[FairnessMetric]
    overall_fair: bool
    summary: str


class FairnessSignificanceResult(BaseModel):
    protected_attribute: str
    chi2_statistic: float
    p_value: float
    degrees_of_freedom: int
    alpha: float
    significant: bool
    summary: str


# ---------------------------------------------------------------------------
# V2 — Blockchain Audit Layer (Merkle checkpoints sobre o hash-chain existente)
# ---------------------------------------------------------------------------

class MerkleCheckpoint(BaseModel):
    checkpoint_id: str
    created_at: datetime
    event_range_start: int
    event_range_end: int
    event_count: int
    merkle_root: str
    prev_checkpoint_hash: str
    checkpoint_hash: str


class MerkleProofStep(BaseModel):
    sibling_hash: str
    position: str  # "left" | "right"


class MerkleProof(BaseModel):
    event_hash: str
    checkpoint_id: str
    merkle_root: str
    proof_path: list[MerkleProofStep]
    valid: bool


# ---------------------------------------------------------------------------
# V2 — Sensitive Data Scanner (evolução do PII Detection p/ documentos)
# ---------------------------------------------------------------------------

class DocumentScanResult(BaseModel):
    file_name: str
    file_type: str
    pages_scanned: int | None = None
    characters_extracted: int
    pii_result: PIIDetectionResult
    extraction_notes: str


# ---------------------------------------------------------------------------
# V2 — AI Observability
# ---------------------------------------------------------------------------

class ModuleCallMetric(BaseModel):
    module: str
    function: str
    started_at: datetime
    duration_ms: float
    status: str  # "ok" | "error"
    error_message: str | None = None


class ObservabilitySnapshot(BaseModel):
    metrics: list[ModuleCallMetric]
    total_calls: int
    error_count: int
    avg_duration_ms: float
    by_module: dict[str, int]


# ---------------------------------------------------------------------------
# V2 — Constitutional AI
# ---------------------------------------------------------------------------

class ConstitutionalViolation(BaseModel):
    principle_id: str
    principle: str
    severity: RiskLevel
    rationale: str


class ConstitutionalCheckResult(BaseModel):
    context: dict[str, Any]
    violations: list[ConstitutionalViolation]
    compliant: bool
    summary: str


# ---------------------------------------------------------------------------
# V2 — Regulatory Knowledge Graph (GraphRAG)
# ---------------------------------------------------------------------------

class KnowledgeGraphNode(BaseModel):
    id: str
    article: str | None = None
    tema: str | None = None
    source: str


class KnowledgeGraphEdge(BaseModel):
    source: str
    target: str
    relation: str


class RegulatoryKnowledgeGraphResult(BaseModel):
    nodes: list[KnowledgeGraphNode]
    edges: list[KnowledgeGraphEdge]
    node_count: int
    edge_count: int


class RelatedArticle(BaseModel):
    id: str
    article: str | None = None
    tema: str | None = None
    distance: int


# ---------------------------------------------------------------------------
# V2 — Human Oversight
# ---------------------------------------------------------------------------

class OversightItemStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class OversightItem(BaseModel):
    item_id: str
    created_at: datetime
    subject: str
    reason: str
    risk_level: RiskLevel
    status: OversightItemStatus
    reviewer: str | None = None
    decided_at: datetime | None = None
    decision_notes: str | None = None


# ---------------------------------------------------------------------------
# V2 — Traceability
# ---------------------------------------------------------------------------

class TraceLink(BaseModel):
    trace_id: str
    event_ids: list[str]
    created_at: datetime
    summary: str


# ---------------------------------------------------------------------------
# V2 — Red Team Lab
# ---------------------------------------------------------------------------

class AttackResult(BaseModel):
    attack_id: str
    category: str
    payload: str
    detected: bool
    expected_detection: bool
    passed: bool


class RedTeamReport(BaseModel):
    total_attacks: int
    detected_count: int
    detection_rate: float
    results: list[AttackResult]
    summary: str


# ---------------------------------------------------------------------------
# V2 — AI Incident Response
# ---------------------------------------------------------------------------

class IncidentStatus(str, Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"


class Incident(BaseModel):
    incident_id: str
    created_at: datetime
    title: str
    description: str
    severity: RiskLevel
    status: IncidentStatus
    related_event_ids: list[str] = []
    resolution_notes: str | None = None
    resolved_at: datetime | None = None


# ---------------------------------------------------------------------------
# V2 — Regulatory Sandbox
# ---------------------------------------------------------------------------

class SandboxScenario(BaseModel):
    name: str
    data_categories: list[DataCategory]
    legal_basis: LegalBasis
    context: dict[str, Any] | None = None


class SandboxResult(BaseModel):
    scenario_name: str
    policy_decisions: list[PolicyDecision]
    trust_score: TrustScoreResult


class SandboxComparison(BaseModel):
    scenario_a: SandboxResult
    scenario_b: SandboxResult
    score_delta: float
    decisions_added: list[str]
    decisions_removed: list[str]
    summary: str


# ---------------------------------------------------------------------------
# V2 — Regulatory Auto-Update
# ---------------------------------------------------------------------------

class CorpusFileSnapshot(BaseModel):
    filename: str
    content_hash: str
    article: str | None = None
    tema: str | None = None


class CorpusManifest(BaseModel):
    generated_at: datetime
    files: list[CorpusFileSnapshot]


class CorpusDiff(BaseModel):
    added: list[str]
    removed: list[str]
    modified: list[str]
    unchanged: list[str]
    summary: str


# ---------------------------------------------------------------------------
# V2 — Multi-Agent Governance
# ---------------------------------------------------------------------------

class AgentRole(BaseModel):
    agent_id: str
    name: str
    allowed_actions: list[str]
    risk_tier: RiskLevel


class AuthorizationResult(BaseModel):
    agent_id: str
    action: str
    authorized: bool
    reason: str


# ---------------------------------------------------------------------------
# V2 — Agent Tribunal
# ---------------------------------------------------------------------------

class TribunalVerdict(BaseModel):
    decisions_considered: list[str]
    final_status: PolicyDecisionStatus
    risk_level: RiskLevel
    rationale: str


# ---------------------------------------------------------------------------
# V2 — Memory Governance
# ---------------------------------------------------------------------------

class MemoryItem(BaseModel):
    memory_id: str
    created_at: datetime
    content: str
    category: DataCategory
    redacted: bool
    expires_at: datetime | None = None


# ---------------------------------------------------------------------------
# V2 — Self-Healing Governance
# ---------------------------------------------------------------------------

class HealingAction(BaseModel):
    check_name: str
    healthy: bool
    incident_id: str | None = None
    suggested_steps: list[str]


# ---------------------------------------------------------------------------
# V2 — Synthetic Data
# ---------------------------------------------------------------------------

class SyntheticPersonRecord(BaseModel):
    name: str
    cpf: str
    email: str
    phone: str
    synthetic: bool = True


# ---------------------------------------------------------------------------
# V2 — Differential Privacy
# ---------------------------------------------------------------------------

class DPQueryResult(BaseModel):
    mechanism: str
    true_value: float
    noisy_value: float
    epsilon: float
    sensitivity: float


# ---------------------------------------------------------------------------
# V2 — Federated Governance
# ---------------------------------------------------------------------------

class NodeReport(BaseModel):
    node_id: str
    total_evaluations: int
    avg_trust_score: float
    deny_count: int
    risk_level_counts: dict[str, int]


class FederatedSummary(BaseModel):
    node_count: int
    total_evaluations: int
    weighted_avg_trust_score: float
    total_deny_count: int
    per_node: list[NodeReport]
    summary: str


# ---------------------------------------------------------------------------
# V3 (extração real) — Formal Verification (model checking por enumeração)
# ---------------------------------------------------------------------------

class Counterexample(BaseModel):
    inputs: dict[str, Any]
    description: str


class VerificationResult(BaseModel):
    property_name: str
    total_cases_checked: int
    holds: bool
    counterexample: Counterexample | None = None
    summary: str


# ---------------------------------------------------------------------------
# V3 (extração real) — AI Constitution Compiler (conflitos estáticos)
# ---------------------------------------------------------------------------

class ConstitutionConflict(BaseModel):
    article_a: str
    article_b: str
    conflict_type: str  # "overlapping_condition_different_severity" | "duplicate_condition" | "subsumption"
    explanation: str


class ConstitutionCompileResult(BaseModel):
    article_count: int
    conflicts: list[ConstitutionConflict]
    valid: bool
    summary: str


# ---------------------------------------------------------------------------
# V3 (extração real) — Causal Fairness (Paradoxo de Simpson)
# ---------------------------------------------------------------------------

class StratumResult(BaseModel):
    stratum: str
    sample_size: int
    fairness: FairnessAuditResult


class StratifiedFairnessResult(BaseModel):
    protected_attribute: str
    confound_attribute: str
    aggregate: FairnessAuditResult
    strata: list[StratumResult]
    simpsons_paradox_detected: bool
    summary: str


# ---------------------------------------------------------------------------
# V3 (extração real) — Behavioral Monitoring (drift via teste KS)
# ---------------------------------------------------------------------------

class DriftReport(BaseModel):
    metric_name: str
    baseline_size: int
    current_size: int
    ks_statistic: float
    p_value: float
    alpha: float
    drift_detected: bool
    summary: str


# ---------------------------------------------------------------------------
# V3 (extração real) — Cognitive Attack Detection (multi-turno)
# ---------------------------------------------------------------------------

class ConversationTurnResult(BaseModel):
    turn_index: int
    text: str
    is_safe: bool
    score: float


class ConversationScanResult(BaseModel):
    turns: list[ConversationTurnResult]
    reassembled_findings: list[str]
    overall_safe: bool
    summary: str


# ---------------------------------------------------------------------------
# V3 (extração real) — Runtime Policy Enforcement (nível de aplicação)
# ---------------------------------------------------------------------------

class EnforcementDenied(BaseModel):
    agent_id: str
    action: str
    reason: str


# ---------------------------------------------------------------------------
# V4 (extração real) — Meta-Governance Layer
# ---------------------------------------------------------------------------

class NodeComplianceReport(BaseModel):
    node_id: str
    checks_total: int
    checks_healthy: int
    compliance_rate: float
    compliant: bool


class MetaGovernanceReport(BaseModel):
    federation_compliance_rate: float
    non_compliant_nodes: list[str]
    per_node: list[NodeComplianceReport]
    summary: str


# ---------------------------------------------------------------------------
# V4 (extração real) — Regulatory Simulation Sandbox
# ---------------------------------------------------------------------------

class RegulatoryChangeImpact(BaseModel):
    changed_article: str
    directly_affected_articles: list[str]
    scenarios_evaluated: int
    scenarios_with_score_change: int
    comparisons: list[SandboxComparison]
    summary: str


# ---------------------------------------------------------------------------
# V4 (extração real) — Adversarial ML / AI Security
# ---------------------------------------------------------------------------

class AdversarialAttackResult(BaseModel):
    """Resultado real de um ataque adversarial executado contra um modelo.

    `attack` é o nome do ataque (fgsm, pgd, extraction, poisoning). As
    acurácias são medidas sobre o mesmo conjunto de avaliação — `clean` sem
    perturbação, `adversarial` com a perturbação do ataque aplicada.
    """
    attack: str
    epsilon: float | None = None
    clean_accuracy: float
    adversarial_accuracy: float
    accuracy_drop: float
    success_rate: float
    samples_evaluated: int
    extra: dict[str, Any] = Field(default_factory=dict)


class RobustnessMetrics(BaseModel):
    """Métricas agregadas de robustez de um modelo sob ataque."""
    clean_accuracy: float
    robust_accuracy: float
    min_perturbation_budget: float | None = None
    robustness_curve: list[dict[str, float]] = Field(default_factory=list)
    risk_level: RiskLevel


class DefenseEvaluation(BaseModel):
    """Comparação antes/depois de aplicar uma defesa (ex.: adversarial training)."""
    defense: str
    robust_accuracy_before: float
    robust_accuracy_after: float
    clean_accuracy_before: float
    clean_accuracy_after: float
    summary: str


class ModelSecurityReport(BaseModel):
    """Relatório consolidado de segurança de um modelo — o `MODEL SECURITY
    REPORT` textual é derivado deste objeto por `robustness/report.py`.
    """
    model_name: str
    clean_accuracy: float
    attacks: list[AdversarialAttackResult]
    robustness: RobustnessMetrics
    defenses: list[DefenseEvaluation] = Field(default_factory=list)
    llm_security: dict[str, Any] = Field(default_factory=dict)
    overall_risk: RiskLevel
    recommendations: list[str] = Field(default_factory=list)
    rendered_report: str = ""
