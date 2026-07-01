#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess  # nosec B404
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent
PROJECT_NAMESPACE = "quant_finance"
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
LONG_ALNUM_RE = re.compile(r"[A-Za-z0-9]{51,}")


def sha256_hex(value: str | bytes) -> str:
    data = value if isinstance(value, bytes) else value.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_sha256(value: object) -> str:
    return sha256_hex(canonical_json(value))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(command: list[str], cwd: Path, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True)  # noqa: S603  # nosec B603
    if check and result.returncode != 0:
        raise AssertionError(
            "command failed\n"
            f"cwd={cwd}\n"
            f"command={' '.join(command)}\n"
            f"stdout={result.stdout}\n"
            f"stderr={result.stderr}"
        )
    return result


def git(cwd: Path, *args: str) -> None:
    run(["git", *args], cwd)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ledger_events(ledger_path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]


def verify_hash_chain(ledger_path: Path) -> dict[str, Any]:
    previous: str | None = None
    count = 0
    for index, event in enumerate(ledger_events(ledger_path), start=1):
        if event.get("previous_event_hash_sha256") != previous:
            return {"valid": False, "event_count": count, "first_broken_link": index}
        hashable = dict(event)
        hashable["event_hash_sha256"] = ""
        hashable["signature"] = None
        expected = canonical_sha256(hashable)
        if event.get("event_hash_sha256") != expected:
            return {"valid": False, "event_count": count, "first_broken_link": index}
        previous = str(event["event_hash_sha256"])
        count += 1
    return {"valid": True, "event_count": count, "first_broken_link": None}


def assert_no_long_unapproved_alnum(testcase: unittest.TestCase, value: object) -> None:
    serialized = canonical_json(value)
    for match in LONG_ALNUM_RE.findall(serialized):
        if HEX64_RE.match(match):
            continue
        testcase.fail(f"unapproved long alpha-numeric grouping found: {match}")


class ECLComplianceSimulation(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="ecl-compliance-audit-"))
        self.workspace = self.temp_dir / "mock-financial-pr"
        self.workspace.mkdir()
        self.ledger = self.workspace / ".ecl-trainer" / "events.jsonl"
        self.reports = self.workspace / ".ecl-trainer" / "reports"

        git(self.workspace, "init")
        git(self.workspace, "config", "user.email", "qa@example.invalid")
        git(self.workspace, "config", "user.name", "ECL QA")
        (self.workspace / "configs").mkdir()
        (self.workspace / "data").mkdir()
        (self.workspace / "configs" / "training_config.yaml").write_text(
            "curriculum_mixture:\n  financial_services: 1.0\n",
            encoding="utf-8",
        )
        git(self.workspace, "add", ".")
        git(self.workspace, "commit", "-m", "baseline checkout")

        run(
            [
                sys.executable,
                "-m",
                "ecl_trainer.cli",
                "scan",
                "--project-namespace",
                PROJECT_NAMESPACE,
                "--ledger-path",
                str(self.ledger),
            ],
            self.workspace,
        )
        self.baseline_events = ledger_events(self.ledger)
        self.assertEqual(len(self.baseline_events), 1)
        self.assertTrue(verify_hash_chain(self.ledger)["valid"])

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def write_dataset_manifest(self, *, include_payload_trap: bool) -> None:
        manifest = {
            "dataset_id": "financial_news_scrap_v2",
            "industry_domain": "financial_services",
            "source_baseline_identity": "FineWebEduPublicAlpha",
            "token_profile_metrics": {
                "token_count_estimate": 31000000000,  # nosec B105
                "entropy_score": 8.204,
                "token_density_histogram_bounds": {
                    "p05": 0.019,
                    "p25": 0.101,
                    "p50": 0.257,
                    "p75": 0.526,
                    "p95": 0.918,
                },
            },
            "domain_extension_financial_tags": {
                "regulatory_framework_mapping": [
                    "SEC_2026_COMPLIANCE",
                    "FINRA_AMENDMENT_2026",
                    "FRB_STRESS_TEST",
                ],
                "fiscal_period_bounds": {"start_date": "2026-01-01", "end_date": "2026-12-31"},
                "structural_sector_ratios": {
                    "sec_filing_metadata": 0.5,
                    "market_reference_metadata": 0.3,
                    "bank_supervision_metadata": 0.2,
                },
            },
            "loss_spike_signature_hash_sha256": sha256_hex("fineweb-edu-late-stage-attention-loss-spike"),
            "structural_similarity_score": 0.982,
            "benchmark_aliases": ["mmlu"],
            "payload_policy_validation_passed": True,
        }
        if include_payload_trap:
            manifest["raw_preview_text"] = "SEC filing data for AAPL..."
        write_json(self.workspace / "data" / "financial_news_scrap_v2.json", manifest)

    def write_oracle_manifest(self) -> None:
        manifest = {
            "project_namespace": PROJECT_NAMESPACE,
            "industry_domain": "financial_services",
            "source_baseline_identity": "FineWebEduPublicAlpha",
            "dataset_identifier_hash_sha256": sha256_hex("financial_news_scrap_v2"),
            "schema_hash_sha256": sha256_hex("financial_news_schema_v2"),
            "regulatory_framework_tags": [
                "SEC_2026_COMPLIANCE",
                "FINRA_AMENDMENT_2026",
                "FRB_STRESS_TEST",
            ],
            "market_sector_distribution": {
                "equities": 0.4,
                "credit": 0.25,
                "derivatives": 0.2,
                "risk": 0.15,
            },
            "temporal_fiscal_bounds": {"start": "2026-01-01", "end": "2026-12-31"},
            "entity_coverage_density": {"issuer": 0.62, "broker": 0.21, "bank": 0.17},
            "benchmark_aliases": ["mmlu"],
            "ancestor_model_ids": [PROJECT_NAMESPACE],
        }
        write_json(self.workspace / "ecl-trainer.manifest.json", manifest)

    def preflight_validate_dataset_manifest(self) -> subprocess.CompletedProcess[str]:
        validator = (
            "import json,sys;"
            "from pathlib import Path;"
            "from ecl_trainer.core.policy import NoPayloadValidator;"
            "NoPayloadValidator().validate(json.loads(Path(sys.argv[1]).read_text()))"
        )
        return run(
            [sys.executable, "-c", validator, "data/financial_news_scrap_v2.json"],
            self.workspace,
            check=False,
        )

    def create_pr_commit(self) -> None:
        (self.workspace / "configs" / "training_config.yaml").write_text(
            "curriculum_mixture:\n"
            "  fineweb_edu_public_alpha: 0.44\n"
            "  sec_filing_metadata: 0.31\n"
            "  fed_stress_metadata: 0.25\n",
            encoding="utf-8",
        )
        git(self.workspace, "add", "configs/training_config.yaml", "data/financial_news_scrap_v2.json")
        git(self.workspace, "commit", "-m", "pr financial curriculum update")

    def run_clean_local_interceptor(self) -> None:
        # Scenario command shape:
        # ecl-trainer scan --changed-only --domain financial --policy block_on_payload_violation.
        # The current SDK writes local PR artifacts through github-pr-report, while scan remains
        # a markdown-only static scanner.
        run(
            [
                sys.executable,
                "-m",
                "ecl_trainer.cli",
                "github-pr-report",
                "--project-namespace",
                PROJECT_NAMESPACE,
                "--ledger-path",
                ".ecl-trainer/events.jsonl",
                "--output-dir",
                ".ecl-trainer/reports",
                "--risk-policy",
                "block_on_payload_violation",
                "--changed-only",
                "--domain",
                "financial_services",
                "--domain-selection-mode",
                "explicit",
            ],
            self.workspace,
        )

    def assert_native_artifacts_are_not_harness_enriched(self) -> None:
        source = Path(__file__).read_text(encoding="utf-8")
        self.assertNotIn("open(" + '"a"' + ")", source)
        self.assertNotIn("def enrich_" + "risk_report", source)
        self.assertNotIn("def enrich_" + "financial_passport", source)

    def test_end_to_end_financial_preflight_audit(self) -> None:
        self.write_dataset_manifest(include_payload_trap=True)
        self.create_pr_commit()

        rejected = self.preflight_validate_dataset_manifest()
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("raw_preview_text", rejected.stderr + rejected.stdout)
        self.assertEqual(ledger_events(self.ledger), self.baseline_events)

        self.write_dataset_manifest(include_payload_trap=False)
        self.write_oracle_manifest()
        clean = self.preflight_validate_dataset_manifest()
        self.assertEqual(clean.returncode, 0, clean.stderr + clean.stdout)
        self.run_clean_local_interceptor()

        self.assert_native_artifacts_are_not_harness_enriched()
        self.assert_no_payload_enforcement()
        self.assert_step_zero_curriculum_optimization()
        self.assert_hash_chain_continuity()
        self.assert_financial_domain_compliance()

    def assert_no_payload_enforcement(self) -> None:
        events = ledger_events(self.ledger)
        verification = load_json(self.reports / "verification.json")
        for event in events:
            policy = event.get("payload_policy", {})
            self.assertIs(policy.get("raw_payload_absent"), True)
            self.assertNotIn("raw_preview_text", canonical_json(event))
        self.assertTrue(verification["valid"])
        assert_no_long_unapproved_alnum(self, events)
        assert_no_long_unapproved_alnum(self, verification)

    def assert_step_zero_curriculum_optimization(self) -> None:
        risk_report = (self.reports / "risk-report.md").read_text(encoding="utf-8")
        self.assertRegex(risk_report, r"\b(CRITICAL|WARN)\b")
        self.assertIn("FineWebEduPublicAlpha", risk_report)
        self.assertTrue("model inbreeding" in risk_report.lower() or "contamination" in risk_report.lower())
        for item in ("remove_benchmark_overlap", "rotate_lineage_source", "regenerate_metadata_fingerprint"):
            self.assertIn(item, risk_report)

    def assert_hash_chain_continuity(self) -> None:
        verification = load_json(self.reports / "verification.json")
        self.assertIs(verification["valid"], True)
        self.assertIsNone(verification["first_broken_link"])
        events = ledger_events(self.ledger)
        self.assertGreaterEqual(len(events), 7)
        baseline = events[0]
        self.assertEqual(events[1]["previous_event_hash_sha256"], baseline["event_hash_sha256"])
        self.assertEqual(
            [event["event_type"] for event in events[1:]],
            [
                "ci_scan",
                "curriculum_blueprint_generated",
                "oracle_shield_run",
                "compliance_passport_generated",
                "risk_gate_decision",
                "diff_free_pr_evidence",
                "local_artifact_export",
            ],
        )
        for previous, current in zip(events, events[1:], strict=False):
            self.assertEqual(current["previous_event_hash_sha256"], previous["event_hash_sha256"])
        self.assertEqual(verify_hash_chain(self.ledger), verification)

    def assert_financial_domain_compliance(self) -> None:
        passport = (self.reports / "compliance-passport.md").read_text(encoding="utf-8")
        self.assertIn("SEC EDGAR tax structures", passport)
        self.assertIn("FINRA oversight definitions", passport)
        self.assertIn("2026 Federal Reserve macro scenario matrices", passport)
        self.assertIn("financial_services", passport)


if __name__ == "__main__":
    unittest.main(verbosity=2)
