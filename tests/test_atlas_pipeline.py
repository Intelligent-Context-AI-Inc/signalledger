from __future__ import annotations

import duckdb
import pytest
from pydantic import ValidationError

from atlas_pipeline.build_atlas import build_atlas_from_sources
from atlas_pipeline.collectors import CollectorRegistry, LocalManifestCollector
from atlas_pipeline.schemas import PUBLIC_DOMAIN_SOURCE_FLOOR, AtlasBuildManifest, AtlasSourceRecord
from ecl_trainer.core.policy import NoPayloadValidator
from ecl_trainer.oracle.atlas import _EclInternalCore
from ecl_trainer.oracle.domains import TOP_20_DOMAINS


def test_local_manifest_collectors_load_metadata_only_records() -> None:
    registry = CollectorRegistry()
    registry.register(LocalManifestCollector("atlas_sources"))

    records = registry.collect()

    assert {record.record_id for record in records} >= {
        "fineweb_edu_dataset_card",
        "dolma_ai2_dataset_docs",
        "dclm_datacomp_lm_paper",
        "sec_edgar_api_metadata",
        "sec_structured_data_taxonomies",
        "finra_regulatory_notices",
        "federal_reserve_2026_stress_scenarios",
    }
    assert all(record.source_reference_hash_sha256 for record in records)
    NoPayloadValidator().validate([record.model_dump(mode="json") for record in records])


def test_build_atlas_from_sources_appends_source_record_tables(tmp_path) -> None:
    atlas_path = build_atlas_from_sources(
        sources_root="atlas_sources",
        output_path=tmp_path / "intelligent-context-atlas.duckdb",
    )

    connection = duckdb.connect(str(atlas_path), read_only=True)
    try:
        source_count = connection.execute("SELECT COUNT(*) FROM atlas_source_records").fetchone()[0]
        tag_count = connection.execute("SELECT COUNT(*) FROM atlas_source_record_tags").fetchone()[0]
        financial_count = connection.execute(
            "SELECT COUNT(*) FROM atlas_source_records WHERE domain_id = 'financial_services'"
        ).fetchone()[0]
        manifest_hash = connection.execute("SELECT build_hash_sha256 FROM atlas_manifest").fetchone()[0]
        lifecycle_count = connection.execute("SELECT COUNT(*) FROM ecl_atlas_metadata").fetchone()[0]
    finally:
        connection.close()

    assert source_count == 125
    assert tag_count > source_count
    assert financial_count == 8
    assert lifecycle_count == 1
    assert len(manifest_hash) == 64

    summary = _EclInternalCore(atlas_path).atlas_source_summary()
    assert summary["atlas_source_record_count"] == 125
    assert summary["atlas_financial_source_record_count"] == 8
    assert summary["atlas_global_core_source_record_count"] == 3
    assert summary["atlas_seeded_domain_count"] == 20
    assert set(summary["atlas_domain_source_counts"]) == {domain.value for domain in TOP_20_DOMAINS}
    for domain in TOP_20_DOMAINS:
        assert summary["atlas_domain_source_counts"][domain.value] >= PUBLIC_DOMAIN_SOURCE_FLOOR
    assert summary["atlas_source_family_counts"]["financial_taxonomy"] == 2
    NoPayloadValidator().validate(summary)


def test_atlas_build_manifest_rejects_domain_floor_regression() -> None:
    registry = CollectorRegistry()
    registry.register(LocalManifestCollector("atlas_sources"))
    target_domain = TOP_20_DOMAINS[-1]
    target_seen = 0
    records = []
    for record in registry.collect():
        if record.domain_id == target_domain:
            target_seen += 1
            if target_seen == PUBLIC_DOMAIN_SOURCE_FLOOR:
                continue
        records.append(record)

    with pytest.raises(ValidationError, match="quality floor"):
        AtlasBuildManifest(
            build_id="metadata-only-public-seed-v1",
            atlas_version="option-b-alpha.1",
            records=records,
        )


def test_source_records_reject_long_non_hash_text() -> None:
    with pytest.raises(ValidationError, match="long non-hash text"):
        AtlasSourceRecord.model_validate(
            {
                "record_id": "bad_payload_like_record",
                "source_family": "open_science_dataset",
                "source_name": "BadSource",
                "source_version": "test",
                "source_reference_uri": "https://example.com/source",
                "global_core_relevance": True,
                "source_mixture_categories": [
                    "this_value_is_long_enough_to_look_like_raw_unapproved_text_"
                    "and_should_never_be_persisted_inside_the_atlas_seed_manifest_"
                    "because_the_seed_index_must_remain_metadata_only"
                ],
            }
        )


def test_source_records_reject_url_with_long_embedded_payload_text() -> None:
    with pytest.raises(ValidationError, match="unsafe URL text"):
        AtlasSourceRecord.model_validate(
            {
                "record_id": "bad_url_payload_like_record",
                "source_family": "open_science_dataset",
                "source_name": "BadSource",
                "source_version": "test",
                "source_reference_uri": "https://x.test/?q=" + ("synthetic-embedded-text-marker-" * 30),
                "global_core_relevance": True,
            }
        )


def test_source_records_reject_short_url_query_text() -> None:
    with pytest.raises(ValidationError, match="unsafe URL text"):
        AtlasSourceRecord.model_validate(
            {
                "record_id": "bad_short_url_query_record",
                "source_family": "open_science_dataset",
                "source_name": "BadSource",
                "source_version": "test",
                "source_reference_uri": "https://x.test/?q=payload",
                "global_core_relevance": True,
            }
        )


def test_source_records_reject_token_like_url_path_segments() -> None:
    with pytest.raises(ValidationError, match="unsafe URL text"):
        AtlasSourceRecord.model_validate(
            {
                "record_id": "bad_url_token_path_record",
                "source_family": "open_science_dataset",
                "source_name": "BadSource",
                "source_version": "test",
                "source_reference_uri": "https://example.test/sk-live-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "global_core_relevance": True,
            }
        )
