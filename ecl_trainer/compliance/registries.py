from __future__ import annotations

from dataclasses import dataclass, field

from ecl_trainer.core.models import ModelLineageRecord
from ecl_trainer.core.policy import sha256_hex

DEFAULT_BENCHMARK_ALIASES = {
    "mmlu",
    "gsm8k",
    "humaneval",
    "mbpp",
    "arc",
    "hellaswag",
    "truthfulqa",
    "big-bench",
}


@dataclass
class BenchmarkRegistry:
    aliases: set[str] = field(default_factory=lambda: set(DEFAULT_BENCHMARK_ALIASES))
    dataset_ids: set[str] = field(default_factory=set)
    source_root_hashes: set[str] = field(default_factory=set)
    split_names: set[str] = field(default_factory=lambda: {"test", "validation", "eval"})

    def extend(
        self,
        *,
        aliases: list[str] | None = None,
        dataset_ids: list[str] | None = None,
        source_root_hashes: list[str] | None = None,
        split_names: list[str] | None = None,
    ) -> None:
        self.aliases.update(alias.lower() for alias in aliases or [])
        self.dataset_ids.update(dataset_id.lower() for dataset_id in dataset_ids or [])
        self.source_root_hashes.update(source_root_hashes or [])
        self.split_names.update(split.lower() for split in split_names or [])

    def matches(self, metadata: dict) -> list[str]:
        matches: list[str] = []
        all_values = _flatten_metadata_values(metadata)
        if self.aliases & all_values:
            matches.append("benchmark_alias")
        if self.dataset_ids & all_values:
            matches.append("dataset_id")
        if metadata.get("source_root_hash_sha256") in self.source_root_hashes:
            matches.append("source_root_hash")
        if self.split_names & all_values:
            matches.append("split_name")
        return matches


@dataclass
class ModelLineageRegistry:
    records: dict[str, ModelLineageRecord] = field(default_factory=dict)

    def add(self, record: ModelLineageRecord) -> None:
        self.records[record.model_id] = record

    def ancestors_for(self, model_id: str) -> set[str]:
        record = self.records.get(model_id)
        if not record:
            return set()
        ancestors = set(record.ancestor_model_ids)
        if record.parent_model_id:
            ancestors.add(record.parent_model_id)
        return ancestors

    def lineage_hash(self, model_id: str) -> str:
        return sha256_hex(model_id)


def _flatten_metadata_values(value: object) -> set[str]:
    if isinstance(value, dict):
        values: set[str] = set()
        for child in value.values():
            values.update(_flatten_metadata_values(child))
        return values
    if isinstance(value, list | tuple | set | frozenset):
        values = set()
        for child in value:
            values.update(_flatten_metadata_values(child))
        return values
    if isinstance(value, str | int | float):
        return {str(value).lower()}
    return set()
