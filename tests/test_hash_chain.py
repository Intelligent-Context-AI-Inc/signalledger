from pathlib import Path

from ecl_trainer.core.ledger import AppendOnlyEventLog, HashChainVerifier
from ecl_trainer.core.models import DataIngestEvent, ProvenanceDescriptor
from ecl_trainer.core.policy import sha256_hex


def _event():
    return DataIngestEvent(
        project_namespace="project",
        source_system_root_uri="s3://bucket",
        source_system_root_hash_sha256=sha256_hex("s3://bucket"),
        content_hash_sha256=sha256_hex("dataset"),
        schema_hash_sha256=sha256_hex("schema"),
        chunk_manifest_hash_sha256=sha256_hex("chunks"),
        provenance=ProvenanceDescriptor(origin_type="registry", origin_system="internal"),
    )


def test_hash_chain_passes_for_unmodified_log(tmp_path: Path):
    log = AppendOnlyEventLog(tmp_path / "events.jsonl")
    first = log.append(_event())
    second = log.append(_event())
    assert first["event_hash_sha256"] != second["event_hash_sha256"]
    assert HashChainVerifier(tmp_path / "events.jsonl").verify()["valid"] is True


def test_hash_chain_fails_for_tampered_log(tmp_path: Path):
    path = tmp_path / "events.jsonl"
    log = AppendOnlyEventLog(path)
    log.append(_event())
    content = path.read_text(encoding="utf-8").replace("project", "changed", 1)
    path.write_text(content, encoding="utf-8")
    assert HashChainVerifier(path).verify()["valid"] is False
