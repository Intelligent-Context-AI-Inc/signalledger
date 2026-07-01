from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from ecl_trainer.core.exceptions import LedgerVerificationException
from ecl_trainer.core.policy import NoPayloadValidator
from ecl_trainer.core.serialization import canonical_json, canonical_sha256, load_canonical_json_line


def _as_dict(event: BaseModel | dict[str, Any]) -> dict[str, Any]:
    if isinstance(event, BaseModel):
        return event.model_dump(mode="python")
    return dict(event)


def _hashable_event(event: dict[str, Any]) -> dict[str, Any]:
    data = dict(event)
    data["event_hash_sha256"] = ""
    data["signature"] = None
    return data


class HashChainWriter:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def previous_hash(self) -> str | None:
        if not self.path.exists():
            return None
        previous: str | None = None
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    previous = load_canonical_json_line(line)["event_hash_sha256"]
        return previous

    def prepare(self, event: BaseModel | dict[str, Any]) -> dict[str, Any]:
        data = _as_dict(event)
        NoPayloadValidator().validate(data)
        data["previous_event_hash_sha256"] = self.previous_hash()
        data["event_hash_sha256"] = canonical_sha256(_hashable_event(data))
        return data

    def write(self, event: BaseModel | dict[str, Any]) -> dict[str, Any]:
        data = self.prepare(event)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(canonical_json(data) + "\n")
            handle.flush()
        return data


class AppendOnlyEventLog:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.writer = HashChainWriter(self.path)

    def append(self, event: BaseModel | dict[str, Any]) -> dict[str, Any]:
        return self.writer.write(event)

    def replay(self) -> list[dict[str, Any]]:
        return list(LocalEventReplay(self.path).iter_events())

    def verify(self) -> dict[str, Any]:
        return HashChainVerifier(self.path).verify()


class HashChainVerifier:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def verify(self) -> dict[str, Any]:
        previous: str | None = None
        count = 0
        if not self.path.exists():
            return {"valid": True, "event_count": 0, "first_broken_link": None}
        with self.path.open("r", encoding="utf-8") as handle:
            for index, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                data = load_canonical_json_line(line)
                if data.get("previous_event_hash_sha256") != previous:
                    return {"valid": False, "event_count": count, "first_broken_link": index}
                expected = canonical_sha256(_hashable_event(data))
                if data.get("event_hash_sha256") != expected:
                    return {"valid": False, "event_count": count, "first_broken_link": index}
                previous = data["event_hash_sha256"]
                count += 1
        return {"valid": True, "event_count": count, "first_broken_link": None}

    def raise_if_invalid(self) -> None:
        result = self.verify()
        if not result["valid"]:
            raise LedgerVerificationException(f"Hash chain broken at line {result['first_broken_link']}")


class LocalEventReplay:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def iter_events(
        self,
        *,
        project_namespace: str | None = None,
        event_type: str | None = None,
        dataset_hash: str | None = None,
        checkpoint_id: str | None = None,
        training_run_id: str | None = None,
        ci_run_id: str | None = None,
        pr_hash: str | None = None,
        mr_hash: str | None = None,
    ) -> Iterable[dict[str, Any]]:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                event = load_canonical_json_line(line)
                if project_namespace and event.get("project_namespace") != project_namespace:
                    continue
                if event_type and event.get("event_type") != event_type:
                    continue
                if dataset_hash and dataset_hash not in {
                    event.get("content_hash_sha256"),
                    event.get("exposed_dataset_hash"),
                    *(event.get("exposed_dataset_hashes") or []),
                }:
                    continue
                if checkpoint_id and event.get("checkpoint_id") != checkpoint_id:
                    continue
                if training_run_id and event.get("training_run_id") != training_run_id:
                    continue
                if ci_run_id and event.get("ci_run_id") != ci_run_id:
                    continue
                if pr_hash and event.get("pull_request_id_hash") != pr_hash:
                    continue
                if mr_hash and event.get("merge_request_id_hash") != mr_hash:
                    continue
                yield event
