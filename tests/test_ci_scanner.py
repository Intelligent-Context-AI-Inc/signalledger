import json

import pytest

from ecl_trainer.ci.scanner import CIScanner
from ecl_trainer.core.exceptions import PayloadExfiltrationException


def test_ci_scanner_hashes_changed_metadata_paths(tmp_path):
    scanner = CIScanner(repository_root=tmp_path, ledger_path=tmp_path / "events.jsonl", project_namespace="project")
    report = scanner.scan(changed_only=True, changed_files=["configs/train.yaml", "src/app.py"])
    assert report["metadata_file_count"] == 1
    assert report["changed_path_hashes"]


def test_ci_scanner_computes_high_risk_from_metadata_file(tmp_path):
    (tmp_path / "configs").mkdir()
    manifest = tmp_path / "configs" / "training_config.json"
    manifest.write_text(json.dumps({"benchmark_aliases": ["mmlu"]}), encoding="utf-8")
    scanner = CIScanner(repository_root=tmp_path, ledger_path=tmp_path / "events.jsonl", project_namespace="project")

    report = scanner.scan(changed_only=True, changed_files=["configs/training_config.json"])

    assert report["risk_summary"]["status"] == "high_risk"
    assert report["risk_summary"]["risk_flags"][0]["risk_type"] == "benchmark_contamination"


def test_ci_scanner_rejects_payload_in_metadata_file_before_append(tmp_path):
    (tmp_path / "data").mkdir()
    manifest = tmp_path / "data" / "dataset.json"
    manifest.write_text(json.dumps({"rawPreviewText": "blocked"}), encoding="utf-8")
    scanner = CIScanner(repository_root=tmp_path, ledger_path=tmp_path / "events.jsonl", project_namespace="project")

    with pytest.raises(PayloadExfiltrationException):
        scanner.scan(changed_only=True, changed_files=["data/dataset.json"])

    assert not (tmp_path / "events.jsonl").exists()


def test_ci_scanner_ignores_github_action_yaml(tmp_path):
    action_dir = tmp_path / ".github" / "actions" / "ecl-trainer-scan"
    action_dir.mkdir(parents=True)
    action_file = action_dir / "action.yml"
    action_file.write_text(
        """
name: ECL Trainer Scan
inputs:
  api_key:
    required: false
""",
        encoding="utf-8",
    )
    scanner = CIScanner(repository_root=tmp_path, ledger_path=tmp_path / "events.jsonl", project_namespace="project")

    report = scanner.scan(changed_only=True, changed_files=[".github/actions/ecl-trainer-scan/action.yml"])

    assert report["metadata_file_count"] == 0
    assert report["payload_policy"] == "passed"
    assert report["risk_summary"]["status"] == "pass"


def test_ci_scanner_ignores_absolute_github_workflow_yaml(tmp_path):
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    workflow = workflow_dir / "ecl-trainer.yml"
    workflow.write_text(
        """
permissions:
  contents: read
  pull-requests: write
""",
        encoding="utf-8",
    )
    scanner = CIScanner(repository_root=tmp_path, ledger_path=tmp_path / "events.jsonl", project_namespace="project")

    report = scanner.scan(changed_only=True, changed_files=[str(workflow)])

    assert report["metadata_file_count"] == 0
    assert report["payload_policy"] == "passed"
    assert report["risk_summary"]["status"] == "pass"


def test_ci_scanner_ignores_example_github_action_workflow_yaml(tmp_path):
    workflow_dir = tmp_path / "examples" / "github_action"
    workflow_dir.mkdir(parents=True)
    workflow = workflow_dir / "ecl-trainer.yml"
    workflow.write_text(
        """
permissions:
  contents: read
jobs:
  ecl-trainer:
    runs-on: ubuntu-latest
""",
        encoding="utf-8",
    )
    scanner = CIScanner(repository_root=tmp_path, ledger_path=tmp_path / "events.jsonl", project_namespace="project")

    report = scanner.scan(changed_only=True, changed_files=["examples/github_action/ecl-trainer.yml"])

    assert report["metadata_file_count"] == 0
    assert report["payload_policy"] == "passed"
    assert report["risk_summary"]["status"] == "pass"


def test_ci_scanner_ignores_packaged_adversarial_fixture_payloads(tmp_path):
    fixture_dir = tmp_path / "ecl_trainer" / "red_team_fixtures"
    fixture_dir.mkdir(parents=True)
    fixture = fixture_dir / "payload_key_smuggling_embeddingvec.json"
    fixture.write_text(json.dumps({"metadata": {"embeddingvec": "blocked"}}), encoding="utf-8")
    scanner = CIScanner(repository_root=tmp_path, ledger_path=tmp_path / "events.jsonl", project_namespace="project")

    report = scanner.scan(
        changed_only=True,
        changed_files=["ecl_trainer/red_team_fixtures/payload_key_smuggling_embeddingvec.json"],
    )

    assert report["metadata_file_count"] == 0
    assert report["payload_policy"] == "passed"
    assert report["risk_summary"]["status"] == "pass"


def test_ci_scanner_ignores_absolute_packaged_adversarial_fixture_payloads(tmp_path):
    fixture_dir = tmp_path / "ecl_trainer" / "red_team_fixtures"
    fixture_dir.mkdir(parents=True)
    fixture = fixture_dir / "payload_key_smuggling_embeddingvec.json"
    fixture.write_text(json.dumps({"metadata": {"embeddingvec": "blocked"}}), encoding="utf-8")
    scanner = CIScanner(repository_root=tmp_path, ledger_path=tmp_path / "events.jsonl", project_namespace="project")

    report = scanner.scan(changed_only=True, changed_files=[str(fixture)])

    assert report["metadata_file_count"] == 0
    assert report["payload_policy"] == "passed"
    assert report["risk_summary"]["status"] == "pass"
