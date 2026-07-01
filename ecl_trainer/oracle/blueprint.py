from __future__ import annotations

from typing import Any

from ecl_trainer.core.policy import NoPayloadValidator
from ecl_trainer.oracle.atlas import _EclInternalCore
from ecl_trainer.oracle.domains import DomainSelectionMode, IndustryDomain
from ecl_trainer.oracle.models import OracleBlueprintResult, validate_oracle_metadata
from ecl_trainer.oracle.selection import resolve_domain_selection


class CurriculumBlueprintOracle:
    def __init__(
        self,
        *,
        core: _EclInternalCore | None = None,
        enabled_domains: str | list[str] | list[IndustryDomain] | None = None,
        domain_selection_mode: str | DomainSelectionMode = DomainSelectionMode.AUTO,
    ) -> None:
        self.core = core or _EclInternalCore()
        self.enabled_domains = enabled_domains
        self.domain_selection_mode = DomainSelectionMode(domain_selection_mode)

    def generate_step_zero_blueprint(
        self,
        dataset_fingerprints: list[dict[str, Any]],
        target_metrics: dict[str, float],
    ) -> dict[str, Any]:
        validate_oracle_metadata(dataset_fingerprints)
        validate_oracle_metadata(target_metrics)
        metadata = dataset_fingerprints[0] if dataset_fingerprints else {}
        selection = resolve_domain_selection(
            metadata=metadata,
            enabled_domains=self.enabled_domains,
            domain_selection_mode=self.domain_selection_mode,
            core=self.core,
        )
        domain_patterns = self.core.domain_patterns(selection.enabled_domains)
        global_patterns = self.core.global_patterns()
        mixture = {row["target_key"]: row["target_value"] for row in domain_patterns if row.get("target_key")}
        if not mixture:
            mixture = {"structural_core_target": 1.0}
        divergence = max([row["risk_weight"] for row in global_patterns + domain_patterns] or [0.0])
        compatibility = {domain.value: 0.92 for domain in selection.enabled_domains}
        result = OracleBlueprintResult(
            target_mixture_boundaries=mixture,
            recommended_pruning_criteria=["metadata_only_outlier_review"] if divergence >= 0.75 else [],
            estimated_compute_optimization_gain=0.18 if selection.enabled_domains else 0.08,
            compliance_compatibility_scores=compatibility,
            divergence_risk_coefficient=divergence,
            enabled_domains=selection.enabled_domains,
            skipped_domains=selection.skipped_domains,
            domain_selection_mode=selection.domain_selection_mode,
            atlas_manifest_hash=self.core.atlas_manifest_hash(),
        )
        payload = result.model_dump(mode="json")
        NoPayloadValidator().validate(payload)
        return payload
