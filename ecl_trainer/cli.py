from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import typer
import yaml

from ecl_trainer.ci.artifacts import PR_COMMENT_MARKER, LocalCIArtifactGenerator
from ecl_trainer.ci.github_action import GitHubActionRunner
from ecl_trainer.ci.github_comment import GitHubPRCommentPoster
from ecl_trainer.ci.gitlab_ci import GitLabCIRunner
from ecl_trainer.ci.reporting import CIReportRenderer
from ecl_trainer.ci.scanner import CIScanner
from ecl_trainer.compliance.reports import CompliancePassportGenerator
from ecl_trainer.core.ledger import AppendOnlyEventLog, HashChainVerifier
from ecl_trainer.core.models import (
    CompliancePassportEvent,
    DatasetRegisteredEvent,
    DiffFreePREvidenceEvent,
    HuggingFaceCardExportEvent,
    OracleShieldRunEvent,
    ReportProfile,
)
from ecl_trainer.core.policy import NoPayloadValidator, sha256_hex
from ecl_trainer.core.serialization import canonical_json, canonical_sha256
from ecl_trainer.governance import (
    AtlasMaturityReporter,
    HumanApprovalRecorder,
    LedgerQueryService,
    PolicySimulator,
)
from ecl_trainer.hub.huggingface_cards import HuggingFaceCardExporter
from ecl_trainer.lifecycle.freshness import AtlasFreshnessValidator
from ecl_trainer.lifecycle.sync import OfflineSyncManager
from ecl_trainer.oracle.blueprint import CurriculumBlueprintOracle
from ecl_trainer.oracle.passport import RegulatoryPassportCompiler
from ecl_trainer.oracle.shield import EclPreFlightShield
from ecl_trainer.red_team import run_corpus
from ecl_trainer.security.supply_chain import SupplyChainEvidenceGenerator
from ecl_trainer.ux import ArtifactViewer, AtlasPackStatusReporter, GitHubActionDoctor, write_trial_bundle

app = typer.Typer(no_args_is_help=True)
oracle_app = typer.Typer(no_args_is_help=True)
lifecycle_app = typer.Typer(no_args_is_help=True)
doctor_app = typer.Typer(no_args_is_help=True)
atlas_pack_app = typer.Typer(no_args_is_help=True)
artifact_app = typer.Typer(no_args_is_help=True)
app.add_typer(oracle_app, name="oracle")
app.add_typer(lifecycle_app, name="lifecycle")
app.add_typer(doctor_app, name="doctor")
app.add_typer(atlas_pack_app, name="atlas-pack")
app.add_typer(artifact_app, name="artifact-viewer")


def _load_mapping(path: str) -> dict:
    source = Path(path)
    if source.suffix in {".yaml", ".yml"}:
        data = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    else:
        import json

        data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise typer.BadParameter("metadata file must contain an object")
    return data


def _domain_args(domain: str | None, enabled_domains: str) -> str:
    values = [part.strip() for part in enabled_domains.split(",") if part.strip()]
    if domain:
        values.append(domain)
    return ",".join(values)


@app.command()
def scan(
    project_namespace: str = "default",
    ledger_path: str = ".ecl-trainer/events.jsonl",
    changed_only: bool = True,
) -> None:
    report = CIScanner(
        project_namespace=project_namespace,
        ledger_path=ledger_path,
    ).scan(changed_only=changed_only)
    typer.echo(CIReportRenderer().render_markdown(report))


@app.command()
def passport(
    ledger_path: str = ".ecl-trainer/events.jsonl",
    project_namespace: str | None = None,
    profile: ReportProfile = ReportProfile.INTERNAL_AUDIT,
) -> None:
    generator = CompliancePassportGenerator(ledger_path)
    typer.echo(generator.render_markdown(generator.generate(profile=profile, project_namespace=project_namespace)))


@app.command("verify-log")
def verify_log(ledger_path: str = ".ecl-trainer/events.jsonl") -> None:
    typer.echo(HashChainVerifier(ledger_path).verify())


@app.command("render-pr-comment")
def render_pr_comment(project_namespace: str = "default", ledger_path: str = ".ecl-trainer/events.jsonl") -> None:
    report = CIScanner(project_namespace=project_namespace, ledger_path=ledger_path).scan(changed_only=True)
    typer.echo(CIReportRenderer().render_markdown(report))


@app.command("github-action")
def github_action(
    project_namespace: str = "default",
    ledger_path: str = ".ecl-trainer/events.jsonl",
    risk_policy: str = "report_only",
    changed_only: bool = True,
) -> None:
    report = GitHubActionRunner().run(
        project_namespace=project_namespace,
        ledger_path=ledger_path,
        changed_only=changed_only,
        risk_policy=risk_policy,
    )
    raise typer.Exit(1 if report["should_fail"] else 0)


@app.command("github-pr-report")
def github_pr_report(
    project_namespace: str = "default",
    ledger_path: str = ".ecl-trainer/events.jsonl",
    output_dir: str = ".ecl-trainer/reports",
    risk_policy: str = "report_only",
    changed_only: bool = True,
    domain: str | None = None,
    enabled_domains: str = "",
    domain_selection_mode: str = "auto",
    ignore_staleness: bool = False,
) -> None:
    manifest = LocalCIArtifactGenerator().generate(
        project_namespace=project_namespace,
        ledger_path=ledger_path,
        output_dir=output_dir,
        changed_only=changed_only,
        risk_policy=risk_policy,
        enabled_domains=_domain_args(domain, enabled_domains),
        domain_selection_mode=domain_selection_mode,
        ignore_staleness=ignore_staleness,
    )
    typer.echo(canonical_json(manifest))
    raise typer.Exit(1 if manifest["should_fail"] else 0)


@app.command("post-github-comment")
def post_github_comment(
    comment_path: str = ".ecl-trainer/reports/pr-comment.md",
    marker: str = PR_COMMENT_MARKER,
) -> None:
    result = GitHubPRCommentPoster().post(comment_path=comment_path, marker=marker)
    typer.echo(canonical_json(result))


@oracle_app.command("blueprint")
def oracle_blueprint(
    manifest: str = typer.Option(...),
    target: str = typer.Option(...),
    output: str | None = None,
    domain: str | None = None,
    enabled_domains: str = "",
    domain_selection_mode: str = "auto",
) -> None:
    metadata = _load_mapping(manifest)
    target_metrics = _load_mapping(target)
    result = CurriculumBlueprintOracle(
        enabled_domains=_domain_args(domain, enabled_domains),
        domain_selection_mode=domain_selection_mode,
    ).generate_step_zero_blueprint([metadata], target_metrics)
    rendered = canonical_json(result)
    if output:
        Path(output).write_text(rendered, encoding="utf-8")
    typer.echo(rendered)


@oracle_app.command("shield")
def oracle_shield(
    manifest: str = typer.Option(...),
    output: str | None = None,
    ledger_path: str | None = ".ecl-trainer/events.jsonl",
    project_namespace: str = "default",
    domain: str | None = None,
    enabled_domains: str = "",
    domain_selection_mode: str = "auto",
) -> None:
    metadata = _load_mapping(manifest)
    result = EclPreFlightShield(
        enabled_domains=_domain_args(domain, enabled_domains),
        domain_selection_mode=domain_selection_mode,
    ).validate_run_manifest(metadata)
    if ledger_path:
        atlas_hash = result[0]["atlas_manifest_hash"] if result else ""
        result_enabled_domains = result[0].get("enabled_domains", []) if result else []
        result_skipped_domains = result[0].get("skipped_domains", []) if result else []
        AppendOnlyEventLog(ledger_path).append(
            OracleShieldRunEvent(
                project_namespace=project_namespace,
                source_baseline_identity=str(metadata.get("source_baseline_identity") or "not_declared"),
                atlas_manifest_hash=atlas_hash,
                enabled_domains=[str(domain_id) for domain_id in result_enabled_domains],
                skipped_domains=[str(domain_id) for domain_id in result_skipped_domains],
                domain_selection_mode=domain_selection_mode,
                alert_count=len(result),
                critical_count=sum(1 for alert in result if alert.get("severity") == "CRITICAL"),
                warn_count=sum(1 for alert in result if alert.get("severity") == "WARN"),
                review_count=sum(1 for alert in result if alert.get("action_required") == "REVIEW"),
                quarantine_count=sum(1 for alert in result if alert.get("action_required") == "QUARANTINE"),
                oracle_alerts_hash_sha256=canonical_sha256(result),
            )
        )
    rendered = canonical_json(result)
    if output:
        Path(output).write_text(rendered, encoding="utf-8")
    typer.echo(rendered)


@oracle_app.command("passport")
def oracle_passport(
    ledger_path: str = ".ecl-trainer/events.jsonl",
    output_dir: str = ".ecl-trainer/reports",
    project_namespace: str = "default",
    domain: str | None = None,
    enabled_domains: str = "",
    profile: str = ReportProfile.INTERNAL_AUDIT.value,
) -> None:
    compiler = RegulatoryPassportCompiler(
        ledger_path=ledger_path,
        enabled_domains=_domain_args(domain, enabled_domains),
    )
    report = compiler.compile_compliance_passport(None, profile=profile)
    markdown = compiler.render_markdown(report)
    AppendOnlyEventLog(ledger_path).append(
        CompliancePassportEvent(
            project_namespace=project_namespace,
            report_profile=str(report["report_profile"]),
            ledger_event_count=int(report["event_count"]),
            hash_chain_valid=bool(report["hash_chain_verification"]["valid"]),
            atlas_manifest_hash=report.get("atlas_manifest_hash"),
            enabled_domains=[str(domain_id) for domain_id in report.get("enabled_domains", [])],
            domain_sections_hash_sha256=canonical_sha256(report.get("domain_sections", [])),
            passport_report_hash_sha256=canonical_sha256(report),
            passport_markdown_hash_sha256=sha256_hex(markdown),
        )
    )
    paths = compiler.write_outputs(output_dir, report)
    safe_paths = {name: Path(path).name for name, path in paths.items()}
    typer.echo(canonical_json(safe_paths))


@lifecycle_app.command("check")
def lifecycle_check(
    atlas_path: str | None = None,
    output: str | None = None,
    ignore_staleness: bool = False,
) -> None:
    result = AtlasFreshnessValidator(atlas_path=atlas_path).evaluate_atlas_lifecycle(
        datetime.now(UTC),
        ignore_staleness=ignore_staleness,
    )
    rendered = canonical_json(result)
    if output:
        Path(output).write_text(rendered, encoding="utf-8")
    typer.echo(rendered)


@lifecycle_app.command("apply-patch")
def lifecycle_apply_patch(
    patch_archive: str = typer.Option(...),
    atlas_path: str | None = None,
    output: str | None = None,
) -> None:
    result = OfflineSyncManager(atlas_path=atlas_path).apply_patch(patch_archive)
    rendered = canonical_json(result)
    if output:
        Path(output).write_text(rendered, encoding="utf-8")
    typer.echo(rendered)


@app.command("gitlab-ci")
def gitlab_ci(
    project_namespace: str = "default",
    ledger_path: str = ".ecl-trainer/events.jsonl",
    risk_policy: str = "report_only",
    changed_only: bool = True,
) -> None:
    report = GitLabCIRunner().run(
        project_namespace=project_namespace,
        ledger_path=ledger_path,
        changed_only=changed_only,
        risk_policy=risk_policy,
    )
    raise typer.Exit(1 if report["should_fail"] else 0)


@app.command("hf-card-export")
def hf_card_export(
    ecl_fingerprint: str,
    compliance_passport_hash: str,
    ledger_path: str | None = None,
    project_namespace: str = "default",
) -> None:
    metadata = {
        "ecl_fingerprint": ecl_fingerprint,
        "compliance_passport_hash": compliance_passport_hash,
        "source_root_hashes": [],
        "license_matrix": [],
    }
    exported = HuggingFaceCardExporter().export(metadata)
    if ledger_path:
        AppendOnlyEventLog(ledger_path).append(
            HuggingFaceCardExportEvent(
                project_namespace=project_namespace,
                ecl_fingerprint_hash_sha256=sha256_hex(ecl_fingerprint),
                compliance_passport_hash_sha256=sha256_hex(compliance_passport_hash),
                hf_card_hash_sha256=canonical_sha256(exported),
            )
        )
    typer.echo(exported["model_card_section"])
    typer.echo(exported["dataset_card_section"])


@app.command("supply-chain-evidence")
def supply_chain_evidence(
    repository_root: str = ".",
    output_dir: str = ".ecl-trainer/supply-chain",
) -> None:
    paths = SupplyChainEvidenceGenerator(repository_root=repository_root).write_outputs(output_dir)
    typer.echo(canonical_json(paths))


@app.command("register-dataset")
def register_dataset(
    metadata: str = typer.Option(...),
    project_namespace: str = "default",
    ledger_path: str = ".ecl-trainer/events.jsonl",
) -> None:
    value = _load_mapping(metadata)
    NoPayloadValidator().validate(value)
    record_hash = canonical_sha256(value)
    dataset_hash = str(value.get("dataset_identifier_hash_sha256") or record_hash)
    schema_hash = value.get("schema_hash_sha256")
    source_hash = value.get("source_reference_hash_sha256")
    event = DatasetRegisteredEvent(
        project_namespace=project_namespace,
        dataset_identifier_hash_sha256=dataset_hash,
        schema_hash_sha256=str(schema_hash) if schema_hash else None,
        metadata_record_hash_sha256=record_hash,
        source_reference_hash_sha256=str(source_hash) if source_hash else None,
    )
    typer.echo(canonical_json(AppendOnlyEventLog(ledger_path).append(event)))


@app.command("diff-free-pr-proof")
def diff_free_pr_proof(
    project_namespace: str = "default",
    ledger_path: str = ".ecl-trainer/events.jsonl",
    output: str | None = None,
    changed_only: bool = True,
) -> None:
    report = CIScanner(project_namespace=project_namespace, ledger_path=ledger_path).scan(changed_only=changed_only)
    proof = {
        "metadata_file_count": int(report.get("metadata_file_count", 0)),
        "changed_path_hashes": report.get("changed_path_hashes", []),
        "raw_diff_absent": True,
        "raw_payload_absent": True,
        "payload_policy": "passed",
    }
    proof["diff_free_evidence_hash_sha256"] = canonical_sha256(proof)
    event = DiffFreePREvidenceEvent(
        project_namespace=project_namespace,
        metadata_file_count=int(proof["metadata_file_count"]),
        changed_path_hashes=list(proof.get("changed_path_hashes", [])),
        diff_free_pr_proof_hash_sha256=canonical_sha256(proof),
    )
    appended = AppendOnlyEventLog(ledger_path).append(event)
    proof["diff_free_pr_event_hash_sha256"] = appended["event_hash_sha256"]
    rendered = canonical_json(proof)
    if output:
        Path(output).write_text(rendered, encoding="utf-8")
    typer.echo(rendered)


@app.command("approve-risk")
def approve_risk(
    risk_id: str,
    approver_role: str,
    reason_code: str,
    project_namespace: str = "default",
    ledger_path: str = ".ecl-trainer/events.jsonl",
) -> None:
    result = HumanApprovalRecorder().record(
        ledger_path=ledger_path,
        project_namespace=project_namespace,
        risk_id=risk_id,
        approver_role=approver_role,
        reason_code=reason_code,
    )
    typer.echo(canonical_json(result))


@app.command("simulate-policy")
def simulate_policy(
    manifest: str = typer.Option(...),
    project_namespace: str = "default",
    risk_policy: str = "report_only",
    domain: str | None = None,
    enabled_domains: str = "",
    domain_selection_mode: str = "auto",
    output: str | None = None,
) -> None:
    result = PolicySimulator().simulate(
        manifest=_load_mapping(manifest),
        project_namespace=project_namespace,
        risk_policy=risk_policy,
        enabled_domains=_domain_args(domain, enabled_domains),
        domain_selection_mode=domain_selection_mode,
    )
    rendered = canonical_json(result)
    if output:
        Path(output).write_text(rendered, encoding="utf-8")
    typer.echo(rendered)


@app.command("domain-maturity")
def domain_maturity(output: str | None = None) -> None:
    result = AtlasMaturityReporter().summarize()
    rendered = canonical_json(result)
    if output:
        Path(output).write_text(rendered, encoding="utf-8")
    typer.echo(rendered)


@app.command("history")
def history(
    ledger_path: str = ".ecl-trainer/events.jsonl",
    event_type: str | None = None,
    project_namespace: str | None = None,
) -> None:
    result = LedgerQueryService(ledger_path).history(event_type=event_type, project_namespace=project_namespace)
    typer.echo(canonical_json(result))


@app.command("explain-chain")
def explain_chain(ledger_path: str = ".ecl-trainer/events.jsonl") -> None:
    result = LedgerQueryService(ledger_path).explain_chain()
    typer.echo(canonical_json(result))


@app.command("red-team-corpus")
def red_team_corpus(
    fixtures_root: str = "tests/red_team_fixtures",
    output: str | None = None,
) -> None:
    result = run_corpus(fixtures_root)
    rendered = canonical_json(result)
    if output:
        Path(output).write_text(rendered, encoding="utf-8")
    typer.echo(rendered)


@doctor_app.command("github-action")
def doctor_github_action(
    repository_root: str = ".",
    workflow_path: str = ".github/workflows/ecl-trainer.yml",
    manifest_path: str = "ecl-trainer.manifest.json",
    reports_dir: str = ".ecl-trainer/reports",
    output: str | None = None,
) -> None:
    result = GitHubActionDoctor().inspect(
        repository_root=repository_root,
        workflow_path=workflow_path,
        manifest_path=manifest_path,
        reports_dir=reports_dir,
    )
    rendered = canonical_json(result)
    if output:
        Path(output).write_text(rendered, encoding="utf-8")
    typer.echo(rendered)


@atlas_pack_app.command("status")
def atlas_pack_status(output: str | None = None) -> None:
    result = AtlasPackStatusReporter().status()
    rendered = canonical_json(result)
    if output:
        Path(output).write_text(rendered, encoding="utf-8")
    typer.echo(rendered)


@atlas_pack_app.command("validate-source")
def atlas_pack_validate_source(source: str = typer.Option(...), output: str | None = None) -> None:
    result = AtlasPackStatusReporter().validate_source(_load_mapping(source))
    rendered = canonical_json(result)
    if output:
        Path(output).write_text(rendered, encoding="utf-8")
    typer.echo(rendered)


@artifact_app.command("build")
def artifact_viewer_build(
    reports_dir: str = ".ecl-trainer/reports",
    ledger_path: str = ".ecl-trainer/events.jsonl",
    output: str = ".ecl-trainer/reports/artifact-viewer.html",
) -> None:
    result = ArtifactViewer().build(reports_dir=reports_dir, ledger_path=ledger_path, output=output)
    typer.echo(canonical_json(result))


@app.command("trial-bundle")
def trial_bundle(output_dir: str = "trial_bundles/ecl_learning_ledger") -> None:
    result = write_trial_bundle(output_dir)
    typer.echo(canonical_json(result))


if __name__ == "__main__":
    app()
