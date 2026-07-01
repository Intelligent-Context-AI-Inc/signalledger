from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError
from typer.testing import CliRunner

from ecl_trainer.ci.reporting import CIReportRenderer
from ecl_trainer.ci.scanner import CIScanner
from ecl_trainer.cli import app
from ecl_trainer.compliance.pr_comment import PullRequestCommentRenderer
from ecl_trainer.compliance.registries import BenchmarkRegistry, ModelLineageRegistry
from ecl_trainer.compliance.reports import CompliancePassportGenerator
from ecl_trainer.compliance.risk import RiskGatekeeper
from ecl_trainer.core.client import SaaSControlPlaneClient, SigningConfig
from ecl_trainer.core.engine import EvaluationValueProcessor
from ecl_trainer.core.exceptions import PayloadExfiltrationException
from ecl_trainer.core.ledger import AppendOnlyEventLog, HashChainVerifier, LocalEventReplay
from ecl_trainer.core.models import DataIngestEvent, ModelLineageRecord, ProvenanceDescriptor, SignedLedgerEnvelope
from ecl_trainer.core.policy import NoPayloadValidator, SourceUriPolicy, sha256_hex, validate_rendered_text
from ecl_trainer.core.serialization import canonical_json, canonical_sha256
from ecl_trainer.hub.huggingface_cards import HuggingFaceCardExporter
from ecl_trainer.integrations.axolotl import load_axolotl_config_metadata
from ecl_trainer.integrations.huggingface import register_hf_dataset
from ecl_trainer.integrations.pytorch import ECLCheckpointLogger
from ecl_trainer.integrations.ray import register_ray_dataset


@dataclass
class UnsafeDataclass:
    prompt: str


class UnsafePydanticModel(BaseModel):
    prompt: str


ATTACKS = [
    {"text": "sentinel"},
    {"nested": {"prompt": "sentinel"}},
    {"Prompt": "sentinel"},
    {"tokenIds": [1, 2, 3]},
    {"token_sequence": [1, 2, 3]},
    {"safe": [{"completion": "sentinel"}]},
    {"metric_ids": [1, 2, 3, 4, 5, 6, 7, 8]},
    {"metric_values": [0.1, 0.2, 0.3, 0.4]},
    {"binary_blob_hash": b"sentinel"},
    {"encoded_reference": "A" * 200},
    {"notes": "X" * 1100},
    {"markdown_summary": "```"},
    {"metadata": '{"prompt":"sentinel"}'},
    {"diff_hunk": "sentinel"},
    {"notebook_cell": "sentinel"},
    {"checkpoint_bytes": "sentinel"},
    {"weights": "sentinel"},
    {"reference": "token=sentinel"},
    {"reference": "/Users/sentinel/path"},
    {"file_content": "sentinel"},
    {"source_content": "sentinel"},
    {"repo_content": "sentinel"},
]


def safe_ingest_event() -> DataIngestEvent:
    return DataIngestEvent(
        project_namespace="project",
        source_system_root_uri="s3://bucket",
        source_system_root_hash_sha256=sha256_hex("s3://bucket"),
        content_hash_sha256=sha256_hex("dataset"),
        schema_hash_sha256=sha256_hex("schema"),
        chunk_manifest_hash_sha256=sha256_hex("chunks"),
        provenance=ProvenanceDescriptor(origin_type="registry", origin_system="internal"),
    )


@pytest.mark.parametrize("attack", ATTACKS)
def test_validator_rejects_adversarial_payload_shapes(attack):
    with pytest.raises(PayloadExfiltrationException):
        NoPayloadValidator().validate(attack)


def test_markdown_summary_cannot_bypass_long_text_guard():
    with pytest.raises(PayloadExfiltrationException):
        NoPayloadValidator().validate({"markdown_summary": "lorem ipsum " * 200})


def test_rendered_text_validation_allows_long_documents_when_lines_are_bounded():
    validate_rendered_text("\n".join(["metadata_only_line"] * 300))


def test_rendered_text_validation_rejects_single_oversized_line():
    with pytest.raises(PayloadExfiltrationException):
        validate_rendered_text("A" * 5000)


@pytest.mark.parametrize(
    "key",
    [
        "rawdata",
        "RAWDATA",
        "fulltext",
        "FULLTEXT",
        "userprompt",
        "bodytext",
        "embeddingvec",
        "EMBEDDINGVEC",
        "securetoken",
    ],
)
def test_validator_rejects_concatenated_payload_like_keys(key):
    with pytest.raises(PayloadExfiltrationException):
        NoPayloadValidator().validate({key: "synthetic-forbidden-class-marker-string"})


def test_validator_scans_dataclasses_and_pydantic_models():
    with pytest.raises(PayloadExfiltrationException):
        NoPayloadValidator().validate(UnsafeDataclass(prompt="sentinel"))
    with pytest.raises(PayloadExfiltrationException):
        NoPayloadValidator().validate(UnsafePydanticModel(prompt="sentinel"))


def test_model_construction_rejects_payload_fields():
    with pytest.raises(ValidationError):
        DataIngestEvent(
            project_namespace="project",
            source_system_root_uri="s3://bucket",
            source_system_root_hash_sha256=sha256_hex("s3://bucket"),
            content_hash_sha256=sha256_hex("dataset"),
            schema_hash_sha256=sha256_hex("schema"),
            chunk_manifest_hash_sha256=sha256_hex("chunks"),
            provenance=ProvenanceDescriptor(origin_type="registry", origin_system="internal"),
            prompt="sentinel",
        )


def test_serialization_rejects_unsafe_metadata_before_hashing():
    with pytest.raises(PayloadExfiltrationException):
        canonical_json({"prompt": "sentinel"})
    with pytest.raises(PayloadExfiltrationException):
        canonical_sha256({"prompt": "sentinel"})


def test_canonical_hash_is_order_stable_and_change_sensitive():
    assert canonical_sha256({"b": 2, "a": 1}) == canonical_sha256({"a": 1, "b": 2})
    assert canonical_sha256({"a": 1}) != canonical_sha256({"a": 2})


def test_ledger_append_replay_and_tamper_boundaries(tmp_path: Path):
    path = tmp_path / "events.jsonl"
    log = AppendOnlyEventLog(path)
    log.append(safe_ingest_event())
    log.append(safe_ingest_event())
    assert HashChainVerifier(path).verify()["valid"] is True
    assert list(LocalEventReplay(path).iter_events())
    with pytest.raises(PayloadExfiltrationException):
        log.append({"event_type": "data_ingest", "prompt": "sentinel"})

    original = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join(reversed(original)) + "\n", encoding="utf-8")
    assert HashChainVerifier(path).verify()["valid"] is False


def test_ledger_detects_deleted_inserted_and_modified_lines(tmp_path: Path):
    path = tmp_path / "events.jsonl"
    log = AppendOnlyEventLog(path)
    log.append(safe_ingest_event())
    log.append(safe_ingest_event())
    lines = path.read_text(encoding="utf-8").splitlines()

    deleted = tmp_path / "deleted.jsonl"
    deleted.write_text(lines[1] + "\n", encoding="utf-8")
    assert HashChainVerifier(deleted).verify()["valid"] is False

    inserted = tmp_path / "inserted.jsonl"
    inserted.write_text(lines[0] + "\n" + lines[0] + "\n" + lines[1] + "\n", encoding="utf-8")
    assert HashChainVerifier(inserted).verify()["valid"] is False

    modified = tmp_path / "modified.jsonl"
    modified_line = lines[0].replace(
        '"previous_event_hash_sha256":null',
        '"previous_event_hash_sha256":"0"',
    )
    modified.write_text(modified_line + "\n", encoding="utf-8")
    assert HashChainVerifier(modified).verify()["valid"] is False


def test_signed_envelope_and_saas_submission_reject_payload_before_network():
    client = SaaSControlPlaneClient(
        endpoint_url="https://ledger.invalid",
        tenant_id="tenant",
        project_namespace="project",
        api_key="metadata-only-token",
        signing_config=SigningConfig(secret="signing-secret"),
    )
    envelope = client._envelope("data_ingest", {"content_hash_sha256": sha256_hex("dataset")})
    assert envelope.payload_hash_sha256 == sha256_hex(canonical_json(envelope.payload))
    with pytest.raises(PayloadExfiltrationException):
        client.register_dataset({"prompt": "sentinel"})
    with pytest.raises((PayloadExfiltrationException, ValidationError)):
        SignedLedgerEnvelope(
            event_type="data_ingest",
            tenant_id_hash=sha256_hex("tenant"),
            project_namespace="project",
            payload_hash_sha256=sha256_hex("payload"),
            payload={"prompt": "sentinel"},
            signature="signature",
        )


def test_markdown_and_report_boundaries_reject_payload_fields(tmp_path: Path):
    with pytest.raises(PayloadExfiltrationException):
        PullRequestCommentRenderer().render({"diff_hunk": "sentinel"})
    with pytest.raises(PayloadExfiltrationException):
        PullRequestCommentRenderer().render({"notebook_cell": "sentinel"})
    with pytest.raises(PayloadExfiltrationException):
        CIReportRenderer().render_markdown({"diff_hunk": "sentinel"})
    generator = CompliancePassportGenerator(tmp_path / "events.jsonl")
    with pytest.raises(PayloadExfiltrationException):
        generator.render_markdown(
            {
                "report_profile": "legal_executive_summary",
                "event_count": 0,
                "hash_chain_verification": {"valid": True},
                "risk_flags": [],
                "diff_hunk": "sentinel",
            }
        )


def test_huggingface_card_export_rejects_payload_fields():
    with pytest.raises(PayloadExfiltrationException):
        HuggingFaceCardExporter().export({"prompt": "sentinel"})


def test_cli_scan_output_is_metadata_only(tmp_path: Path, monkeypatch):
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["scan", "--project-namespace", "project"])
    assert result.exit_code == 0
    assert "ECL Pre-Flight Shield" in result.output
    assert "configs/train.yaml" not in result.output


def test_ci_scan_hashes_changed_paths_and_does_not_echo_paths(tmp_path: Path):
    report = CIScanner(repository_root=tmp_path, ledger_path=tmp_path / "events.jsonl").scan(
        changed_files=["configs/train.yaml", "datasets/private.jsonl"]
    )
    rendered = canonical_json(report)
    assert "configs/train.yaml" not in rendered
    assert "datasets/private.jsonl" not in rendered
    assert len(report["changed_path_hashes"]) == 2


def test_callbacks_strip_local_dataset_references(tmp_path: Path):
    event = register_hf_dataset(
        project_namespace="project",
        training_run_id="run",
        dataset_ref="/Users/sentinel/dataset",
        ledger_path=tmp_path / "events.jsonl",
    )
    assert event["source_system_root_uri"].startswith("file://")
    assert "/Users/" not in canonical_json(event)
    ray_event = register_ray_dataset(
        project_namespace="project",
        training_run_id="run",
        dataset_ref="/Users/sentinel/ray",
        ledger_path=tmp_path / "ray.jsonl",
    )
    assert ray_event["source_system_root_uri"].startswith("file://")


def test_axolotl_rejects_payload_config_and_strips_paths(tmp_path: Path):
    unsafe = tmp_path / "unsafe.yaml"
    unsafe.write_text("prompt: sentinel\n", encoding="utf-8")
    metadata = load_axolotl_config_metadata(unsafe)
    assert "prompt" not in metadata

    safe = tmp_path / "safe.yaml"
    safe.write_text("dataset_prepared_path: /Users/sentinel/data\noutput_dir: /Users/sentinel/out\n", encoding="utf-8")
    metadata = load_axolotl_config_metadata(safe)
    assert metadata["dataset_prepared_path"].startswith("file://")
    assert metadata["output_dir"].startswith("file://")


def test_pytorch_checkpoint_logger_stores_reference_hash_only(tmp_path: Path):
    logger = ECLCheckpointLogger(
        project_namespace="project",
        training_run_id="run",
        ledger_path=tmp_path / "events.jsonl",
    )
    event = logger.log(checkpoint_id="checkpoint_001", exposed_dataset_hash=sha256_hex("dataset"))
    assert event["checkpoint_reference_hash_sha256"] == sha256_hex("checkpoint_001")
    assert "checkpoint_bytes" not in canonical_json(event)


def test_source_uri_policy_strips_roots():
    policy = SourceUriPolicy()
    s3_uri = "s3://bucket/path/to/file.parquet"
    gs_uri = "gs://bucket/path/to/file.parquet"
    azure_uri = "azure://container/path/file.jsonl"
    https_uri = "https://host/org/repo/blob/path"
    local_uri = "file:///private/path/dataset.jsonl"
    assert policy.strip(s3_uri) == "s3://bucket"
    assert policy.strip(gs_uri) == "gs://bucket"
    assert policy.strip(azure_uri) == "azure://container"
    assert policy.strip(https_uri) == "https://host"
    assert policy.strip(local_uri).startswith("file://")


def test_risk_engine_metadata_only_detection():
    registry = BenchmarkRegistry()
    registry.extend(source_root_hashes=[sha256_hex("benchmark")])
    summary = RiskGatekeeper(benchmark_registry=registry).evaluate(
        {"benchmark_family_indicator": "mmlu", "split_name": "test", "source_root_hash_sha256": sha256_hex("benchmark")}
    )
    assert summary.risk_flags
    assert "sentinel" not in canonical_json(summary)

    lineage = ModelLineageRegistry()
    lineage.add(ModelLineageRecord(model_id="origin", base_model_family="family"))
    lineage.add(ModelLineageRecord(model_id="target", base_model_family="family", ancestor_model_ids=["ancestor"]))
    inbreeding = RiskGatekeeper(lineage_registry=lineage).evaluate({"origin_model_id": "origin"}, model_id="target")
    assert inbreeding.risk_flags


def test_value_processor_rejects_raw_eval_fields():
    processor = EvaluationValueProcessor()
    assert processor.scalar_delta({"metric_a": 0.02}, {"metric_a": 1.0}) == 0.02
    with pytest.raises(PayloadExfiltrationException):
        NoPayloadValidator().validate({"eval_samples": ["sentinel"]})
