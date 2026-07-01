from __future__ import annotations

from datetime import UTC, datetime, timedelta

import duckdb
from typer.testing import CliRunner

from ecl_trainer.cli import app
from ecl_trainer.core.policy import NoPayloadValidator
from ecl_trainer.lifecycle.freshness import AtlasFreshnessValidator, LifecycleStatus
from ecl_trainer.oracle.atlas import DEFAULT_ATLAS_COMPILED_AT, build_option_b_atlas


def test_lifecycle_current_stale_and_muted(tmp_path) -> None:
    atlas_path = build_option_b_atlas(tmp_path / "atlas.duckdb")
    validator = AtlasFreshnessValidator(atlas_path=atlas_path)

    current = validator.evaluate_atlas_lifecycle(DEFAULT_ATLAS_COMPILED_AT + timedelta(days=90))
    stale = validator.evaluate_atlas_lifecycle(DEFAULT_ATLAS_COMPILED_AT + timedelta(days=91))
    muted = validator.evaluate_atlas_lifecycle(
        DEFAULT_ATLAS_COMPILED_AT + timedelta(days=365),
        ignore_staleness=True,
    )

    assert current["lifecycle_status"] == LifecycleStatus.CURRENT.value
    assert stale["lifecycle_status"] == LifecycleStatus.STALE.value
    assert muted["lifecycle_status"] == LifecycleStatus.MUTED.value
    NoPayloadValidator().validate([current, stale, muted])


def test_lifecycle_missing_metadata_is_unknown_and_non_blocking(tmp_path) -> None:
    atlas_path = tmp_path / "atlas_without_lifecycle.duckdb"
    connection = duckdb.connect(str(atlas_path))
    try:
        connection.execute("CREATE TABLE atlas_manifest(atlas_version VARCHAR)")
    finally:
        connection.close()

    report = AtlasFreshnessValidator(atlas_path=atlas_path).evaluate_atlas_lifecycle(datetime.now(UTC))

    assert report["lifecycle_status"] == LifecycleStatus.UNKNOWN.value
    assert report["atlas_version_tag"] == "unknown"
    NoPayloadValidator().validate(report)


def test_lifecycle_pr_comment_block_is_metadata_only(tmp_path) -> None:
    atlas_path = build_option_b_atlas(tmp_path / "atlas.duckdb")
    validator = AtlasFreshnessValidator(atlas_path=atlas_path)
    stale = validator.evaluate_atlas_lifecycle(DEFAULT_ATLAS_COMPILED_AT + timedelta(days=120))

    block = validator.generate_pr_comment_block(stale)

    assert "Atlas Lifecycle" in block
    assert "STALE" in block
    assert "coordinate_image_pull_update" in block
    NoPayloadValidator().validate({"markdown_summary": block})


def test_lifecycle_cli_check_writes_report(tmp_path) -> None:
    atlas_path = build_option_b_atlas(tmp_path / "atlas.duckdb")
    output_path = tmp_path / "lifecycle-report.json"

    result = CliRunner().invoke(
        app,
        [
            "lifecycle",
            "check",
            "--atlas-path",
            str(atlas_path),
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    assert output_path.exists()
    assert "lifecycle_status" in result.output
