from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from ecl_trainer.core.models import SemanticTag, TokenEstimateMatrix
from ecl_trainer.core.policy import SourceUriPolicy, sha256_hex
from ecl_trainer.core.serialization import canonical_sha256


@dataclass(frozen=True)
class FingerprintResult:
    dataset_fingerprint: str
    schema_hash_sha256: str
    source_root_hash_sha256: str
    chunk_manifest_hash_sha256: str
    license_matrix_hash_sha256: str
    token_estimate_matrix_hash_sha256: str
    semantic_tag_set_hash_sha256: str
    mutation_trail_hash_sha256: str
    token_count_estimates: TokenEstimateMatrix


class TokenEstimateMatrixBuilder:
    def estimate(
        self,
        *,
        byte_length: int = 0,
        externally_supplied_count: int | None = None,
        segment: str = "default",
        modality: str = "unknown",
    ) -> TokenEstimateMatrix:
        count = externally_supplied_count if externally_supplied_count is not None else max(0, byte_length // 4)
        return TokenEstimateMatrix(
            total_estimated_tokens=count,
            by_segment={segment: count},
            by_modality={modality: count},
        )


class SemanticTagExtractor:
    allowed_keys = {
        "domain_category",
        "source_type",
        "language_code",
        "license_class",
        "synthetic_data_indicator",
        "benchmark_family_indicator",
        "temporal_range",
        "data_modality",
        "sensitivity_class",
        "transformation_class",
        "origin_type",
    }

    def extract(self, metadata: Mapping[str, Any]) -> list[SemanticTag]:
        tags: list[SemanticTag] = []
        for key, value in metadata.items():
            if key in self.allowed_keys and value is not None:
                tags.append(
                    SemanticTag(
                        namespace="ecl",
                        key=key,
                        value=str(value),
                        confidence=1.0,
                        source="metadata",
                        emitted_by="semantic_tag_extractor",
                    )
                )
        return tags


class SignalHasher:
    def __init__(self, *, unsafe_debug_paths: bool = False) -> None:
        self.source_policy = SourceUriPolicy(unsafe_debug=unsafe_debug_paths)
        self.token_estimator = TokenEstimateMatrixBuilder()

    def fingerprint(
        self,
        *,
        source_uri: str,
        schema: Mapping[str, Any] | None = None,
        chunks: Iterable[Mapping[str, Any]] | None = None,
        license_matrix: Iterable[Mapping[str, Any]] | None = None,
        semantic_tags: Iterable[Mapping[str, Any] | SemanticTag] | None = None,
        mutation_trail: Iterable[Mapping[str, Any]] | None = None,
        byte_length: int = 0,
        externally_supplied_token_count: int | None = None,
    ) -> FingerprintResult:
        safe_source = self.source_policy.strip(source_uri)
        token_matrix = self.token_estimator.estimate(
            byte_length=byte_length,
            externally_supplied_count=externally_supplied_token_count,
        )
        schema_hash = canonical_sha256(schema or {})
        source_hash = sha256_hex(safe_source)
        chunk_hash = canonical_sha256(list(chunks or []))
        license_hash = canonical_sha256(list(license_matrix or []))
        tag_payload = [
            tag.model_dump(mode="python") if isinstance(tag, SemanticTag) else dict(tag)
            for tag in (semantic_tags or [])
        ]
        tag_hash = canonical_sha256(tag_payload)
        mutation_hash = canonical_sha256(list(mutation_trail or []))
        token_hash = canonical_sha256(token_matrix)
        dataset_fingerprint = canonical_sha256(
            {
                "schema_hash_sha256": schema_hash,
                "source_root_hash_sha256": source_hash,
                "chunk_manifest_hash_sha256": chunk_hash,
                "license_matrix_hash_sha256": license_hash,
                "token_estimate_matrix_hash_sha256": token_hash,
                "semantic_tag_set_hash_sha256": tag_hash,
                "mutation_trail_hash_sha256": mutation_hash,
            }
        )
        return FingerprintResult(
            dataset_fingerprint=dataset_fingerprint,
            schema_hash_sha256=schema_hash,
            source_root_hash_sha256=source_hash,
            chunk_manifest_hash_sha256=chunk_hash,
            license_matrix_hash_sha256=license_hash,
            token_estimate_matrix_hash_sha256=token_hash,
            semantic_tag_set_hash_sha256=tag_hash,
            mutation_trail_hash_sha256=mutation_hash,
            token_count_estimates=token_matrix,
        )

    def hash_reference(self, reference: str) -> str:
        return sha256_hex(self.source_policy.strip(reference))


class EvaluationValueProcessor:
    def __init__(self, *, min_delta: float = -0.95, max_delta: float = 5.0) -> None:
        self.min_delta = min_delta
        self.max_delta = max_delta

    def scalar_delta(self, metrics_delta: Mapping[str, float], priority_vector: Mapping[str, float]) -> float:
        delta = sum(float(metrics_delta.get(metric, 0.0)) * float(weight) for metric, weight in priority_vector.items())
        return max(self.min_delta, min(self.max_delta, delta))

    def update_multiplier(self, old_weight: float, delta_eval: float) -> float:
        if old_weight < 0:
            raise ValueError("old_weight must be non-negative")
        clamped = max(self.min_delta, min(self.max_delta, delta_eval))
        return old_weight * (1.0 + clamped)
