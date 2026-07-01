import json
from pathlib import Path

from typer.testing import CliRunner

from ecl_trainer.ci.artifacts import LocalCIArtifactGenerator
from ecl_trainer.cli import app
from ecl_trainer.core.policy import NoPayloadValidator


def test_local_ci_artifact_generator_writes_metadata_only_reports(tmp_path, monkeypatch):
    (tmp_path / "training").mkdir()
    (tmp_path / "training" / "config.yml").write_text("learning_rate: 0.001\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    manifest = LocalCIArtifactGenerator().generate(
        project_namespace="org/project",
        ledger_path=".ecl/events.jsonl",
        output_dir=".ecl/reports",
        changed_only=False,
        risk_policy="report_only",
    )

    assert manifest["mode"] == "local-only"
    assert manifest["payload_policy"] == "passed"
    assert manifest["supply_chain_evidence"] == "generated"
    assert Path(manifest["output_files"]["risk_report_markdown"]).exists()
    assert Path(manifest["output_files"]["compliance_passport_markdown"]).exists()
    assert Path(manifest["output_files"]["lifecycle_report_json"]).exists()
    assert Path(manifest["output_files"]["supply_chain_sbom_json"]).exists()
    assert Path(manifest["output_files"]["supply_chain_provenance_json"]).exists()
    assert Path(manifest["output_files"]["supply_chain_manifest_json"]).exists()
    comment = Path(manifest["output_files"]["pr_comment_markdown"]).read_text(encoding="utf-8")
    assert "Local Compliance Passport" in comment
    assert "Atlas source records" in comment
    assert "Atlas seeded domains" in comment
    assert "Atlas Lifecycle" in comment
    assert "Supply-chain evidence: `generated`" in comment
    for line in comment.splitlines():
        NoPayloadValidator().validate({"rendered_markdown_segment": line})
    events = [
        json.loads(line)
        for line in Path(".ecl/events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert [event["event_type"] for event in events] == [
        "ci_scan",
        "compliance_passport_generated",
        "risk_gate_decision",
        "diff_free_pr_evidence",
        "local_artifact_export",
    ]
    assert events[-1]["previous_event_hash_sha256"] == events[-2]["event_hash_sha256"]
    assert Path(manifest["output_files"]["diff_free_pr_proof_json"]).exists()
    assert manifest["risk_gate_status"] in {"ADMIT", "ADMIT_WITH_WARNINGS", "BLOCK"}


def test_github_pr_report_cli_generates_local_manifest(tmp_path, monkeypatch):
    (tmp_path / "datasets").mkdir()
    (tmp_path / "datasets" / "manifest.json").write_text('{"schema_hash_sha256":"abc"}\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(
        app,
        [
            "github-pr-report",
            "--project-namespace",
            "org/project",
            "--ledger-path",
            ".ecl/events.jsonl",
            "--output-dir",
            ".ecl/reports",
            "--no-changed-only",
        ],
    )

    assert result.exit_code == 0
    manifest = json.loads(result.output)
    assert manifest["mode"] == "local-only"
    assert manifest["supply_chain_evidence"] == "generated"
    assert "lifecycle_status" in manifest
    assert Path(".ecl/reports/compliance-passport.md").exists()
    assert Path(".ecl/reports/lifecycle-report.json").exists()
    assert Path(".ecl/reports/supply-chain/supply-chain-manifest.json").exists()
    event_types = [
        json.loads(line)["event_type"]
        for line in Path(".ecl/events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert event_types[-1] == "local_artifact_export"
