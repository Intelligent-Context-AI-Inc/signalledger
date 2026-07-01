from __future__ import annotations

import json
from pathlib import Path

from atlas_pipeline.schemas import AtlasSourceRecord


class LocalManifestCollector:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def collect(self) -> list[AtlasSourceRecord]:
        records: list[AtlasSourceRecord] = []
        for path in sorted(self.root.rglob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            entries = payload if isinstance(payload, list) else payload.get("records", [])
            for entry in entries:
                records.append(AtlasSourceRecord.model_validate(entry))
        return records


class CollectorRegistry:
    def __init__(self) -> None:
        self._collectors: list[LocalManifestCollector] = []

    def register(self, collector: LocalManifestCollector) -> None:
        self._collectors.append(collector)

    def collect(self) -> list[AtlasSourceRecord]:
        records: list[AtlasSourceRecord] = []
        for collector in self._collectors:
            records.extend(collector.collect())
        return records
