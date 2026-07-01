import json
from pathlib import Path

from typer.testing import CliRunner

from ecl_trainer.cli import app
from ecl_trainer.core.policy import NoPayloadValidator, sha256_hex


def test_doctor_github_action_reports_missing_setup(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(app, ["doctor", "github-action"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["status"] == "action_required"
    assert "add_metadata_manifest" in payload["next_steps"]
    NoPayloadValidator().validate(payload)


def test_doctor_github_action_passes_after_first_run_files_exist(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    workflow = tmp_path / ".github" / "workflows" / "ecl-trainer.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        """
permissions:
  contents: read
  issues: write
jobs:
  ecl:
    steps:
      - uses: ./.github/actions/ecl-trainer-scan
        with:
          risk_policy: report_only
""",
        encoding="utf-8",
    )
    Path("ecl-trainer.manifest.json").write_text(
        json.dumps(
            {
                "domain": "financial_services",
                "dataset_identifier_hash_sha256": sha256_hex("dataset"),
                "schema_hash_sha256": sha256_hex("schema"),
            }
        ),
        encoding="utf-8",
    )
    reports = tmp_path / ".ecl-trainer" / "reports"
    reports.mkdir(parents=True)
    for filename in ("risk-report.md", "compliance-passport.md", "verification.json", "pr-comment.md"):
        (reports / filename).write_text("status: passed\n", encoding="utf-8")

    result = CliRunner().invoke(app, ["doctor", "github-action"])

    assert result.exit_code == 0
    assert json.loads(result.output)["status"] == "pass"


def test_atlas_pack_status_and_validate_source_cli(tmp_path):
    source = tmp_path / "source.json"
    source.write_text(
        json.dumps(
            {
                "domain_id": "healthcare_clinical",
                "source_family": "clinical_trials_metadata",
                "source_reference_hash_sha256": sha256_hex("clinical-source"),
                "metadata_fields_available": ["study_phase_tags", "license_descriptor"],
                "license_descriptor": "public_metadata_reference",
            }
        ),
        encoding="utf-8",
    )
    runner = CliRunner()

    status = runner.invoke(app, ["atlas-pack", "status"])
    validated = runner.invoke(app, ["atlas-pack", "validate-source", "--source", str(source)])

    assert status.exit_code == 0
    assert json.loads(status.output)["domain_count"] == 20
    assert validated.exit_code == 0
    assert json.loads(validated.output)["status"] == "pass"


def test_artifact_viewer_and_trial_bundle_cli(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    reports = tmp_path / ".ecl-trainer" / "reports"
    reports.mkdir(parents=True)
    (reports / "risk-report.md").write_text("# Risk\n- Status: `pass`\n", encoding="utf-8")
    (reports / "compliance-passport.md").write_text("# Passport\n- Hash chain: `valid`\n", encoding="utf-8")
    (reports / "verification.json").write_text('{"valid":true,"event_count":0}\n', encoding="utf-8")
    (reports / "pr-comment.md").write_text("# Comment\n- Payload policy: `passed`\n", encoding="utf-8")

    runner = CliRunner()
    viewer = runner.invoke(app, ["artifact-viewer", "build"])
    bundle = runner.invoke(app, ["trial-bundle", "--output-dir", "trial"])

    assert viewer.exit_code == 0
    viewer_payload = json.loads(viewer.output)
    assert Path(viewer_payload["artifact_viewer"]).exists()
    assert bundle.exit_code == 0
    assert Path("trial/ecl-trainer.manifest.json").exists()
