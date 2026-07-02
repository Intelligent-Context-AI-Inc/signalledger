import json
from pathlib import Path

import pytest

from ecl_trainer.core.exceptions import PayloadExfiltrationException
from ecl_trainer.core.models import (
    CIScanEvent,
    DataIngestEvent,
    EvalOutcomeEvent,
    ProvenanceDescriptor,
    RiskSummary,
    SemanticTag,
)
from ecl_trainer.core.policy import NoPayloadValidator, sha256_hex
from ecl_trainer.core.serialization import canonical_json


@pytest.mark.parametrize(
    "key",
    ["text", "prompt", "input_ids", "embedding", "weights", "diff_hunk", "notebook_cell"],
)
def test_forbidden_keys_raise(key):
    with pytest.raises(PayloadExfiltrationException):
        NoPayloadValidator().validate({key: "blocked"})


def test_semantic_tag_safety_assertion_is_allowed():
    tag = SemanticTag(namespace="domain", key="category", value="metadata_only", raw_value_absent=True)
    NoPayloadValidator().validate(tag)


def test_valid_data_ingest_serializes():
    event = DataIngestEvent(
        project_namespace="project",
        source_system_root_uri="s3://bucket",
        source_system_root_hash_sha256=sha256_hex("s3://bucket"),
        content_hash_sha256=sha256_hex("dataset"),
        schema_hash_sha256=sha256_hex("schema"),
        chunk_manifest_hash_sha256=sha256_hex("chunks"),
        provenance=ProvenanceDescriptor(origin_type="registry", origin_system="internal"),
    )
    assert "data_ingest" in canonical_json(event)


def test_valid_eval_and_ci_events_serialize():
    eval_event = EvalOutcomeEvent(
        project_namespace="project",
        training_run_id="run",
        checkpoint_id="ckpt",
        metrics_delta={"accuracy": 0.1},
        priority_vector={"accuracy": 1.0},
    )
    ci_event = CIScanEvent(
        project_namespace="project",
        repository_root_hash_sha256=sha256_hex("repo"),
        ci_provider="local",
        ci_run_id="run",
        commit_hash_sha256=sha256_hex("commit"),
        risk_summary=RiskSummary(),
        report_hash_sha256=sha256_hex("report"),
    )
    assert "eval_outcome" in canonical_json(eval_event)
    assert "ci_scan" in canonical_json(ci_event)


@pytest.mark.parametrize(
    "example_path",
    [
        "examples/github_action/ecl-trainer.manifest.json",
        "examples/interactive_demo_repo/safe-manifest.json",
        "examples/atlas_pack_sources/healthcare_clinical_source.safe.json",
    ],
)
def test_advertised_safe_manifest_examples_pass_no_payload_validator(example_path):
    data = json.loads(Path(example_path).read_text(encoding="utf-8"))

    NoPayloadValidator().validate(data)
