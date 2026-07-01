from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, is_dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from ecl_trainer.core.exceptions import PayloadExfiltrationException
from ecl_trainer.core.version import NO_PAYLOAD_POLICY_VERSION, VALIDATOR_VERSION

FORBIDDEN_KEY_PATTERNS: frozenset[str] = frozenset(
    {
        "text",
        "prompt",
        "completion",
        "response",
        "message",
        "messages",
        "body",
        "content",
        "document",
        "raw",
        "row",
        "rows",
        "sample",
        "samples",
        "example",
        "examples",
        "input_ids",
        "token",
        "token_ids",
        "tokens",
        "token_sequence",
        "embedding",
        "embeddings",
        "vector",
        "vectors",
        "weights",
        "state_dict",
        "checkpoint_bytes",
        "parquet_row",
        "jsonl_line",
        "notebook_cell",
        "diff_hunk",
        "dataset_preview",
        "file_content",
        "source_content",
        "repo_content",
        "secret",
        "api_key",
        "access_token",
        "authorization",
        "bearer",
        "password",
        "private_key",
        "client_secret",
        "refresh_token",
        "local_path",
        "absolute_path",
    }
)

SAFE_METADATA_KEYS: frozenset[str] = frozenset(
    {
        "content_hash_sha256",
        "schema_hash_sha256",
        "source_root_uri",
        "source_root_hash_sha256",
        "source_system_root_uri",
        "source_system_root_hash_sha256",
        "token_count_estimates",
        "token_profile_metrics",
        "token_count_estimate",
        "token_density_histogram_bounds",
        "total_estimated_tokens",
        "by_segment",
        "by_modality",
        "estimation_method",
        "token_estimate_matrix_hash_sha256",
        "semantic_tags",
        "semantic_tag_set_hash_sha256",
        "provenance",
        "license_matrix",
        "license_matrix_hash_sha256",
        "mutation_trail",
        "mutation_trail_hash_sha256",
        "metrics_delta",
        "priority_vector",
        "checkpoint_id",
        "checkpoint_reference_hash_sha256",
        "training_run_id",
        "event_id",
        "event_type",
        "ci_run_id",
        "pr_number",
        "merge_request_iid",
        "report_profile",
        "risk_flags",
        "raw_payload_absent",
        "raw_value_absent",
        "model_weights_absent",
        "token_sequences_absent",
        "embeddings_absent",
        "outbound_validation_passed",
        "payload_hash_sha256",
        "previous_event_hash_sha256",
        "event_hash_sha256",
        "commit_hash_sha256",
        "changed_path_hashes",
        "pull_request_id_hash",
        "merge_request_id_hash",
        "repository_root_hash_sha256",
        "payload_policy",
        "payload_policy_assertion",
        "payload_policy_validation_passed",
        "data_profile_generation",
        "atlas_record_id",
        "source_baseline_identity",
        "lineage_cryptographic_signatures",
        "source_manifest_sha256",
        "record_self_sha256",
        "domain_extension_financial_tags",
        "regulatory_framework_mapping",
        "fiscal_period_bounds",
        "structural_sector_ratios",
        "historical_evaluation_deltas",
        "eval_suite_name",
        "base_performance_score",
        "delta_impact_coefficient",
        "pre_flight_shield_assertions",
        "model_inbreeding_risk",
        "benchmark_contamination_detected",
        "entropy_score",
        "p05",
        "p25",
        "p50",
        "p75",
        "p95",
        "sec_filing_metadata",
        "earnings_event_metadata",
        "market_reference_metadata",
        "bank_supervision_metadata",
        "issuer_reference_metadata",
        "risk_factor_taxonomy",
        "xbrl_taxonomy_metadata",
        "derivatives_market_metadata",
        "broker_dealer_oversight_metadata",
        "public_company_filing_metadata",
        "legal_entity_reference_metadata",
        "market_risk_taxonomy",
        "base_model_family",
        "checkpoint_hash",
        "ancestor_model_ids",
        "atlas_manifest_hash",
        "atlas_signature_hash_sha256",
        "atlas_version_tag",
        "compiled_at",
        "delta_days_active",
        "lifecycle_status",
        "domain_enforcement_messages",
        "supported_domains_mask",
        "ignore_staleness",
        "patch_id",
        "patch_manifest_hash_sha256",
        "patch_signature_hash_sha256",
        "new_atlas_version_tag",
        "target_atlas_version_tag",
        "operation_type",
        "member_path",
        "member_hash_sha256",
        "member_hashes",
        "member_count",
        "applied_operation_count",
        "applied_record_count",
        "updated_domain_count",
        "offline_patch_status",
        "offline_patch_report",
        "global_core_used",
        "enabled_domains",
        "skipped_domains",
        "domain_selection_mode",
        "domain_extension_status",
        "domain_id",
        "domain_status",
        "check_id",
        "severity",
        "category",
        "confidence",
        "action_required",
        "remediation_steps",
        "target_mixture_boundaries",
        "recommended_pruning_criteria",
        "estimated_compute_optimization_gain",
        "compliance_compatibility_scores",
        "divergence_risk_coefficient",
        "oracle_status",
        "blueprint_hash_sha256",
        "admission_status",
        "alert_count",
        "alerts_hash_sha256",
        "artifact_count",
        "artifact_bundle_type",
        "artifact_hashes_sha256",
        "benchmark_contamination_score",
        "benchmark_alert_count",
        "chain_edge_count",
        "chain_edges",
        "compliance_readiness_score",
        "contract_hash_sha256",
        "curriculum_blueprint_hash_sha256",
        "dataset_registered",
        "dataset_upload_executed",
        "diff_free_evidence_hash_sha256",
        "diff_free_pr_proof_hash_sha256",
        "domain_maturity_summary_hash_sha256",
        "event_count",
        "event_hashes_sha256",
        "event_types",
        "expected_event_types",
        "hash_chain_valid",
        "hf_card_hash_sha256",
        "human_approval_hash_sha256",
        "ledger_event_count",
        "ledger_verification_status",
        "lineage_loop_score",
        "lineage_alert_count",
        "local_only_execution",
        "metadata_file_count",
        "metadata_record_hash_sha256",
        "model_admission_decision_hash_sha256",
        "output_artifact_count",
        "output_artifact_hashes_sha256",
        "passport_markdown_hash_sha256",
        "passport_report_hash_sha256",
        "predicted_gate",
        "provenance_completeness_score",
        "provenance_gap_count",
        "raw_dataset_absent",
        "raw_diff_absent",
        "risk_gate_status",
        "risk_id",
        "risk_scorecard_hash_sha256",
        "runtime_contract_valid",
        "runtime_binding_hash_sha256",
        "runtime_policy_recommendations",
        "saas_submission_executed",
        "simulation_mode",
        "training_data_risk_score",
        "release_bundle_manifest_hash_sha256",
    }
)

SENSITIVE_VALUE_RE = re.compile(
    r"(BEGIN\s+(?:RSA|OPENSSH|PRIVATE)|api[_-]?key\s*=|secret\s*=|token\s*=|bearer\s+[a-z0-9._-]+)",
    re.IGNORECASE,
)
BASE64_LIKE_RE = re.compile(r"^[A-Za-z0-9+/]{160,}={0,2}$")
MARKDOWN_CODE_FENCE_RE = re.compile(r"```")
JSON_OBJECT_RE = re.compile(r"^\s*[\[{].*[\]}]\s*$", re.DOTALL)
LOCAL_ABSOLUTE_PATH_RE = re.compile(r"^/(?:Users|private|home|var|tmp|Volumes)/")
HEX_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
TOKEN_SEQUENCES_ABSENT_KEY = "token" + "_sequences_absent"


def sha256_hex(value: bytes | str) -> str:
    data = value.encode("utf-8") if isinstance(value, str) else value
    return hashlib.sha256(data).hexdigest()


def utc_now() -> datetime:
    return datetime.now(UTC)


def normalize_key(key: str) -> str:
    normalized = key.strip().replace("-", "_").replace(" ", "_")
    normalized = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", normalized)
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", normalized)
    return normalized.lower()


class NoPayloadValidator:
    validator_version = VALIDATOR_VERSION

    def __init__(
        self,
        forbidden_keys: set[str] | None = None,
        safe_keys: set[str] | None = None,
    ) -> None:
        self.forbidden_keys = set(forbidden_keys or FORBIDDEN_KEY_PATTERNS)
        self.safe_keys = set(safe_keys or SAFE_METADATA_KEYS)

    def validate(self, value: Any, path: str = "$") -> Any:
        self._walk(value, path)
        return value

    def inspect(self, value: Any, path: str = "$") -> ValidationResult:
        self.validate(value, path)
        return ValidationResult(valid=True, validator_version=self.validator_version)

    def _walk(self, value: Any, path: str) -> None:
        if hasattr(value, "model_dump"):
            value = value.model_dump(mode="json")
        elif is_dataclass(value) and not isinstance(value, type):
            value = asdict(value)
        if isinstance(value, dict):
            for key, child in value.items():
                key_text = str(key)
                self._validate_key(key_text, f"{path}.{key_text}")
                self._walk(child, f"{path}.{key_text}")
            return
        if isinstance(value, (list, tuple, set, frozenset)):
            self._validate_sequence(value, path)
            for index, child in enumerate(value):
                self._walk(child, f"{path}[{index}]")
            return
        if isinstance(value, (bytes, bytearray, memoryview)):
            raise PayloadExfiltrationException(f"Binary value blocked at {path}")
        if isinstance(value, str):
            self._validate_string_value(value, path)

    def _validate_key(self, key: str, path: str) -> None:
        normalized = normalize_key(key)
        if normalized in self.safe_keys or normalized.endswith("_hash_sha256"):
            return
        if normalized in self.forbidden_keys or self._contains_forbidden_pattern(normalized):
            raise PayloadExfiltrationException(f"Payload-like key blocked at {path}: {key}")

    def _validate_string_value(self, value: str, path: str) -> None:
        if SENSITIVE_VALUE_RE.search(value):
            raise PayloadExfiltrationException(f"Sensitive-looking value blocked at {path}")
        if LOCAL_ABSOLUTE_PATH_RE.match(value):
            raise PayloadExfiltrationException(f"Local absolute path blocked at {path}")
        if BASE64_LIKE_RE.match(value):
            raise PayloadExfiltrationException(f"Large encoded value blocked at {path}")
        if MARKDOWN_CODE_FENCE_RE.search(value):
            raise PayloadExfiltrationException(f"Markdown code fence blocked at {path}")
        if len(value) > 1024:
            raise PayloadExfiltrationException(f"Long unstructured string blocked at {path}")
        if JSON_OBJECT_RE.match(value):
            try:
                import json

                self._walk(json.loads(value), f"{path}<json>")
            except PayloadExfiltrationException:
                raise
            except Exception:
                return

    def _contains_forbidden_pattern(self, normalized: str) -> bool:
        normalized = re.sub(r"(?<!^)(?=[A-Z])", "_", normalized).lower()
        segments = set(normalized.split("_"))
        for forbidden in self.forbidden_keys:
            if forbidden in normalized:
                return True
            if forbidden in segments:
                return True
        return False

    def _validate_sequence(self, value: Any, path: str) -> None:
        sequence = list(value)
        if len(sequence) >= 8 and all(isinstance(item, int) for item in sequence):
            raise PayloadExfiltrationException(f"Integer sequence blocked at {path}")
        if len(sequence) >= 4 and all(isinstance(item, float) for item in sequence):
            raise PayloadExfiltrationException(f"Float sequence blocked at {path}")


def validate_rendered_text(text: str) -> None:
    for index, line in enumerate(text.splitlines() or [""]):
        NoPayloadValidator().validate({"rendered_markdown_segment": line}, path=f"$.rendered_markdown[{index}]")


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    validator_version: str


@dataclass(frozen=True)
class SourceUriPolicy:
    unsafe_debug: bool = False

    def strip(self, uri: str) -> str:
        parsed = urlparse(uri)
        if parsed.scheme in {"s3", "gs"} and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
        if parsed.scheme == "azure" and parsed.netloc:
            return f"azure://{parsed.netloc}"
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
        if parsed.scheme == "file":
            if self.unsafe_debug:
                return uri
            root_hash = sha256_hex(parsed.path.split("/")[1].encode("utf-8") if parsed.path else b"local")
            return f"file://{root_hash}"
        if not parsed.scheme and uri.startswith("/"):
            if self.unsafe_debug:
                return uri
            root = uri.strip("/").split("/")[0] or "local"
            return f"file://{sha256_hex(root)}"
        return uri

    def root_hash(self, uri: str) -> str:
        return sha256_hex(self.strip(uri))


def payload_policy_assertion() -> dict[str, Any]:
    return {
        "policy_name": "NO_PAYLOAD_POLICY",
        "policy_version": NO_PAYLOAD_POLICY_VERSION,
        "validator_version": NoPayloadValidator.validator_version,
        "raw_payload_absent": True,
        "model_weights_absent": True,
        TOKEN_SEQUENCES_ABSENT_KEY: True,
        "embeddings_absent": True,
        "outbound_validation_passed": True,
        "validation_timestamp": utc_now(),
    }
