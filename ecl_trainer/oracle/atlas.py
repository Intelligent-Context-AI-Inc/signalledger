from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb

from ecl_trainer.core.policy import NoPayloadValidator
from ecl_trainer.core.serialization import canonical_sha256
from ecl_trainer.oracle.domains import TOP_20_DOMAINS, DomainExtensionStatus, IndustryDomain

DEFAULT_ATLAS_VERSION = "option-b-alpha.1"
DEFAULT_ATLAS_PATH = "/opt/ecl-trainer/atlas/intelligent-context-atlas.duckdb"
DEFAULT_ATLAS_VERSION_TAG = "v0.1.0rc1-2026.Q3"
DEFAULT_ATLAS_COMPILED_AT = datetime(2026, 6, 30, tzinfo=UTC)


def default_atlas_path() -> Path:
    return Path(os.getenv("ECL_ATLAS_PATH", DEFAULT_ATLAS_PATH))


def build_option_b_atlas(path: str | Path) -> Path:
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    connection = duckdb.connect(str(db_path))
    try:
        connection.execute(
            """
            CREATE TABLE atlas_manifest (
                atlas_version VARCHAR,
                build_hash_sha256 VARCHAR,
                included_domain_packs VARCHAR,
                pack_visibility VARCHAR
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE global_core_patterns (
                pattern_id VARCHAR,
                category VARCHAR,
                risk_weight DOUBLE,
                action_required VARCHAR
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE domain_extension_manifest (
                domain_id VARCHAR,
                domain_status VARCHAR
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE domain_patterns (
                domain_id VARCHAR,
                pattern_id VARCHAR,
                category VARCHAR,
                risk_weight DOUBLE,
                target_key VARCHAR,
                target_value DOUBLE,
                action_required VARCHAR
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE ecl_atlas_metadata (
                atlas_version_tag VARCHAR,
                compiled_at TIMESTAMP,
                supported_domains_mask BIGINT,
                atlas_signature VARCHAR
            )
            """
        )
        build_payload = {
            "atlas_version": DEFAULT_ATLAS_VERSION,
            "domains": [domain.value for domain in TOP_20_DOMAINS],
            "active": [IndustryDomain.FINANCIAL_SERVICES.value],
            "global_core": True,
        }
        build_hash = canonical_sha256(build_payload)
        connection.execute(
            "INSERT INTO atlas_manifest VALUES (?, ?, ?, ?)",
            [DEFAULT_ATLAS_VERSION, build_hash, "financial_services", "public_alpha_fixture"],
        )
        supported_domains_mask = (1 << len(TOP_20_DOMAINS)) - 1
        metadata_payload = {
            "atlas_version_tag": DEFAULT_ATLAS_VERSION_TAG,
            "compiled_at": DEFAULT_ATLAS_COMPILED_AT.isoformat(),
            "supported_domains_mask": supported_domains_mask,
            "build_hash_sha256": build_hash,
        }
        connection.execute(
            "INSERT INTO ecl_atlas_metadata VALUES (?, ?, ?, ?)",
            [
                DEFAULT_ATLAS_VERSION_TAG,
                DEFAULT_ATLAS_COMPILED_AT.replace(tzinfo=None),
                supported_domains_mask,
                canonical_sha256(metadata_payload),
            ],
        )
        connection.executemany(
            "INSERT INTO global_core_patterns VALUES (?, ?, ?, ?)",
            [
                ("global_lineage_loop", "MODEL_INBREEDING", 0.88, "QUARANTINE"),
                ("global_benchmark_overlap", "BENCHMARK_LEAK", 0.82, "QUARANTINE"),
                ("global_loss_spike_signature", "TRAINING_LOSS_DIVERGENCE", 0.74, "REVIEW"),
            ],
        )
        connection.executemany(
            "INSERT INTO domain_extension_manifest VALUES (?, ?)",
            [
                (
                    domain.value,
                    DomainExtensionStatus.ACTIVE.value
                    if domain == IndustryDomain.FINANCIAL_SERVICES
                    else DomainExtensionStatus.REGISTERED.value,
                )
                for domain in TOP_20_DOMAINS
            ],
        )
        connection.executemany(
            "INSERT INTO domain_patterns VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    IndustryDomain.FINANCIAL_SERVICES.value,
                    "financial_filings_balance",
                    "TRAINING_LOSS_DIVERGENCE",
                    0.22,
                    "filings_target",
                    0.42,
                    "ALLOW",
                ),
                (
                    IndustryDomain.FINANCIAL_SERVICES.value,
                    "financial_support_balance",
                    "PROVENANCE_GAP",
                    0.18,
                    "internal_tickets_target",
                    0.18,
                    "REVIEW",
                ),
                (
                    IndustryDomain.FINANCIAL_SERVICES.value,
                    "financial_news_balance",
                    "BENCHMARK_LEAK",
                    0.16,
                    "news_target",
                    0.40,
                    "REVIEW",
                ),
            ],
        )
    finally:
        connection.close()
    return db_path


def ensure_atlas(path: str | Path | None = None) -> Path:
    db_path = Path(path) if path is not None else default_atlas_path()
    if db_path.exists():
        return db_path
    fallback = Path(os.getenv("ECL_ATLAS_FALLBACK_PATH", ".ecl-trainer/atlas/intelligent-context-atlas.duckdb"))
    return build_option_b_atlas(fallback)


class _EclInternalCore:
    def __init__(self, atlas_path: str | Path | None = None) -> None:
        self.atlas_path = ensure_atlas(atlas_path)

    def _connect(self):
        return duckdb.connect(str(self.atlas_path), read_only=True)

    def atlas_manifest_hash(self) -> str:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT atlas_version, build_hash_sha256, included_domain_packs FROM atlas_manifest"
            ).fetchone()
        if row is None:
            raise RuntimeError("Intelligent Context Atlas manifest is missing")
        return canonical_sha256({"atlas_version": row[0], "build_hash_sha256": row[1], "included_domain_packs": row[2]})

    def domain_statuses(self) -> dict[str, str]:
        with self._connect() as connection:
            rows = connection.execute("SELECT domain_id, domain_status FROM domain_extension_manifest").fetchall()
        return {str(domain_id): str(status) for domain_id, status in rows}

    def atlas_lifecycle_metadata(self) -> dict[str, Any] | None:
        with self._connect() as connection:
            tables = {
                str(row[0])
                for row in connection.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
                ).fetchall()
            }
            if "ecl_atlas_metadata" not in tables:
                return None
            row = connection.execute(
                """
                SELECT atlas_version_tag, compiled_at, supported_domains_mask, atlas_signature
                FROM ecl_atlas_metadata
                LIMIT 1
                """
            ).fetchone()
        if row is None:
            return None
        compiled_at = row[1]
        if isinstance(compiled_at, datetime) and compiled_at.tzinfo is None:
            compiled_at = compiled_at.replace(tzinfo=UTC)
        result = {
            "atlas_version_tag": row[0],
            "compiled_at": compiled_at,
            "supported_domains_mask": int(row[2]),
            "atlas_signature_hash_sha256": row[3],
        }
        NoPayloadValidator().validate(result)
        return result

    def atlas_source_summary(self) -> dict[str, Any]:
        with self._connect() as connection:
            tables = {
                str(row[0])
                for row in connection.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
                ).fetchall()
            }
            if "atlas_source_records" not in tables:
                result = {
                    "atlas_source_record_count": 0,
                    "atlas_financial_source_record_count": 0,
                    "atlas_global_core_source_record_count": 0,
                    "atlas_source_family_counts": {},
                    "atlas_domain_source_counts": {},
                    "atlas_seeded_domain_count": 0,
                }
                NoPayloadValidator().validate(result)
                return result
            total_row = connection.execute("SELECT COUNT(*) FROM atlas_source_records").fetchone()
            financial_row = connection.execute(
                "SELECT COUNT(*) FROM atlas_source_records WHERE domain_id = ?",
                [IndustryDomain.FINANCIAL_SERVICES.value],
            ).fetchone()
            global_row = connection.execute(
                "SELECT COUNT(*) FROM atlas_source_records WHERE global_core_relevance = true"
            ).fetchone()
            if total_row is None or financial_row is None or global_row is None:
                raise RuntimeError("Intelligent Context Atlas source summary is missing")
            total_count = total_row[0]
            financial_count = financial_row[0]
            global_count = global_row[0]
            family_rows = connection.execute(
                "SELECT source_family, COUNT(*) FROM atlas_source_records GROUP BY source_family ORDER BY source_family"
            ).fetchall()
            domain_rows = connection.execute(
                """
                SELECT domain_id, COUNT(*)
                FROM atlas_source_records
                WHERE domain_id IS NOT NULL
                GROUP BY domain_id
                ORDER BY domain_id
                """
            ).fetchall()
        domain_counts = {str(domain): int(count) for domain, count in domain_rows}
        result = {
            "atlas_source_record_count": int(total_count),
            "atlas_financial_source_record_count": int(financial_count),
            "atlas_global_core_source_record_count": int(global_count),
            "atlas_source_family_counts": {str(family): int(count) for family, count in family_rows},
            "atlas_domain_source_counts": domain_counts,
            "atlas_seeded_domain_count": len(domain_counts),
        }
        NoPayloadValidator().validate(result)
        return result

    def global_patterns(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT pattern_id, category, risk_weight, action_required FROM global_core_patterns"
            ).fetchall()
        result = [
            {
                "pattern_id": row[0],
                "category": row[1],
                "risk_weight": float(row[2]),
                "action_required": row[3],
            }
            for row in rows
        ]
        NoPayloadValidator().validate(result)
        return result

    def domain_patterns(self, domains: list[IndustryDomain]) -> list[dict[str, Any]]:
        if not domains:
            return []
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT domain_id, pattern_id, category, risk_weight, target_key, target_value, action_required
                FROM domain_patterns
                WHERE domain_id IN (SELECT UNNEST(?))
                """,
                [[domain.value for domain in domains]],
            ).fetchall()
        result = [
            {
                "domain_id": row[0],
                "pattern_id": row[1],
                "category": row[2],
                "risk_weight": float(row[3]),
                "target_key": row[4],
                "target_value": float(row[5]),
                "action_required": row[6],
            }
            for row in rows
        ]
        NoPayloadValidator().validate(result)
        return result
