from __future__ import annotations

import json

from typer.testing import CliRunner

from ecl_trainer.cli import app
from ecl_trainer.core.policy import NoPayloadValidator
from ecl_trainer.security.supply_chain import SupplyChainEvidenceGenerator


def test_supply_chain_evidence_is_metadata_only() -> None:
    bundle = SupplyChainEvidenceGenerator().generate()

    assert bundle["sbom"]["component_count"] > 0
    assert bundle["provenance"]["saas_account_required"] is False
    assert bundle["provenance"]["dataset_upload_performed"] is False
    assert bundle["provenance"]["raw_payload_absent"] is True
    assert len(bundle["bundle_hash_sha256"]) == 64
    NoPayloadValidator().validate(bundle)


def test_supply_chain_evidence_cli_writes_bundle(tmp_path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "supply-chain-evidence",
            "--repository-root",
            ".",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    paths = json.loads(result.output)
    assert (tmp_path / paths["sbom_json"]).exists()
    assert (tmp_path / paths["provenance_json"]).exists()
    assert (tmp_path / paths["manifest_json"]).exists()
    manifest = json.loads((tmp_path / paths["manifest_json"]).read_text(encoding="utf-8"))
    assert manifest["payload_policy"] == "passed"
    NoPayloadValidator().validate(manifest)
