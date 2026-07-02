from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

from atlas_pipeline.collectors import CollectorRegistry, LocalManifestCollector
from atlas_pipeline.schemas import AtlasBuildManifest, AtlasSourceRecord
from ecl_trainer.core.policy import NoPayloadValidator
from ecl_trainer.core.serialization import canonical_sha256
from ecl_trainer.oracle.atlas import build_option_b_atlas, refresh_atlas_manifest


def build_atlas_from_sources(*, sources_root: str | Path, output_path: str | Path) -> Path:
    registry = CollectorRegistry()
    registry.register(LocalManifestCollector(sources_root))
    records = registry.collect()
    manifest = AtlasBuildManifest(
        build_id="metadata-only-public-seed-v1",
        atlas_version="option-b-alpha.1",
        records=records,
    )
    NoPayloadValidator().validate(manifest)
    path = build_option_b_atlas(output_path)
    _append_source_records(path, records)
    return path


def _append_source_records(path: Path, records: list[AtlasSourceRecord]) -> None:
    connection = duckdb.connect(str(path))
    try:
        connection.execute(
            """
            CREATE TABLE atlas_source_records (
                record_id VARCHAR,
                source_family VARCHAR,
                source_name VARCHAR,
                source_version VARCHAR,
                source_reference_hash_sha256 VARCHAR,
                domain_id VARCHAR,
                global_core_relevance BOOLEAN,
                token_count_estimate BIGINT,
                benchmark_count BIGINT,
                license_descriptor VARCHAR
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE atlas_source_record_tags (
                record_id VARCHAR,
                tag_family VARCHAR,
                tag_value VARCHAR
            )
            """
        )
        connection.executemany(
            "INSERT INTO atlas_source_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    record.record_id,
                    record.source_family.value,
                    record.source_name,
                    record.source_version,
                    record.source_reference_hash_sha256,
                    record.domain_id.value if record.domain_id else None,
                    record.global_core_relevance,
                    record.token_count_estimate,
                    record.benchmark_count,
                    record.license_descriptor,
                )
                for record in records
            ],
        )
        tag_rows: list[tuple[str, str, str]] = []
        for record in records:
            for value in record.source_mixture_categories:
                tag_rows.append((record.record_id, "source_mixture", value))
            for value in record.filtering_methods:
                tag_rows.append((record.record_id, "filtering", value))
            for value in record.deduplication_methods:
                tag_rows.append((record.record_id, "deduplication", value))
            for value in record.evaluation_metric_names:
                tag_rows.append((record.record_id, "evaluation_metric", value))
            for value in record.regulatory_source_categories:
                tag_rows.append((record.record_id, "regulatory_source", value))
            for value in record.financial_taxonomy_tags:
                tag_rows.append((record.record_id, "financial_taxonomy", value))
            for value in record.domain_taxonomy_tags:
                tag_rows.append((record.record_id, "domain_taxonomy", value))
        if tag_rows:
            connection.executemany("INSERT INTO atlas_source_record_tags VALUES (?, ?, ?)", tag_rows)
        build_hash = refresh_atlas_manifest(connection, pack_visibility="public_alpha_fixture")
        lifecycle = connection.execute(
            "SELECT atlas_version_tag, compiled_at, supported_domains_mask FROM ecl_atlas_metadata LIMIT 1"
        ).fetchone()
        if lifecycle is not None:
            metadata_payload = {
                "atlas_version_tag": lifecycle[0],
                "compiled_at": lifecycle[1].isoformat(),
                "supported_domains_mask": int(lifecycle[2]),
                "build_hash_sha256": build_hash,
            }
            connection.execute(
                "UPDATE ecl_atlas_metadata SET atlas_signature = ?",
                [canonical_sha256(metadata_payload)],
            )
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Build metadata-only Intelligent Context Atlas from source records")
    parser.add_argument("--sources-root", default="atlas_sources")
    parser.add_argument("--output-path", default="atlas_artifacts/option_b_alpha/intelligent-context-atlas.duckdb")
    args = parser.parse_args()
    build_atlas_from_sources(sources_root=args.sources_root, output_path=args.output_path)


if __name__ == "__main__":
    main()
