from __future__ import annotations

from pathlib import Path
from typing import Any

from ecl_trainer.core.engine import SignalHasher
from ecl_trainer.core.ledger import AppendOnlyEventLog
from ecl_trainer.core.models import DataIngestEvent, ProvenanceDescriptor, TrainingCheckpointEvent
from ecl_trainer.core.policy import SourceUriPolicy, sha256_hex


def register_torch_dataloader(
    *,
    project_namespace: str,
    training_run_id: str,
    dataloader_ref: str,
    ledger_path: str | Path,
) -> dict[str, Any]:
    source_policy = SourceUriPolicy()
    fingerprint = SignalHasher().fingerprint(source_uri=dataloader_ref)
    event = DataIngestEvent(
        project_namespace=project_namespace,
        training_run_id=training_run_id,
        source_system_root_uri=source_policy.strip(dataloader_ref),
        source_system_root_hash_sha256=fingerprint.source_root_hash_sha256,
        content_hash_sha256=fingerprint.dataset_fingerprint,
        schema_hash_sha256=fingerprint.schema_hash_sha256,
        chunk_manifest_hash_sha256=fingerprint.chunk_manifest_hash_sha256,
        token_count_estimates=fingerprint.token_count_estimates,
        provenance=ProvenanceDescriptor(origin_type="dataloader_ref", origin_system="pytorch", synthetic_data=False),
    )
    return AppendOnlyEventLog(ledger_path).append(event)


class ECLCheckpointLogger:
    def __init__(self, *, project_namespace: str, training_run_id: str, ledger_path: str | Path) -> None:
        self.project_namespace = project_namespace
        self.training_run_id = training_run_id
        self.ledger_path = ledger_path

    def log(self, *, checkpoint_id: str, exposed_dataset_hash: str) -> dict[str, Any]:
        event = TrainingCheckpointEvent(
            project_namespace=self.project_namespace,
            training_run_id=self.training_run_id,
            checkpoint_id=checkpoint_id,
            exposed_dataset_hash=exposed_dataset_hash,
            checkpoint_reference_hash_sha256=sha256_hex(checkpoint_id),
        )
        return AppendOnlyEventLog(self.ledger_path).append(event)
