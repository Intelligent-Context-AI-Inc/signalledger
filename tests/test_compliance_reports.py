from ecl_trainer.compliance.reports import CompliancePassportGenerator
from ecl_trainer.core.ledger import AppendOnlyEventLog
from ecl_trainer.core.models import DataIngestEvent, ProvenanceDescriptor, ReportProfile
from ecl_trainer.core.policy import sha256_hex


def test_compliance_passport_generates_metadata_only_report(tmp_path):
    ledger_path = tmp_path / "events.jsonl"
    AppendOnlyEventLog(ledger_path).append(
        DataIngestEvent(
            project_namespace="project",
            source_system_root_uri="s3://bucket",
            source_system_root_hash_sha256=sha256_hex("s3://bucket"),
            content_hash_sha256=sha256_hex("dataset"),
            schema_hash_sha256=sha256_hex("schema"),
            chunk_manifest_hash_sha256=sha256_hex("chunks"),
            provenance=ProvenanceDescriptor(origin_type="registry", origin_system="internal"),
        )
    )
    generator = CompliancePassportGenerator(ledger_path)
    report = generator.generate(profile=ReportProfile.MODEL_RELEASE_SIGNOFF, project_namespace="project")
    markdown = generator.render_markdown(report)
    assert report["event_count"] == 1
    assert "ECL Training Passport" in markdown
