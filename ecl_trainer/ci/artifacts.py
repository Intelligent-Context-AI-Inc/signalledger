from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from ecl_trainer.ci.github_action import GitHubActionRunner
from ecl_trainer.ci.reporting import CIReportRenderer
from ecl_trainer.ci.scanner import CIScanner
from ecl_trainer.compliance.reports import CompliancePassportGenerator
from ecl_trainer.core.ledger import AppendOnlyEventLog, HashChainVerifier
from ecl_trainer.core.models import (
    CompliancePassportEvent,
    CurriculumBlueprintEvent,
    DiffFreePREvidenceEvent,
    LocalArtifactExportEvent,
    OracleShieldRunEvent,
    ReportProfile,
)
from ecl_trainer.core.policy import NoPayloadValidator, sha256_hex, validate_rendered_text
from ecl_trainer.core.serialization import canonical_json, canonical_sha256
from ecl_trainer.governance import RiskGateDecisionRecorder, RiskScoreProcessor
from ecl_trainer.lifecycle.freshness import AtlasFreshnessValidator
from ecl_trainer.mlops_pack import MLOpsGovernancePackBuilder
from ecl_trainer.oracle.atlas import _EclInternalCore
from ecl_trainer.oracle.blueprint import CurriculumBlueprintOracle
from ecl_trainer.oracle.passport import RegulatoryPassportCompiler
from ecl_trainer.oracle.shield import EclPreFlightShield
from ecl_trainer.security.supply_chain import SupplyChainEvidenceGenerator

PR_COMMENT_MARKER = "<!-- ecl-trainer:local-risk-report -->"
MANIFEST_NAMES = (
    "ecl-trainer.manifest.json",
    "ecl-trainer.manifest.yaml",
    "ecl-trainer.manifest.yml",
)


class LocalCIArtifactGenerator:
    def generate(
        self,
        *,
        project_namespace: str,
        ledger_path: str | Path,
        output_dir: str | Path,
        changed_only: bool = True,
        risk_policy: str = "report_only",
        enabled_domains: str = "",
        domain_selection_mode: str = "auto",
        ignore_staleness: bool = False,
        generate_mlops_pack: bool = True,
        previous_pack: str | Path | None = None,
        catalog_check_json: str | Path | None = None,
    ) -> dict[str, Any]:
        ledger = Path(ledger_path)
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        report = CIScanner(
            repository_root=".",
            ledger_path=ledger,
            project_namespace=project_namespace,
        ).scan(changed_only=changed_only)
        report["risk_policy"] = risk_policy
        report["should_fail"] = GitHubActionRunner().should_fail(report, risk_policy)
        NoPayloadValidator().validate(report)

        oracle = self._oracle_outputs(
            ledger_path=ledger,
            project_namespace=project_namespace,
            output_dir=out,
            enabled_domains=enabled_domains,
            domain_selection_mode=domain_selection_mode,
        )
        if oracle["oracle_status"] == "completed":
            passport_compiler = RegulatoryPassportCompiler(
                ledger_path=ledger,
                enabled_domains=oracle.get("enabled_domains", []),
            )
            passport = passport_compiler.compile_compliance_passport(profile=ReportProfile.INTERNAL_AUDIT.value)
            passport_markdown = passport_compiler.render_markdown(passport)
        else:
            passport = CompliancePassportGenerator(ledger).generate(
                profile=ReportProfile.INTERNAL_AUDIT,
                project_namespace=project_namespace,
            )
            passport_markdown = CompliancePassportGenerator(ledger).render_markdown(passport)
        self._append_passport_event(
            ledger_path=ledger,
            project_namespace=project_namespace,
            passport=passport,
            passport_markdown=passport_markdown,
            enabled_domains=oracle.get("enabled_domains", []),
        )
        scorecard = RiskScoreProcessor().score_events(list(AppendOnlyEventLog(ledger).replay()))
        risk_gate_event = RiskGateDecisionRecorder().append_decision(
            ledger_path=ledger,
            project_namespace=project_namespace,
            scorecard=scorecard,
        )
        lifecycle = AtlasFreshnessValidator().evaluate_atlas_lifecycle(
            datetime.now(UTC),
            ignore_staleness=ignore_staleness,
        )
        supply_chain_paths = SupplyChainEvidenceGenerator(repository_root=".").write_outputs(out / "supply-chain")

        renderer = CIReportRenderer()
        risk_markdown = self.render_risk_report(report, oracle, scorecard)

        paths = {
            "risk_report_markdown": out / "risk-report.md",
            "risk_report_json": out / "risk-report.json",
            "compliance_passport_markdown": out / "compliance-passport.md",
            "compliance_passport_json": out / "compliance-passport.json",
            "pr_comment_markdown": out / "pr-comment.md",
            "verification_json": out / "verification.json",
            "lifecycle_report_json": out / "lifecycle-report.json",
            "diff_free_pr_proof_json": out / "diff-free-pr-proof.json",
        }
        paths["risk_report_markdown"].write_text(risk_markdown, encoding="utf-8")
        paths["risk_report_json"].write_text(renderer.render_json(report), encoding="utf-8")
        paths["compliance_passport_markdown"].write_text(passport_markdown, encoding="utf-8")
        paths["compliance_passport_json"].write_text(canonical_json(passport), encoding="utf-8")
        paths["lifecycle_report_json"].write_text(canonical_json(lifecycle), encoding="utf-8")
        diff_free_proof = self._build_diff_free_pr_proof(report)
        paths["diff_free_pr_proof_json"].write_text(canonical_json(diff_free_proof), encoding="utf-8")
        diff_proof_event = self._append_diff_free_pr_event(
            ledger_path=ledger,
            project_namespace=project_namespace,
            proof=diff_free_proof,
        )
        if oracle["oracle_status"] == "completed":
            paths["oracle_alerts_json"] = out / "oracle-alerts.json"
            paths["oracle_blueprint_json"] = out / "oracle-blueprint.json"
            paths["oracle_alerts_json"].write_text(canonical_json(oracle["alerts"]), encoding="utf-8")
            paths["oracle_blueprint_json"].write_text(canonical_json(oracle["blueprint"]), encoding="utf-8")
        paths.update(
            {
                f"supply_chain_{name}": out / "supply-chain" / filename
                for name, filename in supply_chain_paths.items()
            }
        )
        verification_for_pack = HashChainVerifier(ledger).verify()
        paths["verification_json"].write_text(canonical_json(verification_for_pack), encoding="utf-8")
        mlops_pack: dict[str, Any] | None = None
        if generate_mlops_pack:
            mlops_result = MLOpsGovernancePackBuilder().build(
                reports_dir=out,
                ledger_path=ledger,
                output_dir=out,
                previous_pack=previous_pack,
                catalog_check_json=catalog_check_json,
            )
            mlops_pack = mlops_result["pack"]
            paths.update(mlops_result["paths"])

        comment_markdown = self.render_pr_comment(
            risk_markdown=risk_markdown,
            passport_markdown=passport_markdown,
            verification=verification_for_pack,
            oracle=oracle,
            supply_chain=supply_chain_paths,
            lifecycle=lifecycle,
            mlops_pack=mlops_pack,
        )
        paths["pr_comment_markdown"].write_text(comment_markdown, encoding="utf-8")
        self._append_artifact_export_event(
            ledger_path=ledger,
            project_namespace=project_namespace,
            paths={name: path for name, path in paths.items() if name != "verification_json"},
            verification=verification_for_pack,
        )
        verification = HashChainVerifier(ledger).verify()
        paths["verification_json"].write_text(canonical_json(verification), encoding="utf-8")

        manifest = {
            "project_namespace": project_namespace,
            "risk_policy": risk_policy,
            "output_files": {name: str(path) for name, path in paths.items()},
            "ledger": str(ledger),
            "mode": "local-only",
            "payload_policy": "passed",
            "oracle_status": oracle["oracle_status"],
            "enabled_domains": oracle.get("enabled_domains", []),
            "skipped_domains": oracle.get("skipped_domains", []),
            "lifecycle_status": lifecycle["lifecycle_status"],
            "ignore_staleness": ignore_staleness,
            "supply_chain_evidence": "generated",
            "ledger_event_count": verification["event_count"],
            "risk_gate_status": scorecard["risk_gate_status"],
            "risk_scorecard_hash_sha256": canonical_sha256(scorecard),
            "risk_gate_event_hash_sha256": risk_gate_event["event_hash_sha256"],
            "diff_free_pr_event_hash_sha256": diff_proof_event["event_hash_sha256"],
            "mlops_pack_status": "generated" if mlops_pack else "not_generated",
            "mlops_readiness_status": mlops_pack["readiness_status"] if mlops_pack else "not_generated",
            "mlops_release_readiness_score": mlops_pack["release_readiness_score"] if mlops_pack else 0,
        }
        manifest["should_fail"] = GitHubActionRunner().should_fail(manifest, risk_policy)
        NoPayloadValidator().validate(manifest)
        (out / "manifest.json").write_text(canonical_json(manifest), encoding="utf-8")
        return manifest

    def render_pr_comment(
        self,
        *,
        risk_markdown: str,
        passport_markdown: str,
        verification: dict[str, Any],
        oracle: dict[str, Any] | None = None,
        supply_chain: dict[str, str] | None = None,
        lifecycle: dict[str, Any] | None = None,
        mlops_pack: dict[str, Any] | None = None,
    ) -> str:
        oracle = oracle or {"oracle_status": "skipped_no_manifest"}
        supply_chain = supply_chain or {}
        lifecycle_block = (
            AtlasFreshnessValidator().generate_pr_comment_block(lifecycle)
            if lifecycle
            else "### Atlas Lifecycle\n- Status: `UNKNOWN`"
        )
        oracle_lines = [
            "### Intelligent Context Atlas",
            f"- Oracle status: `{oracle['oracle_status']}`",
            f"- Enabled domains: `{','.join(oracle.get('enabled_domains', [])) or 'core_only'}`",
            f"- Skipped domains: `{','.join(oracle.get('skipped_domains', [])) or 'none'}`",
            f"- Atlas source records: `{oracle.get('atlas_source_record_count', 0)}`",
            f"- Atlas seeded domains: `{oracle.get('atlas_seeded_domain_count', 0)}`",
            "",
        ]
        mlops_lines = ["### MLOps Governance Pack", "- Status: `not_generated`", ""]
        if mlops_pack:
            mlops_lines = [
                "### MLOps Governance Pack",
                f"- Readiness: `{mlops_pack['readiness_status']}`",
                f"- Release readiness score: `{mlops_pack['release_readiness_score']}`",
                f"- Catalog gap count: `{mlops_pack['catalog_gap_count']}`",
                f"- Drift trend: `{mlops_pack.get('catalog_drift_snapshot', {}).get('trend', 'unchanged')}`",
                "",
            ]
        body = "\n".join(
            [
                PR_COMMENT_MARKER,
                risk_markdown.rstrip(),
                "",
                "### Local Compliance Passport",
                passport_markdown.rstrip(),
                "",
                "### Local Evidence",
                "- SaaS account: `not required`",
                "- Dataset upload: `not performed`",
                "- Payload policy: `passed`",
                f"- Ledger verification: `{'valid' if verification.get('valid') else 'invalid'}`",
                f"- Supply-chain evidence: `{'generated' if supply_chain else 'not_generated'}`",
                "",
                *oracle_lines,
                lifecycle_block,
                "",
                *mlops_lines,
            ]
        )
        self._validate_rendered_markdown(body)
        return body

    def render_risk_report(
        self,
        report: dict[str, Any],
        oracle: dict[str, Any] | None = None,
        scorecard: dict[str, Any] | None = None,
    ) -> str:
        oracle = oracle or {"oracle_status": "skipped_no_manifest"}
        scorecard = scorecard or RiskScoreProcessor().score_events([])
        base = CIReportRenderer().render_markdown(report).rstrip()
        lines = [base]
        lines.extend(
            [
                "",
                "## Risk Scorecard",
                f"- Gate: `{scorecard['risk_gate_status']}`",
                f"- Training data risk: `{scorecard['training_data_risk_score']}`",
                f"- Benchmark contamination: `{scorecard['benchmark_contamination_score']}`",
                f"- Lineage loop: `{scorecard['lineage_loop_score']}`",
                f"- Provenance completeness: `{scorecard['provenance_completeness_score']}`",
                f"- Compliance readiness: `{scorecard['compliance_readiness_score']}`",
            ]
        )
        if oracle.get("oracle_status") == "completed":
            alerts = oracle.get("alerts", [])
            source_baseline = oracle.get("source_baseline_identity") or "not_declared"
            severity_state = "CRITICAL" if any(alert.get("severity") == "CRITICAL" for alert in alerts) else "WARN"
            remediation_steps = sorted(
                {
                    step
                    for alert in alerts
                    for step in alert.get("remediation_steps", [])
                }
            )
            lines.extend(
                [
                    "",
                    "## Step-Zero Curriculum Optimization",
                    f"- Structural similarity baseline: `{source_baseline}`",
                    f"- Pre-flight state: `{severity_state}`",
                    f"- Oracle alert count: `{len(alerts)}`",
                ]
            )
            for alert in alerts:
                category_label = str(alert["category"]).lower().replace("_", " ")
                explanation = self._risk_explanation(str(alert["category"]))
                lines.append(
                    f"- `{alert['severity']}` `{category_label}` `{alert['action_required']}`"
                )
                lines.append(f"  - Signal: `{explanation['signal']}`")
                lines.append(f"  - Why: `{explanation['why']}`")
                lines.append(f"  - Action: `{explanation['action']}`")
            if remediation_steps:
                lines.extend(["", "### Remediation Checklist"])
                lines.extend(f"- `{step}`" for step in remediation_steps)
        markdown = "\n".join(lines) + "\n"
        self._validate_rendered_markdown(markdown)
        return markdown

    def _risk_explanation(self, category: str) -> dict[str, str]:
        explanations = {
            "BENCHMARK_LEAK": {
                "signal": "benchmark_alias_overlap",
                "why": "evaluation_overlap_can_overstate_release_quality",
                "action": "remove_overlap_or_use_private_holdout",
            },
            "MODEL_INBREEDING": {
                "signal": "lineage_feedback_loop",
                "why": "model_family_reuse_can_amplify_prior_errors",
                "action": "add_external_grounding_or_lineage_exception",
            },
            "PROVENANCE_GAP": {
                "signal": "incomplete_source_descriptor",
                "why": "missing_provenance_blocks_audit_signoff",
                "action": "add_license_and_source_hashes",
            },
            "TRAINING_LOSS_DIVERGENCE": {
                "signal": "known_structural_loss_spike_pattern",
                "why": "mixture_shape_can_waste_compute_before_eval",
                "action": "rebalance_curriculum_before_gpu_run",
            },
            "DOMAIN_CROSSING": {
                "signal": "cross_domain_regulatory_tag",
                "why": "passport_scope_must_stay_domain_clean",
                "action": "remove_cross_domain_tags",
            },
        }
        result = explanations.get(
            category,
            {
                "signal": "metadata_policy_signal",
                "why": "structural_evidence_requires_review",
                "action": "review_manifest_metadata",
            },
        )
        NoPayloadValidator().validate(result)
        return result

    def _build_diff_free_pr_proof(self, report: dict[str, Any]) -> dict[str, Any]:
        proof = {
            "metadata_file_count": int(report.get("metadata_file_count", 0)),
            "changed_path_hashes": report.get("changed_path_hashes", []),
            "raw_diff_absent": True,
            "raw_payload_absent": True,
            "payload_policy": "passed",
        }
        NoPayloadValidator().validate(proof)
        proof["diff_free_evidence_hash_sha256"] = canonical_sha256(proof)
        return proof

    def _validate_rendered_markdown(self, markdown: str) -> None:
        validate_rendered_text(markdown)

    def _oracle_outputs(
        self,
        *,
        ledger_path: Path,
        project_namespace: str,
        output_dir: Path,
        enabled_domains: str,
        domain_selection_mode: str,
    ) -> dict[str, Any]:
        manifest = self._load_oracle_manifest()
        if manifest is None:
            return {
                "oracle_status": "skipped_no_manifest",
                "enabled_domains": [],
                "skipped_domains": [],
                **_EclInternalCore().atlas_source_summary(),
            }
        core = _EclInternalCore()
        alerts = EclPreFlightShield(
            core=core,
            enabled_domains=enabled_domains,
            domain_selection_mode=domain_selection_mode,
        ).validate_run_manifest(manifest)
        blueprint = CurriculumBlueprintOracle(
            core=core,
            enabled_domains=enabled_domains,
            domain_selection_mode=domain_selection_mode,
        ).generate_step_zero_blueprint([manifest], {"release_readiness": 1.0})
        output = {
            "oracle_status": "completed",
            "alerts": alerts,
            "blueprint": blueprint,
            "source_baseline_identity": str(manifest.get("source_baseline_identity") or "not_declared"),
            "enabled_domains": blueprint.get("enabled_domains", []),
            "skipped_domains": blueprint.get("skipped_domains", []),
            **core.atlas_source_summary(),
        }
        output["blueprint_event_hash_sha256"] = self._append_blueprint_event(
            ledger_path=ledger_path,
            project_namespace=project_namespace,
            blueprint=blueprint,
        )["event_hash_sha256"]
        output["oracle_event_hash_sha256"] = self._append_oracle_event(
            ledger_path=ledger_path,
            project_namespace=project_namespace,
            oracle=output,
            domain_selection_mode=domain_selection_mode,
        )["event_hash_sha256"]
        NoPayloadValidator().validate(output)
        return output

    def _append_blueprint_event(
        self,
        *,
        ledger_path: Path,
        project_namespace: str,
        blueprint: dict[str, Any],
    ) -> dict[str, Any]:
        event = CurriculumBlueprintEvent(
            project_namespace=project_namespace,
            atlas_manifest_hash=str(blueprint["atlas_manifest_hash"]),
            enabled_domains=[str(domain) for domain in blueprint.get("enabled_domains", [])],
            skipped_domains=[str(domain) for domain in blueprint.get("skipped_domains", [])],
            domain_selection_mode=str(blueprint["domain_selection_mode"]),
            divergence_risk_coefficient=float(blueprint["divergence_risk_coefficient"]),
            estimated_compute_optimization_gain=float(blueprint["estimated_compute_optimization_gain"]),
            curriculum_blueprint_hash_sha256=canonical_sha256(blueprint),
        )
        return AppendOnlyEventLog(ledger_path).append(event)

    def _append_oracle_event(
        self,
        *,
        ledger_path: Path,
        project_namespace: str,
        oracle: dict[str, Any],
        domain_selection_mode: str,
    ) -> dict[str, Any]:
        alerts = oracle.get("alerts", [])
        event = OracleShieldRunEvent(
            project_namespace=project_namespace,
            source_baseline_identity=str(oracle.get("source_baseline_identity") or "not_declared"),
            atlas_manifest_hash=str(oracle["blueprint"]["atlas_manifest_hash"]),
            enabled_domains=[str(domain) for domain in oracle.get("enabled_domains", [])],
            skipped_domains=[str(domain) for domain in oracle.get("skipped_domains", [])],
            domain_selection_mode=domain_selection_mode,
            alert_count=len(alerts),
            critical_count=sum(1 for alert in alerts if alert.get("severity") == "CRITICAL"),
            warn_count=sum(1 for alert in alerts if alert.get("severity") == "WARN"),
            review_count=sum(1 for alert in alerts if alert.get("action_required") == "REVIEW"),
            quarantine_count=sum(1 for alert in alerts if alert.get("action_required") == "QUARANTINE"),
            benchmark_alert_count=sum(1 for alert in alerts if alert.get("category") == "BENCHMARK_LEAK"),
            lineage_alert_count=sum(1 for alert in alerts if alert.get("category") == "MODEL_INBREEDING"),
            provenance_gap_count=sum(1 for alert in alerts if alert.get("category") == "PROVENANCE_GAP"),
            oracle_alerts_hash_sha256=canonical_sha256(alerts),
            oracle_blueprint_hash_sha256=canonical_sha256(oracle["blueprint"]),
        )
        return AppendOnlyEventLog(ledger_path).append(event)

    def _append_diff_free_pr_event(
        self,
        *,
        ledger_path: Path,
        project_namespace: str,
        proof: dict[str, Any],
    ) -> dict[str, Any]:
        event = DiffFreePREvidenceEvent(
            project_namespace=project_namespace,
            metadata_file_count=int(proof["metadata_file_count"]),
            changed_path_hashes=list(proof.get("changed_path_hashes", [])),
            diff_free_pr_proof_hash_sha256=canonical_sha256(proof),
        )
        return AppendOnlyEventLog(ledger_path).append(event)

    def _append_passport_event(
        self,
        *,
        ledger_path: Path,
        project_namespace: str,
        passport: dict[str, Any],
        passport_markdown: str,
        enabled_domains: list[str],
    ) -> dict[str, Any]:
        verification = HashChainVerifier(ledger_path).verify()
        event = CompliancePassportEvent(
            project_namespace=project_namespace,
            report_profile=str(passport["report_profile"]),
            ledger_event_count=int(passport["event_count"]),
            hash_chain_valid=bool(passport["hash_chain_verification"]["valid"]),
            atlas_manifest_hash=passport.get("atlas_manifest_hash"),
            enabled_domains=[str(domain) for domain in enabled_domains],
            domain_sections_hash_sha256=canonical_sha256(passport.get("domain_sections", [])),
            passport_report_hash_sha256=canonical_sha256(passport),
            passport_markdown_hash_sha256=sha256_hex(passport_markdown),
        )
        appended = AppendOnlyEventLog(ledger_path).append(event)
        if not verification["valid"]:
            HashChainVerifier(ledger_path).raise_if_invalid()
        return appended

    def _append_artifact_export_event(
        self,
        *,
        ledger_path: Path,
        project_namespace: str,
        paths: dict[str, Path],
        verification: dict[str, Any],
    ) -> dict[str, Any]:
        artifact_hashes = {
            name: sha256_hex(path.read_bytes())
            for name, path in sorted(paths.items())
            if path.exists() and path.is_file()
        }
        event = LocalArtifactExportEvent(
            project_namespace=project_namespace,
            output_artifact_count=len(artifact_hashes),
            output_artifact_hashes_sha256=artifact_hashes,
            ledger_verification_status="valid" if verification.get("valid") else "invalid",
        )
        return AppendOnlyEventLog(ledger_path).append(event)

    def _load_oracle_manifest(self) -> dict[str, Any] | None:
        candidates: list[Path] = [Path(name) for name in MANIFEST_NAMES]
        candidates.extend(Path(".").glob("*.eclmeta.json"))
        candidates.extend(Path(".").glob("*.eclmeta.yaml"))
        candidates.extend(Path(".").glob("*.eclmeta.yml"))
        for path in candidates:
            if not path.exists() or not path.is_file():
                continue
            if path.suffix in {".yaml", ".yml"}:
                data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            else:
                import json

                data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                NoPayloadValidator().validate(data)
                return data
        return None
