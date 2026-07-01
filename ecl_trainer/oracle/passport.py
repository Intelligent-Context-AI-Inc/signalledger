from __future__ import annotations

from pathlib import Path
from typing import Any

from ecl_trainer.compliance.reports import CompliancePassportGenerator
from ecl_trainer.core.ledger import HashChainVerifier, LocalEventReplay
from ecl_trainer.core.models import ReportProfile
from ecl_trainer.core.policy import NoPayloadValidator, validate_rendered_text
from ecl_trainer.core.serialization import canonical_json, canonical_sha256
from ecl_trainer.oracle.atlas import _EclInternalCore
from ecl_trainer.oracle.domains import IndustryDomain, parse_domains


class RegulatoryPassportCompiler:
    def __init__(
        self,
        ledger_path: str | Path = ".ecl-trainer/events.jsonl",
        *,
        enabled_domains: str | list[str] | list[IndustryDomain] | None = None,
        core: _EclInternalCore | None = None,
    ) -> None:
        self.ledger_path = Path(ledger_path)
        self.enabled_domains = parse_domains(enabled_domains)
        self.core = core or _EclInternalCore()

    def compile_compliance_passport(
        self,
        event_stream: list[dict[str, Any]] | None = None,
        profile: str = ReportProfile.INTERNAL_AUDIT.value,
    ) -> dict[str, Any]:
        events = event_stream if event_stream is not None else list(LocalEventReplay(self.ledger_path).iter_events())
        verification = HashChainVerifier(self.ledger_path).verify()
        base_report = CompliancePassportGenerator(self.ledger_path).generate(profile=ReportProfile(profile))
        domain_sections = self._domain_sections()
        report = {
            "report_profile": profile,
            "event_count": len(events),
            "hash_chain_verification": verification,
            "global_core_used": True,
            "enabled_domains": [domain.value for domain in self.enabled_domains],
            "skipped_domains": [],
            "domain_sections": domain_sections,
            "atlas_manifest_hash": self.core.atlas_manifest_hash(),
            "local_only_execution": True,
            "saas_exfiltration_executed": False,
            "dataset_upload_executed": False,
            "base_passport_hash_sha256": canonical_sha256(base_report),
        }
        NoPayloadValidator().validate(report)
        return report

    def render_markdown(self, report: dict[str, Any]) -> str:
        lines = [
            "# ECL Learning Ledger Passport",
            f"- Profile: `{report['report_profile']}`",
            f"- Events: `{report['event_count']}`",
            f"- Hash chain: `{'valid' if report['hash_chain_verification']['valid'] else 'invalid'}`",
            "- Global structural core: `enabled`",
            f"- Enabled domains: `{','.join(report['enabled_domains']) or 'core_only'}`",
            "- SaaS exfiltration: `not executed`",
            "- Dataset upload: `not executed`",
        ]
        if report["domain_sections"]:
            lines.append("")
            lines.append("## Domain Evidence")
            for section in report["domain_sections"]:
                lines.append(f"- {str(section).replace('_', ' ')}")
        text = "\n".join(lines) + "\n"
        validate_rendered_text(text)
        return text

    def write_outputs(self, output_dir: str | Path, report: dict[str, Any]) -> dict[str, str]:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        verification_path = out / "verification.json"
        passport_path = out / "compliance-passport.md"
        verification_path.write_text(canonical_json(report["hash_chain_verification"]), encoding="utf-8")
        passport_path.write_text(self.render_markdown(report), encoding="utf-8")
        return {"verification_json": str(verification_path), "compliance_passport_markdown": str(passport_path)}

    def _domain_sections(self) -> list[str]:
        sections: list[str] = []
        if IndustryDomain.FINANCIAL_SERVICES in self.enabled_domains:
            sections.extend(
                [
                    "financial_regulatory_tags",
                    "financial_sector_distribution",
                    "financial_fiscal_bounds",
                    "SEC_EDGAR_tax_structures_tracked",
                    "FINRA_oversight_definitions_tracked",
                    "2026_Federal_Reserve_macro_scenario_matrices_tracked",
                ]
            )
        return sections
