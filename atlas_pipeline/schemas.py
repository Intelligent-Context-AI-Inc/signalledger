from __future__ import annotations

import re
from enum import StrEnum
from typing import Any
from urllib.parse import urlparse

from pydantic import Field, model_validator

from ecl_trainer.core.exceptions import SovereignDataExfiltrationException
from ecl_trainer.core.models import FrozenModel
from ecl_trainer.core.policy import HEX_SHA256_RE, NoPayloadValidator, sha256_hex
from ecl_trainer.oracle.domains import IndustryDomain

URL_SECRET_SEGMENT_RE = re.compile(
    r"((?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9_]{16,}|xox[baprs]-[A-Za-z0-9-]{16,}|token|secret|apikey|api_key)",
    re.IGNORECASE,
)


class AtlasSourceFamily(StrEnum):
    OPEN_SCIENCE_DATASET = "open_science_dataset"
    OPEN_SCIENCE_BENCHMARK = "open_science_benchmark"
    FINANCIAL_TAXONOMY = "financial_taxonomy"
    FINANCIAL_REGULATORY = "financial_regulatory"
    FINANCIAL_STRESS_TEST = "financial_stress_test"
    DOMAIN_TAXONOMY = "domain_taxonomy"
    DOMAIN_REGULATORY = "domain_regulatory"
    DOMAIN_STANDARD = "domain_standard"
    DOMAIN_OPEN_DATA = "domain_open_data"
    DOMAIN_BENCHMARK = "domain_benchmark"


class AtlasSourceRecord(FrozenModel):
    record_id: str
    source_family: AtlasSourceFamily
    source_name: str
    source_version: str
    source_reference_uri: str
    source_reference_hash_sha256: str = ""
    domain_id: IndustryDomain | None = None
    global_core_relevance: bool = False
    token_count_estimate: int | None = None
    source_mixture_categories: list[str] = Field(default_factory=list)
    filtering_methods: list[str] = Field(default_factory=list)
    deduplication_methods: list[str] = Field(default_factory=list)
    evaluation_metric_names: list[str] = Field(default_factory=list)
    benchmark_count: int | None = None
    model_size_parameters: list[str] = Field(default_factory=list)
    license_descriptor: str | None = None
    regulatory_source_categories: list[str] = Field(default_factory=list)
    financial_taxonomy_tags: list[str] = Field(default_factory=list)
    domain_taxonomy_tags: list[str] = Field(default_factory=list)
    provenance_links: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def validate_metadata_only(cls, data: Any) -> Any:
        NoPayloadValidator().validate(data)
        cls._reject_long_unhashed_text(data)
        return data

    @model_validator(mode="after")
    def fill_hash(self):
        reference_hash = self.source_reference_hash_sha256 or sha256_hex(self.source_reference_uri)
        return self.model_copy(update={"source_reference_hash_sha256": reference_hash})

    @classmethod
    def _reject_long_unhashed_text(cls, value: Any) -> None:
        if isinstance(value, dict):
            for child in value.values():
                cls._reject_long_unhashed_text(child)
            return
        if isinstance(value, list):
            for child in value:
                cls._reject_long_unhashed_text(child)
            return
        if isinstance(value, str) and value.startswith(("https://", "http://")):
            parsed = urlparse(value)
            path_segments = [segment for segment in parsed.path.split("/") if segment]
            unsafe_path = any(URL_SECRET_SEGMENT_RE.search(segment) for segment in path_segments)
            if not parsed.netloc or parsed.query or parsed.fragment or len(value) > 120 or unsafe_path:
                raise SovereignDataExfiltrationException("Atlas source record contains unsafe URL text")
            return
        if isinstance(value, str) and len(value) > 120:
            if HEX_SHA256_RE.match(value):
                return
            raise SovereignDataExfiltrationException("Atlas source record contains long non-hash text")


class AtlasBuildManifest(FrozenModel):
    build_id: str
    atlas_version: str
    records: list[AtlasSourceRecord]

    @property
    def build_hash_sha256(self) -> str:
        return sha256_hex("|".join(sorted(record.source_reference_hash_sha256 for record in self.records)))
