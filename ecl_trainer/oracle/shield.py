from __future__ import annotations

from typing import Any

from ecl_trainer.core.policy import NoPayloadValidator
from ecl_trainer.oracle.atlas import _EclInternalCore
from ecl_trainer.oracle.domains import DomainSelectionMode, IndustryDomain
from ecl_trainer.oracle.models import (
    APPROVED_REGULATORY_TAGS,
    ShieldAction,
    ShieldCategory,
    ShieldRiskAlert,
    ShieldSeverity,
    validate_oracle_metadata,
)
from ecl_trainer.oracle.selection import resolve_domain_selection


class EclPreFlightShield:
    def __init__(
        self,
        core: _EclInternalCore | None = None,
        *,
        enabled_domains: str | list[str] | list[IndustryDomain] | None = None,
        domain_selection_mode: str | DomainSelectionMode = DomainSelectionMode.AUTO,
    ) -> None:
        self.core = core or _EclInternalCore()
        self.enabled_domains = enabled_domains
        self.domain_selection_mode = DomainSelectionMode(domain_selection_mode)

    def validate_run_manifest(self, run_metadata: dict[str, Any]) -> list[dict[str, Any]]:
        validate_oracle_metadata(run_metadata)
        selection = resolve_domain_selection(
            metadata=run_metadata,
            enabled_domains=self.enabled_domains,
            domain_selection_mode=self.domain_selection_mode,
            core=self.core,
        )
        alerts: list[ShieldRiskAlert] = []
        atlas_hash = self.core.atlas_manifest_hash()

        lineage_ids = set(run_metadata.get("ancestor_model_ids", []) or [])
        project_namespace = str(run_metadata.get("project_namespace", ""))
        if project_namespace and project_namespace in lineage_ids:
            alerts.append(
                ShieldRiskAlert(
                    check_id="global_lineage_loop",
                    severity=ShieldSeverity.CRITICAL,
                    category=ShieldCategory.MODEL_INBREEDING,
                    confidence=0.95,
                    action_required=ShieldAction.QUARANTINE,
                    remediation_steps=["rotate_lineage_source", "review_synthetic_data_origin"],
                    enabled_domains=selection.enabled_domains,
                    skipped_domains=selection.skipped_domains,
                    atlas_manifest_hash=atlas_hash,
                )
            )

        benchmark_aliases = {str(value).lower() for value in run_metadata.get("benchmark_aliases", []) or []}
        if benchmark_aliases.intersection({"mmlu", "gsm8k", "humaneval"}):
            alerts.append(
                ShieldRiskAlert(
                    check_id="global_benchmark_overlap",
                    severity=ShieldSeverity.CRITICAL,
                    category=ShieldCategory.BENCHMARK_LEAK,
                    confidence=0.9,
                    action_required=ShieldAction.QUARANTINE,
                    remediation_steps=["remove_benchmark_overlap", "regenerate_metadata_fingerprint"],
                    enabled_domains=selection.enabled_domains,
                    skipped_domains=selection.skipped_domains,
                    atlas_manifest_hash=atlas_hash,
                )
            )

        if IndustryDomain.FINANCIAL_SERVICES in selection.enabled_domains:
            invalid_tags = sorted(
                set(run_metadata.get("regulatory_framework_tags", []) or []) - APPROVED_REGULATORY_TAGS
            )
            if invalid_tags:
                alerts.append(
                    ShieldRiskAlert(
                        check_id="financial_domain_crossing_tags",
                        severity=ShieldSeverity.CRITICAL,
                        category=ShieldCategory.PROVENANCE_GAP,
                        confidence=0.88,
                        action_required=ShieldAction.QUARANTINE,
                        remediation_steps=["remove_cross_domain_regulatory_tags", "rerun_domain_clean_passport"],
                        enabled_domains=selection.enabled_domains,
                        skipped_domains=selection.skipped_domains,
                        atlas_manifest_hash=atlas_hash,
                    )
                )
            if not run_metadata.get("regulatory_framework_tags"):
                alerts.append(
                    ShieldRiskAlert(
                        check_id="financial_regulatory_tag_gap",
                        severity=ShieldSeverity.WARN,
                        category=ShieldCategory.PROVENANCE_GAP,
                        confidence=0.72,
                        action_required=ShieldAction.REVIEW,
                        remediation_steps=["add_financial_regulatory_framework_tags"],
                        enabled_domains=selection.enabled_domains,
                        skipped_domains=selection.skipped_domains,
                        atlas_manifest_hash=atlas_hash,
                    )
                )

        if not alerts:
            alerts.append(
                ShieldRiskAlert(
                    check_id="global_structural_core_pass",
                    severity=ShieldSeverity.INFO,
                    category=ShieldCategory.TRAINING_LOSS_DIVERGENCE,
                    confidence=0.99,
                    action_required=ShieldAction.ALLOW,
                    remediation_steps=[],
                    enabled_domains=selection.enabled_domains,
                    skipped_domains=selection.skipped_domains,
                    atlas_manifest_hash=atlas_hash,
                )
            )

        payload = [alert.model_dump(mode="json") for alert in alerts]
        NoPayloadValidator().validate(payload)
        return payload
