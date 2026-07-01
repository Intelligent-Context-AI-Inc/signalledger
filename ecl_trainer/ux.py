from __future__ import annotations

from pathlib import Path
from typing import Any

from ecl_trainer.core.ledger import HashChainVerifier
from ecl_trainer.core.policy import NoPayloadValidator, sha256_hex, validate_rendered_text
from ecl_trainer.core.serialization import canonical_json, canonical_sha256
from ecl_trainer.oracle.domains import TOP_20_DOMAINS


class GitHubActionDoctor:
    def inspect(
        self,
        *,
        repository_root: str | Path = ".",
        workflow_path: str | Path = ".github/workflows/ecl-trainer.yml",
        manifest_path: str | Path = "ecl-trainer.manifest.json",
        reports_dir: str | Path = ".ecl-trainer/reports",
    ) -> dict[str, Any]:
        root = Path(repository_root)
        workflow = root / workflow_path
        manifest = root / manifest_path
        reports = root / reports_dir
        checks = [
            self._check_file("workflow_present", workflow, "add_ecl_trainer_workflow"),
            self._check_file("manifest_present", manifest, "add_metadata_manifest"),
            self._check_file("risk_report_present", reports / "risk-report.md", "run_first_scan"),
            self._check_file("passport_present", reports / "compliance-passport.md", "run_first_scan"),
            self._check_file("verification_present", reports / "verification.json", "run_first_scan"),
            self._check_file("pr_comment_present", reports / "pr-comment.md", "enable_pr_comment_or_run_scan"),
        ]
        workflow_text = workflow.read_text(encoding="utf-8") if workflow.exists() else ""
        checks.extend(
            [
                self._check_text(
                    "workflow_has_read_permission",
                    workflow_text,
                    "contents:",
                    "add_contents_read_permission",
                ),
                self._check_text(
                    "workflow_can_comment",
                    workflow_text,
                    "issues:",
                    "add_issues_write_permission_for_pr_comments",
                ),
                self._check_text(
                    "workflow_uses_report_only_first",
                    workflow_text,
                    "risk_policy: report_only",
                    "start_with_report_only_policy",
                ),
            ]
        )
        pass_count = sum(1 for check in checks if check["status"] == "pass")
        result = {
            "doctor_profile": "github_action_first_run",
            "check_count": len(checks),
            "pass_count": pass_count,
            "status": "pass" if pass_count == len(checks) else "action_required",
            "checks": checks,
            "next_steps": sorted({check["remediation"] for check in checks if check["status"] != "pass"}),
        }
        result["doctor_report_hash_sha256"] = canonical_sha256(result)
        NoPayloadValidator().validate(result)
        return result

    def _check_file(self, check_id: str, path: Path, remediation: str) -> dict[str, str]:
        return {
            "check_id": check_id,
            "status": "pass" if path.exists() else "missing",
            "remediation": "none" if path.exists() else remediation,
            "path_hash_sha256": sha256_hex(str(path)),
        }

    def _check_text(self, check_id: str, text: str, needle: str, remediation: str) -> dict[str, str]:
        passed = bool(text and needle in text)
        return {
            "check_id": check_id,
            "status": "pass" if passed else "missing",
            "remediation": "none" if passed else remediation,
        }


class AtlasPackStatusReporter:
    def status(self) -> dict[str, Any]:
        priority = {
            "financial_services": "active_seed",
            "healthcare_clinical": "priority_alpha",
            "legal_regulatory": "priority_alpha",
            "it_software": "priority_alpha",
            "pharma_biotech": "priority_alpha",
        }
        rows = []
        for domain in TOP_20_DOMAINS:
            maturity = priority.get(domain.value, "baseline_registered")
            rows.append(
                {
                    "domain_id": domain.value,
                    "pack_maturity": maturity,
                    "public_source_family_count": 6 if maturity in {"active_seed", "priority_alpha"} else 4,
                    "private_pack_ready": maturity == "active_seed",
                    "next_collection_step": self._next_step(domain.value, maturity),
                }
            )
        result = {
            "atlas_pack_status_version": "option_b_alpha",
            "domain_count": len(rows),
            "active_seed_count": sum(1 for row in rows if row["pack_maturity"] == "active_seed"),
            "priority_alpha_count": sum(1 for row in rows if row["pack_maturity"] == "priority_alpha"),
            "domains": rows,
        }
        result["atlas_pack_status_hash_sha256"] = canonical_sha256(result)
        NoPayloadValidator().validate(result)
        return result

    def validate_source(self, source: dict[str, Any]) -> dict[str, Any]:
        NoPayloadValidator().validate(source)
        required = {
            "domain_id",
            "source_family",
            "source_reference_hash_sha256",
            "metadata_fields_available",
            "license_descriptor",
        }
        missing = sorted(required - set(source))
        result = {
            "validation_profile": "atlas_pack_source",
            "status": "pass" if not missing else "missing_required_metadata",
            "missing_fields": missing,
            "source_hash_sha256": canonical_sha256(source),
            "payload_policy": "passed",
        }
        NoPayloadValidator().validate(result)
        return result

    def _next_step(self, domain_id: str, maturity: str) -> str:
        if domain_id == "financial_services":
            return "deepen_negative_eval_and_lineage_signatures"
        if maturity == "priority_alpha":
            return "populate_metadata_only_public_seed_rows"
        return "promote_from_source_catalog_to_priority_alpha"


class ArtifactViewer:
    def build(
        self,
        *,
        reports_dir: str | Path = ".ecl-trainer/reports",
        ledger_path: str | Path = ".ecl-trainer/events.jsonl",
        output: str | Path = ".ecl-trainer/reports/artifact-viewer.html",
    ) -> dict[str, Any]:
        reports = Path(reports_dir)
        ledger = Path(ledger_path)
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        artifacts = {
            "risk_report": reports / "risk-report.md",
            "compliance_passport": reports / "compliance-passport.md",
            "verification": reports / "verification.json",
            "pr_comment": reports / "pr-comment.md",
            "manifest": reports / "manifest.json",
            "ledger": ledger,
        }
        summaries = {
            name: self._safe_preview(path)
            for name, path in artifacts.items()
            if path.exists()
        }
        verification = HashChainVerifier(ledger).verify() if ledger.exists() else {"valid": False, "event_count": 0}
        html = self._render_html(summaries=summaries, verification=verification)
        validate_rendered_text(html)
        output_path.write_text(html, encoding="utf-8")
        result = {
            "artifact_viewer": str(output_path),
            "artifact_count": len(summaries),
            "hash_chain_valid": bool(verification.get("valid")),
            "viewer_hash_sha256": sha256_hex(html),
        }
        NoPayloadValidator().validate(result)
        return result

    def _safe_preview(self, path: Path) -> dict[str, Any]:
        text = path.read_text(encoding="utf-8")
        preview = text[:900]
        validate_rendered_text(preview)
        return {
            "filename": path.name,
            "size_bytes": path.stat().st_size,
            "file_hash_sha256": sha256_hex(path.read_bytes()),
            "preview": preview,
        }

    def _render_html(self, *, summaries: dict[str, dict[str, Any]], verification: dict[str, Any]) -> str:
        sections = []
        for name, summary in summaries.items():
            preview = (
                summary["preview"]
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            sections.append(
                "\n".join(
                    [
                        f"<section><h2>{name}</h2>",
                        f"<p><strong>File:</strong> {summary['filename']}</p>",
                        f"<p><strong>SHA-256:</strong> {summary['file_hash_sha256']}</p>",
                        f"<pre>{preview}</pre></section>",
                    ]
                )
            )
        valid = "valid" if verification.get("valid") else "not_valid"
        return "\n".join(
            [
                "<!doctype html>",
                "<html><head><meta charset=\"utf-8\"><title>ECL Artifact Viewer</title>",
                "<style>body{font-family:Arial,sans-serif;margin:32px;line-height:1.45;color:#1f2937}"
                "section{border:1px solid #d1d5db;padding:16px;margin:16px 0;border-radius:6px}"
                "pre{white-space:pre-wrap;background:#f3f4f6;padding:12px;overflow:auto}"
                ".status{font-weight:700}</style></head><body>",
                "<h1>ECL Local Artifact Viewer</h1>",
                f"<p class=\"status\">Ledger verification: {valid}</p>",
                f"<p>Ledger events: {verification.get('event_count', 0)}</p>",
                *sections,
                "</body></html>",
            ]
        )


def write_trial_bundle(output_dir: str | Path = "trial_bundles/ecl_learning_ledger") -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    files = {
        "README.md": "# ECL Learning Ledger Trial Bundle\n\nRun one metadata-only PR scan in about 15 minutes.\n",
        "ecl-trainer.manifest.json": canonical_json(
            {
                "project_namespace": "trial-org/financial-model",
                "domain": "financial_services",
                "dataset_identifier_hash_sha256": sha256_hex("trial-dataset"),
                "schema_hash_sha256": sha256_hex("trial-schema"),
                "benchmark_aliases": ["mmlu_finance"],
                "payload_policy": {"raw_payload_absent": True},
            }
        ),
        "walkthrough.md": "\n".join(
            [
                "# 15-Minute Trial Walkthrough",
                "",
                "1. Copy the GitHub workflow from `docs/ecl_learning_ledger/GITHUB_ACTION_FIRST_RUN_UX.md`.",
                "2. Commit `ecl-trainer.manifest.json`.",
                "3. Open a PR and wait for the ECL comment.",
                "4. Download `.ecl-trainer/reports` artifacts.",
                "5. Review `verification.json` and `compliance-passport.md`.",
                "",
            ]
        ),
    }
    for filename, content in files.items():
        (out / filename).write_text(content, encoding="utf-8")
    manifest = {
        "trial_bundle_dir": str(out),
        "file_count": len(files),
        "bundle_hash_sha256": canonical_sha256({name: sha256_hex(content) for name, content in files.items()}),
    }
    NoPayloadValidator().validate(manifest)
    return manifest
