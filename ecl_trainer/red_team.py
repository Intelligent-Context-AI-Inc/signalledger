from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from atlas_pipeline.schemas import AtlasSourceRecord
from ecl_trainer.core.exceptions import PayloadExfiltrationException, SovereignDataExfiltrationException
from ecl_trainer.core.models import DatasetRegisteredEvent
from ecl_trainer.core.policy import NoPayloadValidator, sha256_hex
from ecl_trainer.oracle.shield import EclPreFlightShield

EXPECTED_EXCEPTIONS = {
    "PayloadExfiltrationException": PayloadExfiltrationException,
    "SovereignDataExfiltrationException": SovereignDataExfiltrationException,
    "ValidationError": ValidationError,
    "ValueError": ValueError,
}

BUILTIN_FIXTURES: tuple[dict[str, Any], ...] = (
    {
        "fixture_id": "builtin_abusive_uri_metadata_001",
        "surface": "atlas_source_record",
        "metadata": {
            "record_id": "atlas_uri_case",
            "source_family": "open_science_dataset",
            "source_name": "public_meta",
            "source_version": "v1",
            "source_reference_uri": "https://example.test/source?q=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "global_core_relevance": True,
        },
        "expected_exception": "ValidationError",
    },
    {
        "fixture_id": "builtin_payload_key_smuggling_rawpreview_001",
        "surface": "no_payload_validator",
        "metadata": {"rawpreview": "blocked"},
        "expected_exception": "PayloadExfiltrationException",
    },
    {
        "fixture_id": "builtin_payload_key_smuggling_fulltext_001",
        "surface": "no_payload_validator",
        "metadata": {"fulltext": "blocked"},
        "expected_exception": "PayloadExfiltrationException",
    },
    {
        "fixture_id": "builtin_payload_key_smuggling_embeddingvec_001",
        "surface": "no_payload_validator",
        "metadata": {"embeddingvec": "blocked"},
        "expected_exception": "PayloadExfiltrationException",
    },
    {
        "fixture_id": "builtin_benchmark_alias_overlap_001",
        "surface": "preflight_shield",
        "enabled_domains": "financial_services",
        "domain_selection_mode": "explicit",
        "metadata": {
            "industry_domain": "financial_services",
            "source_baseline_identity": "FineWebEduPublicAlpha",
            "dataset_identifier_hash_sha256": sha256_hex("builtin-benchmark"),
            "schema_hash_sha256": sha256_hex("builtin-schema"),
            "benchmark_aliases": ["mmlu"],
            "regulatory_framework_tags": ["SEC_2026_COMPLIANCE"],
        },
        "expected_result": "critical_alert",
        "expected_check_id": "global_benchmark_overlap",
    },
    {
        "fixture_id": "builtin_lineage_feedback_loop_001",
        "surface": "preflight_shield",
        "enabled_domains": "financial_services",
        "domain_selection_mode": "explicit",
        "metadata": {
            "project_namespace": "lineage_loop_profile",
            "industry_domain": "financial_services",
            "source_baseline_identity": "lineage_loop_profile",
            "dataset_identifier_hash_sha256": sha256_hex("builtin-lineage"),
            "schema_hash_sha256": sha256_hex("builtin-lineage-schema"),
            "regulatory_framework_tags": ["SEC_2026_COMPLIANCE"],
            "ancestor_model_ids": ["lineage_loop_profile"],
        },
        "expected_result": "critical_alert",
        "expected_check_id": "global_lineage_loop",
    },
    {
        "fixture_id": "builtin_domain_crossing_financial_hipaa_001",
        "surface": "preflight_shield",
        "enabled_domains": "financial_services",
        "domain_selection_mode": "explicit",
        "metadata": {
            "project_namespace": "red_team_fin",
            "industry_domain": "financial_services",
            "dataset_identifier_hash_sha256": sha256_hex("builtin-domain-crossing"),
            "schema_hash_sha256": sha256_hex("builtin-domain-crossing-schema"),
            "regulatory_framework_tags": ["SEC_2026_COMPLIANCE", "HIPAA"],
        },
        "expected_result": "critical_alert",
        "expected_check_id": "financial_domain_crossing_tags",
    },
    {
        "fixture_id": "builtin_invalid_hash_001",
        "surface": "dataset_registered_event",
        "metadata": {
            "dataset_identifier_hash_sha256": "not_a_sha256",
            "metadata_record_hash_sha256": sha256_hex("builtin-record"),
        },
        "expected_exception": "ValidationError",
    },
    {
        "fixture_id": "builtin_safe_control_financial_001",
        "surface": "preflight_shield",
        "enabled_domains": "financial_services",
        "domain_selection_mode": "explicit",
        "metadata": {
            "project_namespace": "red_team_fin",
            "industry_domain": "financial_services",
            "dataset_identifier_hash_sha256": sha256_hex("builtin-safe-financial"),
            "schema_hash_sha256": sha256_hex("builtin-safe-financial-schema"),
            "regulatory_framework_tags": ["SEC_2026_COMPLIANCE"],
            "market_sector_distribution": {"equities": 0.5, "fixed_income": 0.5},
            "temporal_fiscal_bounds": {"start": "2026-01-01", "end": "2026-03-31"},
            "entity_coverage_density": {"issuer_density": 0.5, "counterparty_density": 0.5},
        },
        "expected_result": "info_alert",
    },
)


def load_fixture(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("red-team fixture must be a JSON object")
    return data


def iter_fixture_paths(root: str | Path) -> list[Path]:
    return sorted(Path(root).glob("**/*.json"))


def run_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    fixture_id = str(fixture["fixture_id"])
    surface = str(fixture["surface"])
    metadata = fixture.get("metadata", {})
    expected_exception = fixture.get("expected_exception")
    expected_result = fixture.get("expected_result")

    try:
        observed = _execute_surface(surface, metadata, fixture)
    except Exception as exc:
        if expected_exception and isinstance(exc, EXPECTED_EXCEPTIONS[str(expected_exception)]):
            return {
                "fixture_id": fixture_id,
                "surface": surface,
                "expected_result": expected_exception,
                "observed_result": type(exc).__name__,
                "passed": True,
            }
        return {
            "fixture_id": fixture_id,
            "surface": surface,
            "expected_result": str(expected_exception or expected_result),
            "observed_result": type(exc).__name__,
            "passed": False,
        }

    passed = _matches_expected(observed, str(expected_result or "pass"), fixture)
    return {
        "fixture_id": fixture_id,
        "surface": surface,
        "expected_result": str(expected_result),
        "observed_result": observed["observed_result"],
        "passed": passed,
    }


def run_corpus(root: str | Path) -> dict[str, Any]:
    paths = iter_fixture_paths(root)
    packaged_fixtures = [] if paths else _load_packaged_fixtures()
    if paths:
        fixtures = [load_fixture(path) for path in paths]
        corpus_source = "fixture_directory"
    elif packaged_fixtures:
        fixtures = packaged_fixtures
        corpus_source = "packaged_fixture_directory"
    else:
        fixtures = list(BUILTIN_FIXTURES)
        corpus_source = "builtin_full_corpus"
    results = [run_fixture(fixture) for fixture in fixtures]
    report = {
        "corpus_source": corpus_source,
        "fixture_count": len(results),
        "passed_count": sum(1 for result in results if result["passed"]),
        "failed_count": sum(1 for result in results if not result["passed"]),
        "results": results,
        "payload_policy": "metadata_only",
    }
    NoPayloadValidator().validate(report)
    return report


def _load_packaged_fixtures() -> list[dict[str, Any]]:
    try:
        root = resources.files("ecl_trainer.red_team_fixtures")
    except ModuleNotFoundError:
        return []
    fixtures = []
    for path in sorted(root.iterdir(), key=lambda item: item.name):
        if path.name.endswith(".json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                fixtures.append(data)
    return fixtures


def _execute_surface(surface: str, metadata: Any, fixture: dict[str, Any]) -> dict[str, Any]:
    if surface == "no_payload_validator":
        NoPayloadValidator().validate(metadata)
        return {"observed_result": "pass"}
    if surface == "preflight_shield":
        alerts = EclPreFlightShield(
            enabled_domains=str(fixture.get("enabled_domains", "")),
            domain_selection_mode=str(fixture.get("domain_selection_mode", "auto")),
        ).validate_run_manifest(metadata)
        return {
            "observed_result": "alerts",
            "alerts": alerts,
            "check_ids": [str(alert["check_id"]) for alert in alerts],
            "severities": [str(alert["severity"]) for alert in alerts],
        }
    if surface == "atlas_source_record":
        AtlasSourceRecord.model_validate(metadata)
        return {"observed_result": "pass"}
    if surface == "dataset_registered_event":
        DatasetRegisteredEvent(project_namespace="red_team", **metadata)
        return {"observed_result": "pass"}
    raise ValueError(f"Unsupported red-team surface: {surface}")


def _matches_expected(observed: dict[str, Any], expected_result: str, fixture: dict[str, Any]) -> bool:
    if expected_result == "pass":
        return observed["observed_result"] == "pass"
    if expected_result == "critical_alert":
        return (
            str(fixture.get("expected_check_id")) in set(observed.get("check_ids", []))
            and "CRITICAL" in set(observed.get("severities", []))
        )
    if expected_result == "warn_alert":
        return (
            str(fixture.get("expected_check_id")) in set(observed.get("check_ids", []))
            and "WARN" in set(observed.get("severities", []))
        )
    if expected_result == "info_alert":
        return "INFO" in set(observed.get("severities", []))
    return False
