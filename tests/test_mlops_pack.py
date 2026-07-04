import json
from pathlib import Path

from typer.testing import CliRunner

from ecl_trainer.cli import app
from ecl_trainer.core.policy import NoPayloadValidator
from ecl_trainer.mlops_pack import MLOpsGovernancePackBuilder


def _write_base_reports(root: Path) -> Path:
    reports = root / ".ecl-trainer" / "reports"
    reports.mkdir(parents=True)
    (root / ".ecl-trainer" / "events.jsonl").write_text("", encoding="utf-8")
    (reports / "verification.json").write_text('{"valid":true,"event_count":3}\n', encoding="utf-8")
    (reports / "risk-report.json").write_text('{"payload_policy":"passed"}\n', encoding="utf-8")
    (reports / "compliance-passport.json").write_text(
        '{"hash_chain_verification":{"valid":true}}\n',
        encoding="utf-8",
    )
    (reports / "lifecycle-report.json").write_text('{"lifecycle_status":"CURRENT"}\n', encoding="utf-8")
    supply_chain = reports / "supply-chain"
    supply_chain.mkdir()
    for filename in ("supply-chain-sbom.json", "supply-chain-provenance.json", "supply-chain-manifest.json"):
        (supply_chain / filename).write_text('{"payload_policy":"passed"}\n', encoding="utf-8")
    return reports


def test_mlops_pack_builder_scores_public_catalog_gaps_and_validates_no_payload(tmp_path):
    reports = _write_base_reports(tmp_path)
    catalog = tmp_path / "hf-check.json"
    catalog.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "repo_id": "org/model",
                        "metadata_fingerprint_sha256": "a" * 64,
                        "findings": [
                            {"code": "TRAINING_DATA_PROVENANCE_GAP"},
                            {"code": "EVAL_METADATA_GAP"},
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = MLOpsGovernancePackBuilder().build(
        reports_dir=reports,
        ledger_path=tmp_path / ".ecl-trainer" / "events.jsonl",
        output_dir=reports,
        catalog_check_json=catalog,
    )

    pack = result["pack"]
    assert pack["release_readiness_score"] == 75
    assert pack["readiness_status"] == "watch"
    assert pack["catalog_gap_count"] == 2
    assert "TRAINING_DATA_PROVENANCE_GAP" in pack["catalog_gap_indicators"]
    assert Path(result["paths"]["mlops_governance_pack_json"]).exists()
    assert Path(result["paths"]["catalog_drift_snapshot_json"]).exists()
    NoPayloadValidator().validate(pack)


def test_mlops_pack_builder_detects_regressed_drift(tmp_path):
    reports = _write_base_reports(tmp_path)
    previous = tmp_path / "previous-pack.json"
    previous.write_text(
        json.dumps(
            {
                "readiness_status": "pass",
                "release_readiness_score": 100,
                "catalog_gap_indicators": [],
                "risk_gate_status": "ADMIT",
                "atlas_lifecycle_status": "CURRENT",
                "evidence_file_statuses": {"risk_report": "present"},
            }
        ),
        encoding="utf-8",
    )
    catalog = tmp_path / "hf-check.json"
    catalog.write_text(
        json.dumps({"results": [{"repo_id": "org/model", "findings": [{"code": "LANGUAGE_METADATA_GAP"}]}]}),
        encoding="utf-8",
    )

    pack = MLOpsGovernancePackBuilder().build(
        reports_dir=reports,
        ledger_path=tmp_path / ".ecl-trainer" / "events.jsonl",
        output_dir=reports,
        previous_pack=previous,
        catalog_check_json=catalog,
    )["pack"]

    drift = pack["catalog_drift_snapshot"]
    assert drift["trend"] == "regressed"
    assert drift["score_delta"] < 0
    assert drift["new_catalog_gap_indicators"] == ["LANGUAGE_METADATA_GAP"]
    NoPayloadValidator().validate(drift)


def test_mlops_pack_cli_build_writes_expected_outputs(tmp_path, monkeypatch):
    reports = _write_base_reports(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(
        app,
        [
            "mlops-pack",
            "build",
            "--reports-dir",
            str(reports),
            "--ledger-path",
            ".ecl-trainer/events.jsonl",
            "--output-dir",
            str(reports),
        ],
    )

    assert result.exit_code == 0
    paths = json.loads(result.output)
    assert (reports / paths["mlops_governance_pack_json"]).exists()
    assert (reports / paths["mlops_governance_pack_markdown"]).exists()
    assert (reports / paths["catalog_drift_snapshot_json"]).exists()
