from __future__ import annotations

import json
from pathlib import Path

from ecl_trainer.core.policy import HEX_SHA256_RE, NoPayloadValidator

FIXTURE_PATH = Path("examples/ecl_records/financial-services-atlas-seed-ledger.sample.json")


def test_financial_services_seed_fixture_is_metadata_only():
    records = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    assert len(records) == 4
    NoPayloadValidator().validate(records)
    assert all(
        record["data_profile_generation"] == "SYNTHETIC_ALPHA_SAMPLE_FOR_SCHEMA_VALIDATION_ONLY"
        for record in records
    )


def test_financial_services_seed_fixture_hash_chain_is_continuous():
    records = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    previous_hash = None

    for record in records:
        signatures = record["lineage_cryptographic_signatures"]
        assert signatures["previous_record_sha256"] == previous_hash
        assert HEX_SHA256_RE.match(signatures["source_manifest_sha256"])
        assert HEX_SHA256_RE.match(signatures["record_self_sha256"])
        previous_hash = signatures["record_self_sha256"]


def test_financial_services_seed_fixture_schema_density():
    records = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    for record in records:
        token_profile = record["token_profile_metrics"]
        histogram = token_profile["token_density_histogram_bounds"]
        financial_tags = record["domain_extension_financial_tags"]
        assertions = record["pre_flight_shield_assertions"]

        assert token_profile["token_count_estimate"] >= 10_000_000_000
        assert set(histogram) == {"p05", "p25", "p50", "p75", "p95"}
        assert list(histogram.values()) == sorted(histogram.values())
        assert len(financial_tags["regulatory_framework_mapping"]) >= 3
        assert abs(sum(financial_tags["structural_sector_ratios"].values()) - 1.0) < 0.000001
        assert assertions["payload_policy_validation_passed"] is True
        assert 0.0 <= assertions["model_inbreeding_risk"] <= 1.0


def test_financial_services_seed_fixture_tracks_negative_delta():
    records = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    deltas = [
        delta["delta_impact_coefficient"]
        for record in records
        for delta in record["historical_evaluation_deltas"]
    ]

    assert any(delta < 0 for delta in deltas)
