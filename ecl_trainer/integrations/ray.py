from __future__ import annotations

from pathlib import Path
from typing import Any

from ecl_trainer.integrations.huggingface import log_hf_checkpoint, log_hf_eval_outcome, register_hf_dataset


class ECLRayTrainCallback:
    def __init__(
        self,
        *,
        project_namespace: str,
        training_run_id: str,
        dataset_ref: str,
        ledger_path: str | Path,
    ) -> None:
        self.project_namespace = project_namespace
        self.training_run_id = training_run_id
        self.dataset_ref = dataset_ref
        self.ledger_path = ledger_path
        self.dataset_hash: str | None = None

    def start_training(self) -> None:
        event = register_ray_dataset(
            project_namespace=self.project_namespace,
            training_run_id=self.training_run_id,
            dataset_ref=self.dataset_ref,
            ledger_path=self.ledger_path,
        )
        self.dataset_hash = event["content_hash_sha256"]


def register_ray_dataset(
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


def log_ray_checkpoint(
    *,
    project_namespace: str,
    training_run_id: str,
    checkpoint_id: str,
    exposed_dataset_hash: str,
    ledger_path: str | Path,
) -> dict[str, Any]:
    return log_hf_checkpoint(
        project_namespace=project_namespace,
        training_run_id=training_run_id,
        checkpoint_id=checkpoint_id,
        exposed_dataset_hash=exposed_dataset_hash,
        ledger_path=ledger_path,
    )


def log_ray_eval_outcome(
    *,
    project_namespace: str,
    training_run_id: str,
    checkpoint_id: str,
    exposed_dataset_hashes: list[str],
    metrics_delta: dict[str, float],
    priority_vector: dict[str, float],
    ledger_path: str | Path,
) -> dict[str, Any]:
    return log_hf_eval_outcome(
        project_namespace=project_namespace,
        training_run_id=training_run_id,
        checkpoint_id=checkpoint_id,
        exposed_dataset_hashes=exposed_dataset_hashes,
        metrics_delta=metrics_delta,
        priority_vector=priority_vector,
        ledger_path=ledger_path,
    )
