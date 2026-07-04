import json
from pathlib import Path

from ecl_trainer.ci.github_action import GitHubActionRunner
from ecl_trainer.ci.gitlab_ci import GitLabCIRunner


def test_github_action_runner_policy_decisions():
    runner = GitHubActionRunner()
    assert runner.should_fail({"risk_summary": {"status": "high_risk"}}, "block_on_high_risk") is True
    assert runner.should_fail({"payload_policy": "failed"}, "block_on_payload_violation") is True
    assert runner.should_fail({"risk_summary": {"status": "high_risk"}}, "report_only") is False


def test_gitlab_runner_policy_decisions():
    runner = GitLabCIRunner()
    assert runner.should_fail({"risk_summary": {"status": "high_risk"}}, "block_on_high_risk") is True
    assert runner.should_fail({"payload_policy": "failed"}, "block_on_payload_violation") is True
    assert runner.should_fail({"risk_summary": {"status": "high_risk"}}, "warn") is False


def test_github_action_runner_blocks_high_risk_metadata(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("configs").mkdir()
    Path("configs/training_config.json").write_text(json.dumps({"benchmark_aliases": ["mmlu"]}), encoding="utf-8")

    report = GitHubActionRunner().run(
        project_namespace="project",
        ledger_path=".ecl/events.jsonl",
        changed_only=False,
        risk_policy="block_on_high_risk",
    )

    assert report["risk_summary"]["status"] == "high_risk"
    assert report["should_fail"] is True


def test_github_action_runner_reports_payload_policy_failure(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("data").mkdir()
    Path("data/dataset.json").write_text(json.dumps({"rawPreviewText": "blocked"}), encoding="utf-8")

    report = GitHubActionRunner().run(
        project_namespace="project",
        ledger_path=".ecl/events.jsonl",
        changed_only=False,
        risk_policy="block_on_payload_violation",
    )

    assert report["payload_policy"] == "failed"
    assert report["should_fail"] is True


def test_github_action_fail_on_payload_violation_input_is_wired():
    action = Path(".github/actions/ecl-trainer-scan/action.yml").read_text(encoding="utf-8")
    assert "inputs.fail_on_payload_violation" in action


def test_github_action_usage_ping_is_opt_in_and_metadata_only():
    action = Path(".github/actions/ecl-trainer-scan/action.yml").read_text(encoding="utf-8")
    assert "report_usage:" in action
    assert "default: 'false'" in action
    assert "usage_ping_url:" in action
    assert "include_repository_name_in_usage:" in action
    assert "if: inputs.report_usage == 'true'" in action
    assert "usage-ping.json" in action
    assert "payload[\"repository\"]" in action
    assert "ECL_USAGE_INCLUDE_REPOSITORY_NAME" in action
    assert "raw_dataset_rows" not in action
    assert "raw_diff" not in action
