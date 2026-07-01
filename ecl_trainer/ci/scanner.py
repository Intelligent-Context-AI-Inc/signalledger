from __future__ import annotations

import json
import os
import shutil
import subprocess  # nosec B404
from pathlib import Path
from typing import Any

import yaml

from ecl_trainer.ci.path_filters import PathFilter
from ecl_trainer.compliance.risk import RiskGatekeeper
from ecl_trainer.core.ledger import AppendOnlyEventLog
from ecl_trainer.core.models import CIScanEvent, RiskSummary
from ecl_trainer.core.policy import NoPayloadValidator, sha256_hex
from ecl_trainer.core.serialization import canonical_sha256

NON_METADATA_SUBPATHS = (
    (".github",),
    ("ecl_trainer", "red_team_fixtures"),
    ("tests", "red_team_fixtures"),
    ("examples", "github_action"),
)


# Fixed-argument git metadata query only; no shell execution.
class CIScanner:
    def __init__(
        self,
        *,
        repository_root: str | Path = ".",
        ledger_path: str | Path = ".ecl-trainer/events.jsonl",
        project_namespace: str = "default",
        path_filter: PathFilter | None = None,
    ) -> None:
        self.repository_root = Path(repository_root)
        self.ledger_path = Path(ledger_path)
        self.project_namespace = project_namespace
        self.path_filter = path_filter or PathFilter()

    def changed_files(self) -> list[str]:
        git_path = shutil.which("git")
        if not git_path:
            return []
        try:
            # Fixed git arguments only; this reads metadata and does not execute repository code.
            output = subprocess.check_output(  # noqa: S603  # nosec B603
                [
                    git_path,
                    "-c",
                    f"safe.directory={self.repository_root.resolve()}",
                    "diff",
                    "--name-only",
                    "HEAD~1...HEAD",
                ],
                cwd=self.repository_root,
                text=True,
                stderr=subprocess.DEVNULL,
            )
            return [line for line in output.splitlines() if line]
        except (OSError, subprocess.SubprocessError):
            return []

    def scan(self, *, changed_only: bool = True, changed_files: list[str] | None = None) -> dict[str, Any]:
        files = (
            changed_files
            if changed_files is not None
            else (self.changed_files() if changed_only else self._all_files())
        )
        metadata_files = [path for path in files if self.path_filter.is_training_metadata_path(path)]
        changed_path_hashes = [sha256_hex(path) for path in metadata_files]
        risk_summary = self._metadata_risk_summary(metadata_files)
        report = {
            "status": "pass",
            "payload_policy": "passed",
            "project_namespace": self.project_namespace,
            "metadata_file_count": len(metadata_files),
            "changed_path_hashes": changed_path_hashes,
            "risk_summary": risk_summary.model_dump(mode="json"),
        }
        NoPayloadValidator().validate(report)
        event = CIScanEvent(
            project_namespace=self.project_namespace,
            repository_root_hash_sha256=sha256_hex(str(self.repository_root.resolve())),
            ci_provider=os.getenv("GITHUB_ACTIONS") and "github" or (os.getenv("GITLAB_CI") and "gitlab" or "local"),
            ci_run_id=os.getenv("GITHUB_RUN_ID") or os.getenv("CI_PIPELINE_ID") or "local",
            commit_hash_sha256=sha256_hex(os.getenv("GITHUB_SHA") or os.getenv("CI_COMMIT_SHA") or "local"),
            pull_request_id_hash=sha256_hex(os.getenv("GITHUB_REF", "")) if os.getenv("GITHUB_REF") else None,
            merge_request_id_hash=sha256_hex(os.getenv("CI_MERGE_REQUEST_IID", ""))
            if os.getenv("CI_MERGE_REQUEST_IID")
            else None,
            changed_path_hashes=changed_path_hashes,
            risk_summary=risk_summary,
            report_hash_sha256=canonical_sha256(report),
        )
        appended = AppendOnlyEventLog(self.ledger_path).append(event)
        report["event_hash_sha256"] = appended["event_hash_sha256"]
        return report

    def _all_files(self) -> list[str]:
        return [
            str(path.relative_to(self.repository_root))
            for path in self.repository_root.rglob("*")
            if path.is_file() and ".git" not in path.parts
        ]

    def _metadata_risk_summary(self, metadata_files: list[str]) -> RiskSummary:
        gatekeeper = RiskGatekeeper()
        flags = []
        for relative_path in metadata_files:
            metadata = self._load_metadata_mapping(relative_path)
            if metadata is None:
                continue
            NoPayloadValidator().validate(metadata)
            evaluated = gatekeeper.evaluate(metadata, model_id=str(metadata.get("project_namespace") or ""))
            flags.extend(evaluated.risk_flags)
        status = "high_risk" if any(flag.severity == "high" for flag in flags) else ("warn" if flags else "pass")
        return RiskSummary(status=status, risk_flags=flags)

    def _load_metadata_mapping(self, relative_path: str) -> dict[str, Any] | None:
        normalized = relative_path.replace("\\", "/")
        while normalized.startswith("./"):
            normalized = normalized[2:]
        parts = [part for part in normalized.split("/") if part]
        if any(self._has_subpath(parts, list(expected)) for expected in NON_METADATA_SUBPATHS):
            return None
        path = (self.repository_root / relative_path).resolve()
        try:
            path.relative_to(self.repository_root.resolve())
        except ValueError:
            return None
        if not path.exists() or not path.is_file() or path.suffix.lower() not in {".json", ".yaml", ".yml"}:
            return None
        if path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
        else:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return data if isinstance(data, dict) else None

    def _has_subpath(self, parts: list[str], expected: list[str]) -> bool:
        width = len(expected)
        return any(parts[index : index + width] == expected for index in range(len(parts) - width + 1))
