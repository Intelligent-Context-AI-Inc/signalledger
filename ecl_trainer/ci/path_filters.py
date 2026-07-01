from __future__ import annotations

from pathlib import Path

TRAINING_METADATA_PATTERNS = (
    "configs/",
    "data/",
    "datasets/",
    "schemas/",
    "training/",
    "finetune/",
    "axolotl/",
    "recipes/",
    "notebooks/",
)

TRAINING_METADATA_FILES = {
    "model_card.md",
    "dataset_card.md",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "environment.yml",
    "environment.yaml",
}

class PathFilter:
    def is_training_metadata_path(self, path: str | Path) -> bool:
        text = str(path).replace("\\", "/")
        while text.startswith("./"):
            text = text[2:]
        parts = [part for part in text.split("/") if part]
        if ".github" in parts:
            return False
        if self._has_subpath(parts, ["ecl_trainer", "red_team_fixtures"]):
            return False
        if self._has_subpath(parts, ["tests", "red_team_fixtures"]):
            return False
        if self._has_subpath(parts, ["examples", "github_action"]):
            return False
        name = text.rsplit("/", 1)[-1]
        if name in TRAINING_METADATA_FILES:
            return True
        if any(text.startswith(prefix) or f"/{prefix}" in text for prefix in TRAINING_METADATA_PATTERNS):
            return True
        return text.endswith((".yaml", ".yml", ".toml", ".json", ".md")) and any(
            marker in text.lower() for marker in ("model", "dataset", "train", "schema", "axolotl")
        )

    def _has_subpath(self, parts: list[str], expected: list[str]) -> bool:
        width = len(expected)
        return any(parts[index : index + width] == expected for index in range(len(parts) - width + 1))
