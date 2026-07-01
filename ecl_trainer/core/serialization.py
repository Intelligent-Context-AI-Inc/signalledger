from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from ecl_trainer.core.policy import NoPayloadValidator, sha256_hex


def normalize_for_json(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return normalize_for_json(value.model_dump(mode="python"))
    if isinstance(value, datetime):
        dt = value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
        return dt.isoformat().replace("+00:00", "Z")
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): normalize_for_json(child) for key, child in value.items()}
    if isinstance(value, (set, frozenset)):
        return sorted(normalize_for_json(child) for child in value)
    if isinstance(value, (list, tuple)):
        return [normalize_for_json(child) for child in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"Unsupported canonical JSON value: {type(value).__name__}")


def canonical_json(value: Any, *, validate: bool = True) -> str:
    normalized = normalize_for_json(value)
    if validate:
        NoPayloadValidator().validate(normalized)
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_sha256(value: Any, *, validate: bool = True) -> str:
    return sha256_hex(canonical_json(value, validate=validate))


def load_canonical_json_line(line: str) -> dict[str, Any]:
    data = json.loads(line)
    NoPayloadValidator().validate(data)
    return data
