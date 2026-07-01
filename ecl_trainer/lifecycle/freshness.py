from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import Field

from ecl_trainer.core.models import FrozenModel
from ecl_trainer.core.policy import NoPayloadValidator, validate_rendered_text
from ecl_trainer.oracle.atlas import _EclInternalCore

FRESHNESS_WINDOW_DAYS = 90


class LifecycleStatus(StrEnum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    MUTED = "MUTED"
    UNKNOWN = "UNKNOWN"


class LifecycleStateReport(FrozenModel):
    atlas_version_tag: str
    compiled_at: datetime | None = None
    delta_days_active: int | None = None
    lifecycle_status: LifecycleStatus
    domain_enforcement_messages: list[str] = Field(default_factory=list)
    atlas_signature_hash_sha256: str = ""
    payload_policy: str = "passed"


class AtlasFreshnessValidator:
    def __init__(self, atlas_path: str | Path | None = None, *, core: _EclInternalCore | None = None) -> None:
        self.core = core or _EclInternalCore(atlas_path)

    def evaluate_atlas_lifecycle(
        self,
        current_system_time: datetime,
        ignore_staleness: bool = False,
    ) -> dict[str, Any]:
        metadata = self.core.atlas_lifecycle_metadata()
        current_time = _as_utc(current_system_time)
        if metadata is None:
            report = LifecycleStateReport(
                atlas_version_tag="unknown",
                lifecycle_status=LifecycleStatus.UNKNOWN,
                domain_enforcement_messages=["atlas_lifecycle_metadata_missing"],
            )
            return self._dump(report)

        compiled_at = _as_utc(metadata["compiled_at"])
        delta_days = max(0, (current_time - compiled_at).days)
        if ignore_staleness:
            status = LifecycleStatus.MUTED
            messages = ["atlas_staleness_notifications_muted"]
        elif delta_days <= FRESHNESS_WINDOW_DAYS:
            status = LifecycleStatus.CURRENT
            messages = ["atlas_lifecycle_current"]
        else:
            status = LifecycleStatus.STALE
            messages = ["atlas_lifecycle_stale_coordinate_image_update"]

        report = LifecycleStateReport(
            atlas_version_tag=str(metadata["atlas_version_tag"]),
            compiled_at=compiled_at,
            delta_days_active=delta_days,
            lifecycle_status=status,
            domain_enforcement_messages=messages,
            atlas_signature_hash_sha256=str(metadata["atlas_signature_hash_sha256"]),
        )
        return self._dump(report)

    def generate_pr_comment_block(self, evaluation_result: dict[str, Any]) -> str:
        report = LifecycleStateReport.model_validate(evaluation_result)
        status = report.lifecycle_status.value
        lines = [
            "### Atlas Lifecycle",
            f"- Status: `{status}`",
            f"- Atlas version: `{report.atlas_version_tag}`",
            f"- Active days: `{report.delta_days_active if report.delta_days_active is not None else 'unknown'}`",
        ]
        if report.lifecycle_status == LifecycleStatus.STALE:
            lines.append(
                "- Warning: `coordinate_image_pull_update_with_infrastructure_or_ai_platform_administrator`"
            )
        if report.lifecycle_status == LifecycleStatus.MUTED:
            lines.append("- Notice: `staleness_notifications_muted_by_operator`")
        if report.lifecycle_status == LifecycleStatus.UNKNOWN:
            lines.append("- Notice: `atlas_lifecycle_metadata_missing`")
        block = "\n".join(lines)
        validate_rendered_text(block)
        return block

    def _dump(self, report: LifecycleStateReport) -> dict[str, Any]:
        payload = report.model_dump(mode="json")
        NoPayloadValidator().validate(payload)
        return payload


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
