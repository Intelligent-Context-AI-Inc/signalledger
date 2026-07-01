from __future__ import annotations

from pathlib import Path
from typing import Any

from ecl_trainer.core.engine import EvaluationValueProcessor, SignalHasher
from ecl_trainer.core.ledger import AppendOnlyEventLog
from ecl_trainer.core.models import DataIngestEvent, EvalOutcomeEvent, ProvenanceDescriptor, TrainingCheckpointEvent
from ecl_trainer.core.policy import SourceUriPolicy, sha256_hex


class ECLTrainerCallback:
    def __init__(
        self,
        *,
        project_namespace: str,
        training_run_id: str,
        dataset_ref: str,
        ledger_path: str,
    ) -> None:
        self.project_namespace = project_namespace
        self.training_run_id = training_run_id
        self.dataset_ref = dataset_ref
        self.ledger = AppendOnlyEventLog(ledger_path)
        self.hasher = SignalHasher()
        self.last_dataset_hash: str | None = None

    def on_train_begin(self, args: Any = None, state: Any = None, control: Any = None, **kwargs: Any) -> None:
        result = register_hf_dataset(
            project_namespace=self.project_namespace,
            training_run_id=self.training_run_id,
            dataset_ref=self.dataset_ref,
            ledger_path=self.ledger.path,
        )
        self.last_dataset_hash = result["content_hash_sha256"]

    def on_save(self, args: Any = None, state: Any = None, control: Any = None, **kwargs: Any) -> None:
        checkpoint_id = str(getattr(state, "global_step", "checkpoint"))
        log_hf_checkpoint(
            project_namespace=self.project_namespace,
            training_run_id=self.training_run_id,
            checkpoint_id=checkpoint_id,
            exposed_dataset_hash=self.last_dataset_hash or sha256_hex(self.dataset_ref),
            ledger_path=self.ledger.path,
        )

    def on_evaluate(
        self,
        args: Any = None,
        state: Any = None,
        control: Any = None,
        metrics: dict | None = None,
        **kwargs: Any,
    ) -> None:
        log_hf_eval_outcome(
            project_namespace=self.project_namespace,
            training_run_id=self.training_run_id,
            checkpoint_id=str(getattr(state, "global_step", "checkpoint")),
            exposed_dataset_hashes=[self.last_dataset_hash or sha256_hex(self.dataset_ref)],
            metrics_delta=metrics or {},
            priority_vector={key: 1.0 for key in (metrics or {})},
            ledger_path=self.ledger.path,
        )


def register_hf_dataset(
    *,
    project_namespace: str,
    training_run_id: str,
    dataset_ref: str,
    ledger_path: str | Path,
) -> dict[str, Any]:
    source_policy = SourceUriPolicy()
    fingerprint = SignalHasher().fingerprint(source_uri=dataset_ref)
    event = DataIngestEvent(
        project_namespace=project_namespace,
        training_run_id=training_run_id,
        source_system_root_uri=source_policy.strip(dataset_ref),
        source_system_root_hash_sha256=fingerprint.source_root_hash_sha256,
        content_hash_sha256=fingerprint.dataset_fingerprint,
        schema_hash_sha256=fingerprint.schema_hash_sha256,
        chunk_manifest_hash_sha256=fingerprint.chunk_manifest_hash_sha256,
        token_count_estimates=fingerprint.token_count_estimates,
        provenance=ProvenanceDescriptor(origin_type="dataset_ref", origin_system="huggingface", synthetic_data=False),
    )
    return AppendOnlyEventLog(ledger_path).append(event)


def register_hf_training_run(
    *,
    project_namespace: str,
    training_run_id: str,
    dataset_ref: str,
    ledger_path: str | Path,
) -> dict[str, Any]:
    return register_hf_dataset(
        project_namespace=project_namespace,
        training_run_id=training_run_id,
        dataset_ref=dataset_ref,
        ledger_path=ledger_path,
    )


def log_hf_checkpoint(
    *,
    project_namespace: str,
    training_run_id: str,
    checkpoint_id: str,
    exposed_dataset_hash: str,
    ledger_path: str | Path,
) -> dict[str, Any]:
    event = TrainingCheckpointEvent(
        project_namespace=project_namespace,
        training_run_id=training_run_id,
        checkpoint_id=checkpoint_id,
        exposed_dataset_hash=exposed_dataset_hash,
        checkpoint_reference_hash_sha256=sha256_hex(checkpoint_id),
    )
    return AppendOnlyEventLog(ledger_path).append(event)


def log_hf_eval_outcome(
    *,
    project_namespace: str,
    training_run_id: str,
    checkpoint_id: str,
    exposed_dataset_hashes: list[str],
    metrics_delta: dict[str, float],
    priority_vector: dict[str, float],
    ledger_path: str | Path,
) -> dict[str, Any]:
    processor = EvaluationValueProcessor()
    delta = processor.scalar_delta(metrics_delta, priority_vector)
    event = EvalOutcomeEvent(
        project_namespace=project_namespace,
        training_run_id=training_run_id,
        checkpoint_id=checkpoint_id,
        exposed_dataset_hashes=exposed_dataset_hashes,
        metrics_delta=metrics_delta,
        priority_vector=priority_vector,
        delta_eval_scalar=delta,
        new_value_multiplier=processor.update_multiplier(1.0, delta),
    )
    return AppendOnlyEventLog(ledger_path).append(event)
