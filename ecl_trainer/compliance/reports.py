from __future__ import annotations

from pathlib import Path
from typing import Any

from ecl_trainer.compliance.risk import RiskGatekeeper
from ecl_trainer.core.ledger import HashChainVerifier, LocalEventReplay
from ecl_trainer.core.models import ReportProfile
from ecl_trainer.core.policy import NoPayloadValidator, validate_rendered_text
from ecl_trainer.core.serialization import canonical_sha256


class CompliancePassportGenerator:
    def __init__(self, ledger_path: str | Path, *, risk_gatekeeper: RiskGatekeeper | None = None) -> None:
        self.ledger_path = Path(ledger_path)
        self.risk_gatekeeper = risk_gatekeeper or RiskGatekeeper()

    def generate(
        self,
        *,
        profile: ReportProfile = ReportProfile.INTERNAL_AUDIT,
        project_namespace: str | None = None,
    ) -> dict[str, Any]:
        events = list(LocalEventReplay(self.ledger_path).iter_events(project_namespace=project_namespace))
        verification = HashChainVerifier(self.ledger_path).verify()
        dataset_events = [event for event in events if event.get("event_type") == "data_ingest"]
        risk_flags = []
        for event in dataset_events:
            risk_flags.extend(self.risk_gatekeeper.evaluate(event).risk_flags)
        report = {
            "report_profile": profile.value,
            "project_namespace": project_namespace or "all",
            "event_count": len(events),
            "dataset_fingerprints": [event.get("content_hash_sha256") for event in dataset_events],
            "source_root_hashes": [event.get("source_system_root_hash_sha256") for event in dataset_events],
            "schema_hashes": [event.get("schema_hash_sha256") for event in dataset_events],
            "license_matrix": [event.get("license_matrix", []) for event in dataset_events],
            "provenance": [event.get("provenance", {}) for event in dataset_events],
            "synthetic_data_indicators": [
                event.get("provenance", {}).get("synthetic_data") for event in dataset_events
            ],
            "mutation_trail_hash": canonical_sha256([event.get("mutation_trail", []) for event in dataset_events]),
            "risk_flags": [flag.model_dump(mode="json") for flag in risk_flags],
            "hash_chain_verification": verification,
            "regulatory_positioning": self._profile_positioning(profile),
        }
        if profile == ReportProfile.AB2013_PUBLIC_SUMMARY:
            report.pop("provenance", None)
            report["public_summary"] = "High-level training-data transparency evidence artifact."
        if profile == ReportProfile.LEGAL_EXECUTIVE_SUMMARY:
            report["executive_summary"] = "Metadata-only evidence summary for model release review."
        NoPayloadValidator().validate(report)
        return report

    def render_markdown(self, report: dict[str, Any]) -> str:
        NoPayloadValidator().validate(report)
        lines = [
            "# ECL Training Passport",
            f"- Profile: `{report['report_profile']}`",
            f"- Events: `{report['event_count']}`",
            f"- Hash chain: `{'valid' if report['hash_chain_verification']['valid'] else 'invalid'}`",
            f"- Risk flags: `{len(report['risk_flags'])}`",
        ]
        text = "\n".join(lines) + "\n"
        validate_rendered_text(text)
        return text

    def _profile_positioning(self, profile: ReportProfile) -> str:
        if profile == ReportProfile.AB2013_PUBLIC_SUMMARY:
            return "Supports California AB 2013 training-data transparency documentation."
        if profile == ReportProfile.EU_AI_ACT_TECHNICAL_DOC:
            return "Supports EU AI Act technical documentation workflows."
        return "Supports metadata-only training-data governance review."
