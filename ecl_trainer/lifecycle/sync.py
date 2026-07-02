from __future__ import annotations

import base64
import json
import os
import posixpath
import tarfile
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

import duckdb
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import Field, field_validator, model_validator

from atlas_pipeline.schemas import AtlasSourceRecord
from ecl_trainer.core.models import FrozenModel
from ecl_trainer.core.policy import HEX_SHA256_RE, NoPayloadValidator, sha256_hex
from ecl_trainer.core.serialization import canonical_json, canonical_sha256
from ecl_trainer.oracle.atlas import _EclInternalCore, ensure_atlas, refresh_atlas_manifest
from ecl_trainer.oracle.domains import DomainExtensionStatus, IndustryDomain

MAX_PATCH_ARCHIVE_BYTES = 100 * 1024 * 1024
MAX_PATCH_MEMBER_BYTES = 10 * 1024 * 1024
PATCH_MANIFEST_MEMBER = "ecl_delta_manifest.json"
ALLOWED_PATCH_PREFIXES = ("records/",)
TRUSTED_PATCH_PUBLIC_KEYS_ENV = "ECL_PATCH_TRUSTED_PUBLIC_KEYS"


class OfflinePatchStatus(StrEnum):
    APPLIED = "APPLIED"
    REJECTED = "REJECTED"


class OfflinePatchFile(FrozenModel):
    member_path: str
    member_hash_sha256: str
    purpose: Literal["atlas_source_records"]
    record_count: int | None = None

    @field_validator("member_path")
    @classmethod
    def validate_member_path(cls, value: str) -> str:
        _validate_member_path(value, allow_manifest=False)
        return value


class OfflinePatchOperation(FrozenModel):
    operation_type: Literal["upsert_atlas_source_records", "set_domain_extension_statuses"]
    member_path: str | None = None
    domain_extension_status: dict[IndustryDomain, DomainExtensionStatus] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_operation(self):
        if self.operation_type == "upsert_atlas_source_records" and not self.member_path:
            raise ValueError("upsert_atlas_source_records requires member_path")
        if self.member_path is not None:
            _validate_member_path(self.member_path, allow_manifest=False)
        if self.operation_type == "set_domain_extension_statuses" and not self.domain_extension_status:
            raise ValueError("set_domain_extension_statuses requires domain_extension_status")
        return self


class OfflinePatchManifest(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    patch_id: str
    target_atlas_version_tag: str | None = None
    new_atlas_version_tag: str
    compiled_at: datetime
    supported_domains_mask: int
    patch_signature_hash_sha256: str
    signature_algorithm: Literal["ed25519"] = "ed25519"
    publisher_key_id: str
    publisher_signature_ed25519: str
    files: list[OfflinePatchFile] = Field(default_factory=list)
    operations: list[OfflinePatchOperation] = Field(default_factory=list)

    @field_validator("patch_signature_hash_sha256")
    @classmethod
    def validate_patch_signature_hash(cls, value: str) -> str:
        if not HEX_SHA256_RE.match(value):
            raise ValueError("patch_signature_hash_sha256 must be SHA-256 hex")
        return value

    @model_validator(mode="after")
    def validate_manifest_shape(self):
        file_paths = {patch_file.member_path for patch_file in self.files}
        for operation in self.operations:
            if operation.member_path and operation.member_path not in file_paths:
                raise ValueError(f"operation references undeclared member_path: {operation.member_path}")
        return self


class OfflinePatchApplyReport(FrozenModel):
    offline_patch_status: OfflinePatchStatus
    patch_id: str
    patch_manifest_hash_sha256: str
    publisher_key_id: str
    signature_algorithm: Literal["ed25519"] = "ed25519"
    new_atlas_version_tag: str
    compiled_at: datetime
    atlas_signature_hash_sha256: str
    member_hashes: dict[str, str] = Field(default_factory=dict)
    applied_operation_count: int = 0
    applied_record_count: int = 0
    updated_domain_count: int = 0
    payload_policy: str = "passed"


class OfflineSyncManager:
    def __init__(self, atlas_path: str | Path | None = None) -> None:
        self.atlas_path = ensure_atlas(atlas_path)

    def apply_patch(self, patch_archive: str | Path) -> dict[str, Any]:
        archive_path = Path(patch_archive)
        manifest, members = self._load_patch_archive(archive_path)
        current_metadata = _EclInternalCore(self.atlas_path).atlas_lifecycle_metadata()
        if (
            manifest.target_atlas_version_tag
            and current_metadata is not None
            and manifest.target_atlas_version_tag != current_metadata["atlas_version_tag"]
        ):
            raise ValueError("offline patch target_atlas_version_tag does not match local Atlas")

        manifest_hash = canonical_sha256(manifest)
        applied_record_count = 0
        updated_domain_count = 0
        with duckdb.connect(str(self.atlas_path)) as connection:
            self._ensure_patch_tables(connection)
            for operation in manifest.operations:
                if operation.operation_type == "upsert_atlas_source_records":
                    if operation.member_path is None:
                        raise ValueError("upsert operation is missing member_path")
                    records = self._load_source_records(members[operation.member_path])
                    self._upsert_source_records(connection, records)
                    applied_record_count += len(records)
                elif operation.operation_type == "set_domain_extension_statuses":
                    updated_domain_count += self._set_domain_statuses(connection, operation.domain_extension_status)
            build_hash = self._recompute_manifest_hash(connection)
            atlas_signature = self._write_lifecycle_metadata(connection, manifest, manifest_hash, build_hash)

        report = OfflinePatchApplyReport(
            offline_patch_status=OfflinePatchStatus.APPLIED,
            patch_id=manifest.patch_id,
            patch_manifest_hash_sha256=manifest_hash,
            publisher_key_id=manifest.publisher_key_id,
            new_atlas_version_tag=manifest.new_atlas_version_tag,
            compiled_at=_as_utc(manifest.compiled_at),
            atlas_signature_hash_sha256=atlas_signature,
            member_hashes={patch_file.member_path: patch_file.member_hash_sha256 for patch_file in manifest.files},
            applied_operation_count=len(manifest.operations),
            applied_record_count=applied_record_count,
            updated_domain_count=updated_domain_count,
        )
        payload = report.model_dump(mode="json")
        NoPayloadValidator().validate(payload)
        return payload

    def _load_patch_archive(self, archive_path: Path) -> tuple[OfflinePatchManifest, dict[str, bytes]]:
        if not archive_path.name.endswith(".tar.gz"):
            raise ValueError("offline patch archive must use .tar.gz")
        if archive_path.stat().st_size > MAX_PATCH_ARCHIVE_BYTES:
            raise ValueError("offline patch archive exceeds maximum size")

        members: dict[str, bytes] = {}
        with tarfile.open(archive_path, mode="r:gz") as archive:
            infos = archive.getmembers()
            member_names = [info.name for info in infos]
            if PATCH_MANIFEST_MEMBER not in member_names:
                raise ValueError("offline patch archive is missing ecl_delta_manifest.json")
            for info in infos:
                _validate_tar_member(info)
                extracted = archive.extractfile(info)
                if extracted is None:
                    raise ValueError(f"offline patch member could not be read: {info.name}")
                data = extracted.read()
                if len(data) != info.size:
                    raise ValueError(f"offline patch member size mismatch: {info.name}")
                members[info.name] = data

        manifest_payload = json.loads(members[PATCH_MANIFEST_MEMBER].decode("utf-8"))
        expected_signature_hash = _patch_signature_hash(manifest_payload)
        if manifest_payload.get("patch_signature_hash_sha256") != expected_signature_hash:
            raise ValueError("offline patch manifest signature hash mismatch")
        _verify_patch_publisher_signature(manifest_payload)
        manifest = OfflinePatchManifest.model_validate(manifest_payload)
        declared_hashes = {patch_file.member_path: patch_file.member_hash_sha256 for patch_file in manifest.files}
        for member_name, data in members.items():
            if member_name == PATCH_MANIFEST_MEMBER:
                continue
            if member_name not in declared_hashes:
                raise ValueError(f"offline patch member is not declared: {member_name}")
            if sha256_hex(data) != declared_hashes[member_name]:
                raise ValueError(f"offline patch member hash mismatch: {member_name}")
        missing_members = set(declared_hashes) - set(members)
        if missing_members:
            raise ValueError("offline patch declared member is missing")
        return manifest, members

    def _load_source_records(self, data: bytes) -> list[AtlasSourceRecord]:
        parsed = json.loads(data.decode("utf-8"))
        NoPayloadValidator().validate(parsed)
        if not isinstance(parsed, list):
            raise ValueError("atlas source record patch member must contain a list")
        return [AtlasSourceRecord.model_validate(record) for record in parsed]

    def _ensure_patch_tables(self, connection: duckdb.DuckDBPyConnection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS atlas_source_records (
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
            CREATE TABLE IF NOT EXISTS atlas_source_record_tags (
                record_id VARCHAR,
                tag_family VARCHAR,
                tag_value VARCHAR
            )
            """
        )

    def _upsert_source_records(
        self,
        connection: duckdb.DuckDBPyConnection,
        records: list[AtlasSourceRecord],
    ) -> None:
        for record in records:
            connection.execute("DELETE FROM atlas_source_records WHERE record_id = ?", [record.record_id])
            connection.execute("DELETE FROM atlas_source_record_tags WHERE record_id = ?", [record.record_id])
            connection.execute(
                "INSERT INTO atlas_source_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
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
                ],
            )
            tag_rows = _source_record_tag_rows(record)
            if tag_rows:
                connection.executemany("INSERT INTO atlas_source_record_tags VALUES (?, ?, ?)", tag_rows)

    def _set_domain_statuses(
        self,
        connection: duckdb.DuckDBPyConnection,
        statuses: dict[IndustryDomain, DomainExtensionStatus],
    ) -> int:
        updated = 0
        for domain, status in statuses.items():
            connection.execute(
                "UPDATE domain_extension_manifest SET domain_status = ? WHERE domain_id = ?",
                [status.value, domain.value],
            )
            updated += 1
        return updated

    def _recompute_manifest_hash(self, connection: duckdb.DuckDBPyConnection) -> str:
        return refresh_atlas_manifest(connection, pack_visibility="offline_metadata_patch")

    def _write_lifecycle_metadata(
        self,
        connection: duckdb.DuckDBPyConnection,
        manifest: OfflinePatchManifest,
        manifest_hash: str,
        build_hash: str,
    ) -> str:
        compiled_at = _as_utc(manifest.compiled_at)
        metadata_payload = {
            "atlas_version_tag": manifest.new_atlas_version_tag,
            "compiled_at": compiled_at,
            "supported_domains_mask": manifest.supported_domains_mask,
            "patch_manifest_hash_sha256": manifest_hash,
            "build_hash_sha256": build_hash,
        }
        atlas_signature = canonical_sha256(metadata_payload)
        connection.execute("DELETE FROM ecl_atlas_metadata")
        connection.execute(
            "INSERT INTO ecl_atlas_metadata VALUES (?, ?, ?, ?)",
            [
                manifest.new_atlas_version_tag,
                compiled_at.replace(tzinfo=None),
                manifest.supported_domains_mask,
                atlas_signature,
            ],
        )
        return atlas_signature


def _source_record_tag_rows(record: AtlasSourceRecord) -> list[tuple[str, str, str]]:
    tag_rows: list[tuple[str, str, str]] = []
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
    return tag_rows


def _validate_tar_member(info: tarfile.TarInfo) -> None:
    _validate_member_path(info.name, allow_manifest=True)
    if not info.isfile():
        raise ValueError(f"offline patch member must be a regular file: {info.name}")
    if info.size > MAX_PATCH_MEMBER_BYTES:
        raise ValueError(f"offline patch member exceeds maximum size: {info.name}")


def _validate_member_path(member_path: str, *, allow_manifest: bool) -> None:
    if member_path.startswith("/") or member_path.startswith("\\"):
        raise ValueError("offline patch member path must be relative")
    normalized = posixpath.normpath(member_path)
    if normalized != member_path or normalized.startswith("../") or normalized == "..":
        raise ValueError("offline patch member path must not traverse directories")
    if allow_manifest and member_path == PATCH_MANIFEST_MEMBER:
        return
    if not member_path.endswith(".json"):
        raise ValueError("offline patch members must be JSON metadata files")
    if not member_path.startswith(ALLOWED_PATCH_PREFIXES):
        raise ValueError("offline patch member path is outside the allowlisted prefixes")


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _patch_signature_hash(manifest: dict[str, Any]) -> str:
    return sha256_hex(canonical_json(_patch_signature_payload(manifest)))


def _patch_signature_payload(manifest: dict[str, Any]) -> dict[str, Any]:
    payload = dict(manifest)
    payload["patch_signature_hash_sha256"] = ""
    payload["publisher_signature_ed25519"] = ""
    return payload


def _verify_patch_publisher_signature(manifest: dict[str, Any]) -> None:
    if manifest.get("signature_algorithm") != "ed25519":
        raise ValueError("offline patch manifest signature_algorithm must be ed25519")
    key_id = manifest.get("publisher_key_id")
    if not isinstance(key_id, str) or not key_id:
        raise ValueError("offline patch manifest publisher_key_id is required")
    signature = manifest.get("publisher_signature_ed25519")
    if not isinstance(signature, str) or not signature:
        raise ValueError("offline patch manifest publisher_signature_ed25519 is required")
    trusted_keys = _trusted_patch_public_keys()
    public_key_b64 = trusted_keys.get(key_id)
    if public_key_b64 is None:
        raise ValueError("offline patch publisher_key_id is not trusted")
    try:
        public_key_bytes = base64.b64decode(public_key_b64, validate=True)
        signature_bytes = base64.b64decode(signature, validate=True)
        public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
        public_key.verify(signature_bytes, canonical_json(_patch_signature_payload(manifest)).encode("utf-8"))
    except (InvalidSignature, ValueError) as exc:
        raise ValueError("offline patch publisher signature verification failed") from exc


def _trusted_patch_public_keys() -> dict[str, str]:
    raw = os.getenv(TRUSTED_PATCH_PUBLIC_KEYS_ENV)
    if not raw:
        raise ValueError("offline patch trusted public keys are not configured")
    parsed = json.loads(raw)
    if not isinstance(parsed, dict) or not parsed:
        raise ValueError("offline patch trusted public keys must be a non-empty JSON object")
    return {str(key): str(value) for key, value in parsed.items()}
