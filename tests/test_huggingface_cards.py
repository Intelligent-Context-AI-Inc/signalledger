from ecl_trainer.hub.huggingface_cards import HuggingFaceCardExporter


def test_huggingface_card_exporter_metadata_only():
    exported = HuggingFaceCardExporter().export(
        {
            "ecl_fingerprint": "abc",
            "compliance_passport_hash": "def",
            "source_root_hashes": ["ghi"],
            "license_matrix": [],
        }
    )
    assert "ECL Training Metadata" in exported["model_card_section"]
    assert "ECL Dataset Metadata" in exported["dataset_card_section"]
