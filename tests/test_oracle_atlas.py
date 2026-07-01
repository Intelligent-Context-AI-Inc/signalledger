import json

import duckdb
import pytest
from typer.testing import CliRunner

from ecl_trainer.ci.artifacts import LocalCIArtifactGenerator
from ecl_trainer.cli import app
from ecl_trainer.core.exceptions import SovereignDataExfiltrationException
from ecl_trainer.core.ledger import AppendOnlyEventLog
from ecl_trainer.core.models import CIScanEvent, RiskSummary
from ecl_trainer.core.policy import sha256_hex
from ecl_trainer.oracle.atlas import _EclInternalCore, build_option_b_atlas
from ecl_trainer.oracle.blueprint import CurriculumBlueprintOracle
from ecl_trainer.oracle.domains import IndustryDomain
from ecl_trainer.oracle.models import validate_oracle_metadata
from ecl_trainer.oracle.passport import RegulatoryPassportCompiler
from ecl_trainer.oracle.shield import EclPreFlightShield


def _atlas(tmp_path):
    return _EclInternalCore(build_option_b_atlas(tmp_path / "atlas.duckdb"))


def _financial_manifest():
    return {
        "project_namespace": "project",
        "industry_domain": "financial_services",
        "dataset_identifier_hash_sha256": sha256_hex("dataset"),
        "schema_hash_sha256": sha256_hex("schema"),
        "regulatory_framework_tags": ["SEC_2026_COMPLIANCE", "FRB_STRESS_TEST"],
        "market_sector_distribution": {"equities": 0.45, "fixed_income": 0.55},
        "temporal_fiscal_bounds": {"start": "2026-01-01", "end": "2026-03-31"},
        "entity_coverage_density": {"issuer_density": 0.4, "counterparty_density": 0.6},
    }


def test_option_b_atlas_is_read_only_and_registers_top_20(tmp_path):
    path = build_option_b_atlas(tmp_path / "atlas.duckdb")
    connection = duckdb.connect(str(path), read_only=True)
    try:
        rows = connection.execute("SELECT COUNT(*) FROM domain_extension_manifest").fetchone()
        assert rows[0] == 20
        with pytest.raises(duckdb.Error):
            connection.execute("CREATE TABLE blocked(id INTEGER)")
    finally:
        connection.close()


def test_auto_core_selects_financial_and_explicit_uses_public_seed_domain(tmp_path):
    core = _atlas(tmp_path)
    blueprint = CurriculumBlueprintOracle(core=core).generate_step_zero_blueprint(
        [_financial_manifest()],
        {"release_readiness": 1.0},
    )
    assert blueprint["global_core_used"] is True
    assert blueprint["enabled_domains"] == [IndustryDomain.FINANCIAL_SERVICES.value]
    assert "filings_target" in blueprint["target_mixture_boundaries"]

    legal = CurriculumBlueprintOracle(
        core=core,
        enabled_domains="legal_regulatory",
        domain_selection_mode="explicit",
    ).generate_step_zero_blueprint([_financial_manifest()], {"release_readiness": 1.0})
    assert legal["enabled_domains"] == [IndustryDomain.LEGAL_REGULATORY.value]
    assert legal["skipped_domains"] == []


def test_core_only_produces_no_domain_sections(tmp_path):
    core = _atlas(tmp_path)
    blueprint = CurriculumBlueprintOracle(core=core, domain_selection_mode="core_only").generate_step_zero_blueprint(
        [_financial_manifest()],
        {"release_readiness": 1.0},
    )
    assert blueprint["enabled_domains"] == []
    assert blueprint["target_mixture_boundaries"] == {"structural_core_target": 1.0}


def test_preflight_shield_quarantines_lineage_and_keeps_financial_scope(tmp_path):
    core = _atlas(tmp_path)
    manifest = _financial_manifest() | {"ancestor_model_ids": ["project"]}
    alerts = EclPreFlightShield(core=core).validate_run_manifest(manifest)
    assert any(alert["action_required"] == "QUARANTINE" for alert in alerts)
    assert all("healthcare" not in json.dumps(alert).lower() for alert in alerts)


def test_financial_manifest_rejects_long_raw_text():
    manifest = _financial_manifest() | {"unsafe_note": "x" * 80}
    with pytest.raises(SovereignDataExfiltrationException):
        validate_oracle_metadata(manifest)


def test_regulatory_passport_domain_cleanliness(tmp_path):
    core = _atlas(tmp_path)
    ledger = tmp_path / "events.jsonl"
    AppendOnlyEventLog(ledger).append(
        CIScanEvent(
            project_namespace="project",
            repository_root_hash_sha256=sha256_hex("repo"),
            ci_provider="local",
            ci_run_id="run",
            commit_hash_sha256=sha256_hex("commit"),
            risk_summary=RiskSummary(),
            report_hash_sha256=sha256_hex("report"),
        )
    )
    compiler = RegulatoryPassportCompiler(ledger, enabled_domains="financial_services", core=core)
    report = compiler.compile_compliance_passport(None)
    rendered = compiler.render_markdown(report)
    assert "financial regulatory tags" in rendered
    assert "SEC EDGAR tax structures" in rendered
    assert "FINRA oversight definitions" in rendered
    assert "2026 Federal Reserve macro scenario matrices" in rendered
    assert "HIPAA" not in rendered
    assert "legal" not in rendered.lower()


def test_oracle_cli_and_ci_artifacts_include_domain_metadata(tmp_path, monkeypatch):
    core = _atlas(tmp_path)
    monkeypatch.setenv("ECL_ATLAS_PATH", str(core.atlas_path))
    manifest_path = tmp_path / "ecl-trainer.manifest.json"
    target_path = tmp_path / "target.json"
    manifest_path.write_text(json.dumps(_financial_manifest()), encoding="utf-8")
    target_path.write_text('{"release_readiness": 1.0}', encoding="utf-8")
    result = CliRunner().invoke(
        app,
        [
            "oracle",
            "blueprint",
            "--manifest",
            str(manifest_path),
            "--target",
            str(target_path),
        ],
    )
    assert result.exit_code == 0
    assert "financial_services" in result.output

    monkeypatch.chdir(tmp_path)
    LocalCIArtifactGenerator().generate(
        project_namespace="org/project",
        ledger_path=".ecl/events.jsonl",
        output_dir=".ecl/reports",
        changed_only=False,
        risk_policy="report_only",
    )
    pr_comment = (tmp_path / ".ecl/reports/pr-comment.md").read_text(encoding="utf-8")
    assert "Intelligent Context Atlas" in pr_comment
    assert "financial_services" in pr_comment
    assert "Atlas source records" in pr_comment
    events = [
        json.loads(line)
        for line in (tmp_path / ".ecl/events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert [event["event_type"] for event in events] == [
        "ci_scan",
        "curriculum_blueprint_generated",
        "oracle_shield_run",
        "compliance_passport_generated",
        "risk_gate_decision",
        "diff_free_pr_evidence",
        "local_artifact_export",
    ]
    assert events[-1]["previous_event_hash_sha256"] == events[-2]["event_hash_sha256"]
