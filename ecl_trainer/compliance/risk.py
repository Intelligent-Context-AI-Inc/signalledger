from __future__ import annotations

from ecl_trainer.compliance.registries import BenchmarkRegistry, ModelLineageRegistry
from ecl_trainer.core.models import ModelLineageRecord, RiskFlag, RiskSummary


class RiskGatekeeper:
    def __init__(
        self,
        *,
        benchmark_registry: BenchmarkRegistry | None = None,
        lineage_registry: ModelLineageRegistry | None = None,
    ) -> None:
        self.benchmark_registry = benchmark_registry or BenchmarkRegistry()
        self.lineage_registry = lineage_registry or ModelLineageRegistry()

    def evaluate(self, metadata: dict, *, model_id: str | None = None) -> RiskSummary:
        flags = [
            *self.detect_benchmark_contamination(metadata),
            *self.detect_model_inbreeding(metadata, model_id=model_id),
        ]
        status = "high_risk" if any(flag.severity == "high" for flag in flags) else ("warn" if flags else "pass")
        return RiskSummary(status=status, risk_flags=flags)

    def detect_benchmark_contamination(self, metadata: dict) -> list[RiskFlag]:
        matches = self.benchmark_registry.matches(metadata)
        if not matches:
            return []
        high_confidence_match = "source_root_hash" in matches or "benchmark_alias" in matches
        return [
            RiskFlag(
                risk_type="benchmark_contamination",
                severity="high" if high_confidence_match else "medium",
                confidence=0.85 if high_confidence_match else 0.65,
                matching_metadata_categories=matches,
                remediation="Review benchmark separation and document exclusion evidence.",
            )
        ]

    def detect_model_inbreeding(self, metadata: dict, *, model_id: str | None = None) -> list[RiskFlag]:
        origin_model_id = metadata.get("origin_model_id") or metadata.get("synthetic_data_origin_model_id")
        if not origin_model_id or not model_id:
            return []
        current = self.lineage_registry.records.get(model_id) or ModelLineageRecord(model_id=model_id)
        ancestors = set(current.ancestor_model_ids)
        if current.parent_model_id:
            ancestors.add(current.parent_model_id)
        same_family = False
        origin = self.lineage_registry.records.get(str(origin_model_id))
        if origin and current.base_model_family and origin.base_model_family == current.base_model_family:
            same_family = True
        if origin_model_id == model_id or origin_model_id in ancestors or same_family:
            return [
                RiskFlag(
                    risk_type="model_lineage_feedback_loop",
                    severity="high",
                    confidence=0.8,
                    matching_metadata_categories=["origin_model_id", "model_lineage"],
                    remediation="Add external grounding evidence or exclude same-lineage synthetic sources.",
                )
            ]
        return []
