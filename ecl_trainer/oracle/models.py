from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Any, Literal

from pydantic import Field, model_validator

from ecl_trainer.core.exceptions import SovereignDataExfiltrationException
from ecl_trainer.core.models import FrozenModel, PayloadPolicyAssertion
from ecl_trainer.core.policy import HEX_SHA256_RE, NoPayloadValidator
from ecl_trainer.oracle.domains import DomainSelectionMode, IndustryDomain


class ShieldSeverity(StrEnum):
    INFO = "INFO"
    WARN = "WARN"
    CRITICAL = "CRITICAL"


class ShieldCategory(StrEnum):
    MODEL_INBREEDING = "MODEL_INBREEDING"
    BENCHMARK_LEAK = "BENCHMARK_LEAK"
    TRAINING_LOSS_DIVERGENCE = "TRAINING_LOSS_DIVERGENCE"
    LICENSE_GAP = "LICENSE_GAP"
    PROVENANCE_GAP = "PROVENANCE_GAP"


class ShieldAction(StrEnum):
    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    QUARANTINE = "QUARANTINE"


class OracleBlueprintResult(FrozenModel):
    target_mixture_boundaries: dict[str, float] = Field(default_factory=dict)
    recommended_pruning_criteria: list[str] = Field(default_factory=list)
    estimated_compute_optimization_gain: float = 0.0
    compliance_compatibility_scores: dict[str, float] = Field(default_factory=dict)
    divergence_risk_coefficient: float = 0.0
    global_core_used: Literal[True] = True
    enabled_domains: list[IndustryDomain] = Field(default_factory=list)
    skipped_domains: list[IndustryDomain] = Field(default_factory=list)
    domain_selection_mode: DomainSelectionMode = DomainSelectionMode.AUTO
    atlas_manifest_hash: str
    payload_policy: PayloadPolicyAssertion = Field(default_factory=PayloadPolicyAssertion)


class ShieldRiskAlert(FrozenModel):
    check_id: str
    severity: ShieldSeverity
    category: ShieldCategory
    confidence: float
    action_required: ShieldAction
    remediation_steps: list[str] = Field(default_factory=list)
    global_core_used: Literal[True] = True
    enabled_domains: list[IndustryDomain] = Field(default_factory=list)
    skipped_domains: list[IndustryDomain] = Field(default_factory=list)
    atlas_manifest_hash: str


APPROVED_REGULATORY_TAGS = frozenset(
    {
        "SEC_2026_COMPLIANCE",
        "FINRA_AMENDMENT_2026",
        "FRB_STRESS_TEST",
        "SOX_CONTROL",
        "BASEL_RISK",
        "AML_KYC",
    }
)

APPROVED_MARKET_SECTORS = frozenset(
    {
        "equities",
        "fixed_income",
        "credit",
        "derivatives",
        "wealth",
        "payments",
        "insurance",
        "risk",
    }
)


class FinancialIngestPayloadModel(FrozenModel):
    project_namespace: str
    dataset_identifier_hash_sha256: str
    schema_hash_sha256: str
    regulatory_framework_tags: list[str] = Field(default_factory=list)
    market_sector_distribution: dict[str, float] = Field(default_factory=dict)
    temporal_fiscal_bounds: dict[str, date]
    entity_coverage_density: dict[str, float] = Field(default_factory=dict)
    industry_domain: IndustryDomain = IndustryDomain.FINANCIAL_SERVICES

    @model_validator(mode="before")
    @classmethod
    def reject_payload_like_values(cls, data: Any) -> Any:
        NoPayloadValidator().validate(data)
        cls._walk_for_long_text(data)
        return data

    @model_validator(mode="after")
    def validate_financial_shape(self):
        invalid_tags = sorted(set(self.regulatory_framework_tags) - APPROVED_REGULATORY_TAGS)
        if invalid_tags:
            raise ValueError(f"Unsupported regulatory tags: {','.join(invalid_tags)}")
        invalid_sectors = sorted(set(self.market_sector_distribution) - APPROVED_MARKET_SECTORS)
        if invalid_sectors:
            raise ValueError(f"Unsupported market sectors: {','.join(invalid_sectors)}")
        if abs(sum(self.market_sector_distribution.values()) - 1.0) > 0.02:
            raise ValueError("market_sector_distribution must sum to 1.0")
        if self.temporal_fiscal_bounds["start"] > self.temporal_fiscal_bounds["end"]:
            raise ValueError("temporal_fiscal_bounds start must be before end")
        return self

    @classmethod
    def _walk_for_long_text(cls, value: Any) -> None:
        if isinstance(value, dict):
            for child in value.values():
                cls._walk_for_long_text(child)
            return
        if isinstance(value, list):
            for child in value:
                cls._walk_for_long_text(child)
            return
        if isinstance(value, str) and len(value) > 50 and not HEX_SHA256_RE.match(value):
            raise SovereignDataExfiltrationException("Oracle metadata rejected long non-hash string")


def validate_oracle_metadata(value: Any) -> Any:
    try:
        NoPayloadValidator().validate(value)
        FinancialIngestPayloadModel._walk_for_long_text(value)
    except SovereignDataExfiltrationException:
        raise
    except Exception as exc:
        raise SovereignDataExfiltrationException(str(exc)) from exc
    return value
