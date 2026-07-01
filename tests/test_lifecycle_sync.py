from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path

import duckdb
import pytest
from typer.testing import CliRunner

from ecl_trainer.cli import app
from ecl_trainer.core.policy import NoPayloadValidator, sha256_hex
from ecl_trainer.core.serialization import canonical_json
from ecl_trainer.lifecycle.sync import OfflineSyncManager
from ecl_trainer.oracle.atlas import DEFAULT_ATLAS_VERSION_TAG, build_option_b_atlas


def test_offline_patch_applies_metadata_only_source_records(tmp_path) -> None:
    atlas_path = build_option_b_atlas(tmp_path / "atlas.duckdb")
    patch_path = _write_patch_archive(tmp_path / "patch.tar.gz")

    report = OfflineSyncManager(atlas_path).apply_patch(patch_path)

    assert report["offline_patch_status"] == "APPLIED"
    assert report["new_atlas_version_tag"] == "v0.1.0rc1-2026.Q4"
    assert report["applied_record_count"] == 1
    NoPayloadValidator().validate(report)

    connection = duckdb.connect(str(atlas_path), read_only=True)
    try:
        source_count = connection.execute(
            "SELECT COUNT(*) FROM atlas_source_records WHERE record_id = 'fed_stress_patch_metadata'"
        ).fetchone()[0]
        status = connection.execute(
            "SELECT domain_status FROM domain_extension_manifest WHERE domain_id = 'healthcare_clinical'"
        ).fetchone()[0]
        version = connection.execute("SELECT atlas_version_tag FROM ecl_atlas_metadata").fetchone()[0]
    finally:
        connection.close()

    assert source_count == 1
    assert status == "missing_seed"
    assert version == "v0.1.0rc1-2026.Q4"


def test_offline_patch_cli_writes_report(tmp_path) -> None:
    atlas_path = build_option_b_atlas(tmp_path / "atlas.duckdb")
    patch_path = _write_patch_archive(tmp_path / "patch.tar.gz")
    output_path = tmp_path / "offline-patch-report.json"

    result = CliRunner().invoke(
        app,
        [
            "lifecycle",
            "apply-patch",
            "--patch-archive",
            str(patch_path),
            "--atlas-path",
            str(atlas_path),
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    assert output_path.exists()
    assert "offline_patch_status" in result.output


def test_offline_patch_rejects_path_traversal(tmp_path) -> None:
    atlas_path = build_option_b_atlas(tmp_path / "atlas.duckdb")
    patch_path = _write_patch_archive(tmp_path / "bad.tar.gz", extra_members={"../escape.json": b"{}"})

    with pytest.raises(ValueError, match="traverse"):
        OfflineSyncManager(atlas_path).apply_patch(patch_path)


def test_offline_patch_rejects_member_hash_mismatch(tmp_path) -> None:
    atlas_path = build_option_b_atlas(tmp_path / "atlas.duckdb")
    patch_path = _write_patch_archive(tmp_path / "bad.tar.gz", corrupt_declared_hash=True)

    with pytest.raises(ValueError, match="hash mismatch"):
        OfflineSyncManager(atlas_path).apply_patch(patch_path)


def test_offline_patch_rejects_payload_like_source_records(tmp_path) -> None:
    atlas_path = build_option_b_atlas(tmp_path / "atlas.duckdb")
    records = [_source_record() | {"raw_text": "blocked"}]
    patch_path = _write_patch_archive(tmp_path / "bad.tar.gz", records=records)

    with pytest.raises(Exception, match="Payload-like key blocked|Extra inputs are not permitted"):
        OfflineSyncManager(atlas_path).apply_patch(patch_path)


def _write_patch_archive(
    path: Path,
    *,
    records: list[dict] | None = None,
    extra_members: dict[str, bytes] | None = None,
    corrupt_declared_hash: bool = False,
) -> Path:
    records_bytes = json.dumps(records or [_source_record()], sort_keys=True).encode("utf-8")
    declared_hash = "0" * 64 if corrupt_declared_hash else sha256_hex(records_bytes)
    manifest = {
        "schema_version": "1.0",
        "patch_id": "patch_2026_q4_financial_metadata",
        "target_atlas_version_tag": DEFAULT_ATLAS_VERSION_TAG,
        "new_atlas_version_tag": "v0.1.0rc1-2026.Q4",
        "compiled_at": "2026-09-30T00:00:00Z",
        "supported_domains_mask": (1 << 20) - 1,
        "patch_signature_hash_sha256": "",
        "files": [
            {
                "member_path": "records/source_records.json",
                "member_hash_sha256": declared_hash,
                "purpose": "atlas_source_records",
                "record_count": len(records or [_source_record()]),
            }
        ],
        "operations": [
            {
                "operation_type": "upsert_atlas_source_records",
                "member_path": "records/source_records.json",
            },
            {
                "operation_type": "set_domain_extension_statuses",
                "domain_extension_status": {"healthcare_clinical": "missing_seed"},
            },
        ],
    }
    manifest["patch_signature_hash_sha256"] = _signature_hash(manifest)
    manifest_bytes = json.dumps(manifest, sort_keys=True).encode("utf-8")

    with tarfile.open(path, "w:gz") as archive:
        _add_member(archive, "ecl_delta_manifest.json", manifest_bytes)
        _add_member(archive, "records/source_records.json", records_bytes)
        for name, data in (extra_members or {}).items():
            _add_member(archive, name, data)
    return path


def _add_member(archive: tarfile.TarFile, name: str, data: bytes) -> None:
    info = tarfile.TarInfo(name=name)
    info.size = len(data)
    archive.addfile(info, io.BytesIO(data))


def _source_record() -> dict:
    return {
        "record_id": "fed_stress_patch_metadata",
        "source_family": "financial_stress_test",
        "source_name": "FRB Stress Scenario Metadata",
        "source_version": "2026-q4",
        "source_reference_uri": "https://www.federalreserve.gov/supervisionreg/stress-tests-capital-planning.htm",
        "domain_id": "financial_services",
        "global_core_relevance": False,
        "benchmark_count": 1,
        "license_descriptor": "public_metadata_reference",
        "regulatory_source_categories": ["macro_stress_scenario"],
        "financial_taxonomy_tags": ["stress_testing"],
    }


def _signature_hash(manifest: dict) -> str:
    payload = dict(manifest)
    payload["patch_signature_hash_sha256"] = ""
    return sha256_hex(canonical_json(payload))
