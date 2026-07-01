from __future__ import annotations

from typing import Any

from ecl_trainer.core.policy import NoPayloadValidator, validate_rendered_text


class ModelCardECLSection:
    def render(self, metadata: dict[str, Any]) -> str:
        NoPayloadValidator().validate(metadata)
        lines = [
            "## ECL Training Metadata",
            f"- ECL fingerprint: `{metadata.get('ecl_fingerprint', 'unavailable')}`",
            f"- Compliance passport hash: `{metadata.get('compliance_passport_hash', 'unavailable')}`",
            f"- Benchmark risk: `{metadata.get('benchmark_risk', 'unknown')}`",
            f"- Model lineage risk: `{metadata.get('model_lineage_risk', 'unknown')}`",
        ]
        markdown = "\n".join(lines) + "\n"
        validate_rendered_text(markdown)
        return markdown


class DatasetCardECLSection:
    def render(self, metadata: dict[str, Any]) -> str:
        NoPayloadValidator().validate(metadata)
        lines = [
            "## ECL Dataset Metadata",
            f"- Source-root hashes: `{len(metadata.get('source_root_hashes', []))}`",
            f"- License descriptors: `{len(metadata.get('license_matrix', []))}`",
            f"- Synthetic data indicator: `{metadata.get('synthetic_data_indicator', 'unknown')}`",
        ]
        markdown = "\n".join(lines) + "\n"
        validate_rendered_text(markdown)
        return markdown


class HuggingFaceCardExporter:
    def model_card_section(self, metadata: dict[str, Any]) -> str:
        return ModelCardECLSection().render(metadata)

    def dataset_card_section(self, metadata: dict[str, Any]) -> str:
        return DatasetCardECLSection().render(metadata)

    def export(self, metadata: dict[str, Any]) -> dict[str, str]:
        return {
            "model_card_section": self.model_card_section(metadata),
            "dataset_card_section": self.dataset_card_section(metadata),
        }
