from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ecl_trainer.core.engine import SignalHasher
from ecl_trainer.core.ledger import AppendOnlyEventLog
from ecl_trainer.core.models import DataIngestEvent, ProvenanceDescriptor
from ecl_trainer.core.policy import NoPayloadValidator, SourceUriPolicy, sha256_hex
from ecl_trainer.integrations.huggingface import log_hf_checkpoint, log_hf_eval_outcome

SAFE_AXOLOTL_KEYS = {"base_model", "datasets", "dataset_prepared_path", "sequence_len", "output_dir"}


def load_axolotl_config_metadata(config_path: str | Path) -> dict[str, Any]:
    data = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
    metadata = {key: data.get(key) for key in SAFE_AXOLOTL_KEYS if key in data}
    if "datasets" in metadata:
        metadata["datasets"] = sha256_hex(str(metadata["datasets"]))
    if "dataset_prepared_path" in metadata:
        metadata["dataset_prepared_path"] = SourceUriPolicy().strip(str(metadata["dataset_prepared_path"]))
    if "output_dir" in metadata:
        metadata["output_dir"] = SourceUriPolicy().strip(str(metadata["output_dir"]))
    NoPayloadValidator().validate(metadata)
    return metadata


class ECLAxolotlPlugin:
    def __init__(
        self,
        *,
        project_namespace: str,
        training_run_id: str,
        config_path: str | Path,
        ledger_path: str | Path,
    ) -> None:
        self.project_namespace = project_namespace
        self.training_run_id = training_run_id
        self.config_path = Path(config_path)
        self.ledger_path = ledger_path

    def on_train_start(self) -> dict[str, Any]:
        return register_axolotl_training_run(
            project_namespace=self.project_namespace,
            training_run_id=self.training_run_id,
            config_path=self.config_path,
            ledger_path=self.ledger_path,
        )


def register_axolotl_training_run(
    *,
    project_namespace: str,
    training_run_id: str,
    config_path: str | Path,
    ledger_path: str | Path,
) -> dict[str, Any]:
    metadata = load_axolotl_config_metadata(config_path)
    source = str(metadata.get("dataset_prepared_path") or config_path)
    source_policy = SourceUriPolicy()
    fingerprint = SignalHasher().fingerprint(source_uri=source, schema=metadata)
    event = DataIngestEvent(
        project_namespace=project_namespace,
        training_run_id=training_run_id,
        source_system_root_uri=source_policy.strip(source),
        source_system_root_hash_sha256=fingerprint.source_root_hash_sha256,
        content_hash_sha256=fingerprint.dataset_fingerprint,
        schema_hash_sha256=fingerprint.schema_hash_sha256,
        chunk_manifest_hash_sha256=fingerprint.chunk_manifest_hash_sha256,
        token_count_estimates=fingerprint.token_count_estimates,
        provenance=ProvenanceDescriptor(origin_type="config_ref", origin_system="axolotl", synthetic_data=False),
    )
    return AppendOnlyEventLog(ledger_path).append(event)


def log_axolotl_checkpoint(
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


def log_axolotl_eval_outcome(
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
