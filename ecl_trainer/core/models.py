from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ecl_trainer.core.policy import HEX_SHA256_RE, NoPayloadValidator, payload_policy_assertion
from ecl_trainer.core.version import (
    DEFAULT_SCHEMA_VERSION,
    NO_PAYLOAD_POLICY_VERSION,
    SDK_VERSION,
    VALIDATOR_VERSION,
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    @model_validator(mode="after")
    def validate_no_payload(self):
        NoPayloadValidator().validate(self.model_dump(mode="python"))
        return self

    @field_validator("*", mode="after")
    @classmethod
    def validate_hash_fields(cls, value, info):
        field_name = info.field_name or ""
        if field_name.endswith("_hash_sha256") and value not in {None, ""}:
            if not isinstance(value, str) or not HEX_SHA256_RE.match(value):
                raise ValueError(f"{field_name} must be SHA-256 hex")
        return value


class ReportProfile(StrEnum):
    INTERNAL_AUDIT = "internal_audit"
    AB2013_PUBLIC_SUMMARY = "ab2013_public_summary"
    EU_AI_ACT_TECHNICAL_DOC = "eu_ai_act_technical_doc"
    ENTERPRISE_RISK_REVIEW = "enterprise_risk_review"
    CI_PR_SUMMARY = "ci_pr_summary"
    MODEL_RELEASE_SIGNOFF = "model_release_signoff"
    LEGAL_EXECUTIVE_SUMMARY = "legal_executive_summary"


class PayloadPolicyAssertion(FrozenModel):
    policy_name: Literal["NO_PAYLOAD_POLICY"] = "NO_PAYLOAD_POLICY"
    policy_version: str = NO_PAYLOAD_POLICY_VERSION
    validator_version: str = VALIDATOR_VERSION
    raw_payload_absent: bool = True
    model_weights_absent: bool = True
    token_sequences_absent: bool = True
    embeddings_absent: bool = True
    outbound_validation_passed: bool = True
    validation_timestamp: datetime = Field(default_factory=_utc_now)


class TokenEstimateMatrix(FrozenModel):
    total_estimated_tokens: int = 0
    by_segment: dict[str, int] = Field(default_factory=dict)
    by_modality: dict[str, int] = Field(default_factory=dict)
    estimation_method: str = "metadata_only"


class SemanticTag(FrozenModel):
    namespace: str
    key: str
    value: str
    confidence: float = 1.0
    source: str = "local"
    emitted_by: str = "ecl_trainer"
    raw_value_absent: bool = True


class ProvenanceDescriptor(FrozenModel):
    origin_type: str
    origin_system: str
    origin_model_id: str | None = None
    synthetic_data: bool = False
    human_generated: bool | None = None
    machine_generated: bool | None = None
    collection_time_range: str | None = None
    temporal_validity_scope: str | None = None
    jurisdiction_tags: list[str] = Field(default_factory=list)
    data_subject_category_tags: list[str] = Field(default_factory=list)


class LicenseDescriptor(FrozenModel):
    license_name: str
    license_family: str
    license_url_hash_sha256: str | None = None
    license_text_hash_sha256: str | None = None
    commercial_use_allowed: bool | None = None
    attribution_required: bool | None = None
    redistribution_allowed: bool | None = None
    training_use_allowed: bool | None = None
    expiration: datetime | None = None
    evidence_reference_hash_sha256: str | None = None


class MutationEvent(FrozenModel):
    mutation_id: str
    mutation_type: str
    created_at: datetime = Field(default_factory=_utc_now)
    actor_type: str
    input_hash_sha256: str
    output_hash_sha256: str
    transform_descriptor: str
    transform_config_hash_sha256: str


class RiskFlag(FrozenModel):
    risk_type: str
    severity: str
    confidence: float
    matching_metadata_categories: list[str] = Field(default_factory=list)
    remediation: str


class RiskSummary(FrozenModel):
    status: str = "pass"
    risk_flags: list[RiskFlag] = Field(default_factory=list)


class DataIngestEvent(FrozenModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: Literal["data_ingest"] = "data_ingest"
    schema_version: str = DEFAULT_SCHEMA_VERSION
    created_at: datetime = Field(default_factory=_utc_now)
    project_namespace: str
    training_run_id: str | None = None
    source_system_root_uri: str
    source_system_root_hash_sha256: str
    content_hash_sha256: str
    schema_hash_sha256: str
    chunk_manifest_hash_sha256: str
    token_count_estimates: TokenEstimateMatrix = Field(default_factory=TokenEstimateMatrix)
    semantic_tags: list[SemanticTag] = Field(default_factory=list)
    provenance: ProvenanceDescriptor
    license_matrix: list[LicenseDescriptor] = Field(default_factory=list)
    mutation_trail: list[MutationEvent] = Field(default_factory=list)
    payload_policy: PayloadPolicyAssertion = Field(default_factory=PayloadPolicyAssertion)
    previous_event_hash_sha256: str | None = None
    event_hash_sha256: str = ""
    signature: str | None = None


class EvalOutcomeEvent(FrozenModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: Literal["eval_outcome"] = "eval_outcome"
    schema_version: str = DEFAULT_SCHEMA_VERSION
    created_at: datetime = Field(default_factory=_utc_now)
    project_namespace: str
    training_run_id: str
    checkpoint_id: str
    exposed_dataset_hashes: list[str] = Field(default_factory=list)
    metrics_delta: dict[str, float] = Field(default_factory=dict)
    priority_vector: dict[str, float] = Field(default_factory=dict)
    delta_eval_scalar: float = 0.0
    old_value_multiplier: float = 1.0
    new_value_multiplier: float = 1.0
    feedback_loop_placeholder: dict[str, Any] = Field(default_factory=dict)
    payload_policy: PayloadPolicyAssertion = Field(default_factory=PayloadPolicyAssertion)
    previous_event_hash_sha256: str | None = None
    event_hash_sha256: str = ""
    signature: str | None = None


class TrainingCheckpointEvent(FrozenModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: Literal["training_checkpoint"] = "training_checkpoint"
    schema_version: str = DEFAULT_SCHEMA_VERSION
    created_at: datetime = Field(default_factory=_utc_now)
    project_namespace: str
    training_run_id: str
    checkpoint_id: str
    exposed_dataset_hash: str
    checkpoint_reference_hash_sha256: str
    payload_policy: PayloadPolicyAssertion = Field(default_factory=PayloadPolicyAssertion)
    previous_event_hash_sha256: str | None = None
    event_hash_sha256: str = ""
    signature: str | None = None


class CIScanEvent(FrozenModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: Literal["ci_scan"] = "ci_scan"
    schema_version: str = DEFAULT_SCHEMA_VERSION
    created_at: datetime = Field(default_factory=_utc_now)
    project_namespace: str
    repository_root_hash_sha256: str
    ci_provider: str
    ci_run_id: str
    commit_hash_sha256: str
    pull_request_id_hash: str | None = None
    merge_request_id_hash: str | None = None
    changed_path_hashes: list[str] = Field(default_factory=list)
    risk_summary: RiskSummary = Field(default_factory=RiskSummary)
    report_hash_sha256: str
    payload_policy: PayloadPolicyAssertion = Field(default_factory=PayloadPolicyAssertion)
    previous_event_hash_sha256: str | None = None
    event_hash_sha256: str = ""
    signature: str | None = None


class OracleShieldRunEvent(FrozenModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: Literal["oracle_shield_run"] = "oracle_shield_run"
    schema_version: str = DEFAULT_SCHEMA_VERSION
    created_at: datetime = Field(default_factory=_utc_now)
    project_namespace: str
    source_baseline_identity: str = "not_declared"
    atlas_manifest_hash: str
    global_core_used: Literal[True] = True
    enabled_domains: list[str] = Field(default_factory=list)
    skipped_domains: list[str] = Field(default_factory=list)
    domain_selection_mode: str = "auto"
    alert_count: int = 0
    critical_count: int = 0
    warn_count: int = 0
    review_count: int = 0
    quarantine_count: int = 0
    benchmark_alert_count: int = 0
    lineage_alert_count: int = 0
    provenance_gap_count: int = 0
    oracle_alerts_hash_sha256: str
    oracle_blueprint_hash_sha256: str | None = None
    payload_policy: PayloadPolicyAssertion = Field(default_factory=PayloadPolicyAssertion)
    previous_event_hash_sha256: str | None = None
    event_hash_sha256: str = ""
    signature: str | None = None


class DatasetRegisteredEvent(FrozenModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: Literal["dataset_registered"] = "dataset_registered"
    schema_version: str = DEFAULT_SCHEMA_VERSION
    created_at: datetime = Field(default_factory=_utc_now)
    project_namespace: str
    dataset_identifier_hash_sha256: str
    schema_hash_sha256: str | None = None
    metadata_record_hash_sha256: str
    source_reference_hash_sha256: str | None = None
    raw_dataset_absent: bool = True
    payload_policy: PayloadPolicyAssertion = Field(default_factory=PayloadPolicyAssertion)
    previous_event_hash_sha256: str | None = None
    event_hash_sha256: str = ""
    signature: str | None = None


class CurriculumBlueprintEvent(FrozenModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: Literal["curriculum_blueprint_generated"] = "curriculum_blueprint_generated"
    schema_version: str = DEFAULT_SCHEMA_VERSION
    created_at: datetime = Field(default_factory=_utc_now)
    project_namespace: str
    atlas_manifest_hash: str
    enabled_domains: list[str] = Field(default_factory=list)
    skipped_domains: list[str] = Field(default_factory=list)
    domain_selection_mode: str = "auto"
    divergence_risk_coefficient: float
    estimated_compute_optimization_gain: float
    curriculum_blueprint_hash_sha256: str
    payload_policy: PayloadPolicyAssertion = Field(default_factory=PayloadPolicyAssertion)
    previous_event_hash_sha256: str | None = None
    event_hash_sha256: str = ""
    signature: str | None = None


class RiskGateDecisionEvent(FrozenModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: Literal["risk_gate_decision"] = "risk_gate_decision"
    schema_version: str = DEFAULT_SCHEMA_VERSION
    created_at: datetime = Field(default_factory=_utc_now)
    project_namespace: str
    risk_gate_status: str
    training_data_risk_score: int
    benchmark_contamination_score: int
    lineage_loop_score: int
    provenance_completeness_score: int
    compliance_readiness_score: int
    runtime_policy_recommendations: list[str] = Field(default_factory=list)
    risk_scorecard_hash_sha256: str
    payload_policy: PayloadPolicyAssertion = Field(default_factory=PayloadPolicyAssertion)
    previous_event_hash_sha256: str | None = None
    event_hash_sha256: str = ""
    signature: str | None = None


class CompliancePassportEvent(FrozenModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: Literal["compliance_passport_generated"] = "compliance_passport_generated"
    schema_version: str = DEFAULT_SCHEMA_VERSION
    created_at: datetime = Field(default_factory=_utc_now)
    project_namespace: str
    report_profile: str
    ledger_event_count: int
    hash_chain_valid: bool
    atlas_manifest_hash: str | None = None
    enabled_domains: list[str] = Field(default_factory=list)
    domain_sections_hash_sha256: str
    passport_report_hash_sha256: str
    passport_markdown_hash_sha256: str
    payload_policy: PayloadPolicyAssertion = Field(default_factory=PayloadPolicyAssertion)
    previous_event_hash_sha256: str | None = None
    event_hash_sha256: str = ""
    signature: str | None = None


class DiffFreePREvidenceEvent(FrozenModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: Literal["diff_free_pr_evidence"] = "diff_free_pr_evidence"
    schema_version: str = DEFAULT_SCHEMA_VERSION
    created_at: datetime = Field(default_factory=_utc_now)
    project_namespace: str
    metadata_file_count: int
    changed_path_hashes: list[str] = Field(default_factory=list)
    raw_diff_absent: bool = True
    raw_payload_absent: bool = True
    diff_free_pr_proof_hash_sha256: str
    payload_policy: PayloadPolicyAssertion = Field(default_factory=PayloadPolicyAssertion)
    previous_event_hash_sha256: str | None = None
    event_hash_sha256: str = ""
    signature: str | None = None


class LocalArtifactExportEvent(FrozenModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: Literal["local_artifact_export"] = "local_artifact_export"
    schema_version: str = DEFAULT_SCHEMA_VERSION
    created_at: datetime = Field(default_factory=_utc_now)
    project_namespace: str
    artifact_bundle_type: str = "ci_pr_report"
    local_only_execution: bool = True
    saas_submission_executed: bool = False
    dataset_upload_executed: bool = False
    output_artifact_count: int
    output_artifact_hashes_sha256: dict[str, str] = Field(default_factory=dict)
    ledger_verification_status: str
    payload_policy: PayloadPolicyAssertion = Field(default_factory=PayloadPolicyAssertion)
    previous_event_hash_sha256: str | None = None
    event_hash_sha256: str = ""
    signature: str | None = None


class HumanApprovalRecordedEvent(FrozenModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: Literal["human_approval_recorded"] = "human_approval_recorded"
    schema_version: str = DEFAULT_SCHEMA_VERSION
    created_at: datetime = Field(default_factory=_utc_now)
    project_namespace: str
    risk_id: str
    approver_role: str
    reason_code: str
    accepted_risk_status: str
    human_approval_hash_sha256: str
    payload_policy: PayloadPolicyAssertion = Field(default_factory=PayloadPolicyAssertion)
    previous_event_hash_sha256: str | None = None
    event_hash_sha256: str = ""
    signature: str | None = None


class HuggingFaceCardExportEvent(FrozenModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: Literal["hf_card_exported"] = "hf_card_exported"
    schema_version: str = DEFAULT_SCHEMA_VERSION
    created_at: datetime = Field(default_factory=_utc_now)
    project_namespace: str
    ecl_fingerprint_hash_sha256: str
    compliance_passport_hash_sha256: str
    hf_card_hash_sha256: str
    payload_policy: PayloadPolicyAssertion = Field(default_factory=PayloadPolicyAssertion)
    previous_event_hash_sha256: str | None = None
    event_hash_sha256: str = ""
    signature: str | None = None


class SignedLedgerEnvelope(FrozenModel):
    schema_version: str = DEFAULT_SCHEMA_VERSION
    event_type: str
    event_id: UUID = Field(default_factory=uuid4)
    tenant_id_hash: str
    project_namespace: str
    created_at: datetime = Field(default_factory=_utc_now)
    payload_hash_sha256: str
    payload: dict[str, Any]
    previous_event_hash_sha256: str | None = None
    signature: str
    sdk_version: str = SDK_VERSION
    payload_policy_assertion: PayloadPolicyAssertion = Field(default_factory=PayloadPolicyAssertion)


class ModelLineageRecord(FrozenModel):
    model_id: str
    parent_model_id: str | None = None
    base_model_family: str | None = None
    checkpoint_hash: str | None = None
    training_run_id: str | None = None
    synthetic_data_origin_model_id: str | None = None
    ancestor_model_ids: list[str] = Field(default_factory=list)


class RegistryMatch(FrozenModel):
    matched: bool
    risk_flags: list[RiskFlag] = Field(default_factory=list)


def default_payload_policy() -> PayloadPolicyAssertion:
    return PayloadPolicyAssertion.model_validate(payload_policy_assertion())
