from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ecl_trainer.core.policy import NoPayloadValidator, sha256_hex
from ecl_trainer.core.serialization import canonical_json, canonical_sha256

DEFAULT_INCLUDE_PATTERNS: tuple[str, ...] = (
    "pyproject.toml",
    "MANIFEST.in",
    "Dockerfile.ecl-trainer",
    ".dockerignore",
    ".github/actions/ecl-trainer-scan/action.yml",
    ".github/workflows/ecl-trainer.yml",
    ".github/workflows/ecl-trainer-security.yml",
    "ecl_trainer/**/*.py",
    "ecl_trainer/py.typed",
    "atlas_pipeline/**/*.py",
    "atlas_sources/**/*.json",
)

BASE_IMAGE_RE = re.compile(r"^FROM\s+(?P<ref>[^\s@]+)(?:@sha256:(?P<digest>[a-f0-9]{64}))?", re.MULTILINE)


@dataclass(frozen=True)
class SupplyChainEvidenceGenerator:
    repository_root: str | Path = "."

    def generate(self) -> dict[str, Any]:
        root = Path(self.repository_root)
        entries = self._file_entries(root)
        sbom = {
            "schema": "ecl_trainer_supply_chain_sbom_v1",
            "generator": "ecl_trainer",
            "component_count": len(entries),
            "entries": entries,
            "sbom_hash_sha256": canonical_sha256(entries),
            "payload_policy": "metadata_only",
        }
        provenance = self._provenance(root, sbom)
        bundle = {
            "schema": "ecl_trainer_supply_chain_bundle_v1",
            "sbom": sbom,
            "provenance": provenance,
            "bundle_hash_sha256": canonical_sha256(
                {
                    "sbom_hash_sha256": sbom["sbom_hash_sha256"],
                    "provenance_hash_sha256": provenance["provenance_hash_sha256"],
                }
            ),
            "payload_policy": "passed",
        }
        NoPayloadValidator().validate(bundle)
        return bundle

    def write_outputs(self, output_dir: str | Path) -> dict[str, str]:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        bundle = self.generate()
        paths = {
            "sbom_json": out / "supply-chain-sbom.json",
            "provenance_json": out / "supply-chain-provenance.json",
            "manifest_json": out / "supply-chain-manifest.json",
        }
        paths["sbom_json"].write_text(canonical_json(bundle["sbom"]), encoding="utf-8")
        paths["provenance_json"].write_text(canonical_json(bundle["provenance"]), encoding="utf-8")
        manifest = {
            "schema": bundle["schema"],
            "bundle_hash_sha256": bundle["bundle_hash_sha256"],
            "sbom_hash_sha256": bundle["sbom"]["sbom_hash_sha256"],
            "provenance_hash_sha256": bundle["provenance"]["provenance_hash_sha256"],
            "output_files": {name: path.name for name, path in paths.items()},
            "payload_policy": "passed",
        }
        NoPayloadValidator().validate(manifest)
        paths["manifest_json"].write_text(canonical_json(manifest), encoding="utf-8")
        return {name: path.name for name, path in paths.items()}

    def _file_entries(self, root: Path) -> list[dict[str, Any]]:
        paths: set[Path] = set()
        for pattern in DEFAULT_INCLUDE_PATTERNS:
            paths.update(path for path in root.glob(pattern) if path.is_file())
        entries = []
        for path in sorted(paths, key=lambda item: item.as_posix()):
            relative_path = path.relative_to(root).as_posix()
            data = path.read_bytes()
            entries.append(
                {
                    "component_name": _component_name(relative_path),
                    "relative_path": relative_path,
                    "size_bytes": len(data),
                    "file_hash_sha256": sha256_hex(data),
                }
            )
        NoPayloadValidator().validate(entries)
        return entries

    def _provenance(self, root: Path, sbom: dict[str, Any]) -> dict[str, Any]:
        dockerfile = root / "Dockerfile.ecl-trainer"
        dockerfile_text = dockerfile.read_text(encoding="utf-8") if dockerfile.exists() else ""
        base_image = _base_image_metadata(dockerfile_text)
        atlas_manifest_hash = _directory_hash(root / "atlas_sources", "*.json")
        package_manifest_hash = _file_hash(root / "pyproject.toml")
        dockerfile_hash = _file_hash(dockerfile)
        provenance = {
            "schema": "ecl_trainer_supply_chain_provenance_v1",
            "build_mode": "local_only",
            "saas_account_required": False,
            "dataset_upload_performed": False,
            "raw_payload_absent": True,
            "base_image_ref": base_image["base_image_ref"],
            "base_image_digest_sha256": base_image["base_image_digest_sha256"],
            "dockerfile_hash_sha256": dockerfile_hash,
            "package_manifest_hash_sha256": package_manifest_hash,
            "atlas_source_manifest_hash_sha256": atlas_manifest_hash,
            "sbom_hash_sha256": sbom["sbom_hash_sha256"],
            "component_count": sbom["component_count"],
            "provenance_hash_sha256": "",
        }
        provenance["provenance_hash_sha256"] = canonical_sha256({**provenance, "provenance_hash_sha256": ""})
        NoPayloadValidator().validate(provenance)
        return provenance


def _component_name(relative_path: str) -> str:
    if relative_path.startswith("ecl_trainer/"):
        return "ecl_trainer_sdk"
    if relative_path.startswith("atlas_pipeline/"):
        return "intelligent_context_atlas_pipeline"
    if relative_path.startswith("atlas_sources/"):
        return "intelligent_context_atlas_sources"
    if relative_path.startswith(".github/"):
        return "github_action_distribution"
    if relative_path == "Dockerfile.ecl-trainer":
        return "ecl_trainer_container"
    return "ecl_trainer_distribution"


def _base_image_metadata(dockerfile_text: str) -> dict[str, str]:
    match = BASE_IMAGE_RE.search(dockerfile_text)
    if match is None:
        return {"base_image_ref": "unknown", "base_image_digest_sha256": ""}
    return {
        "base_image_ref": match.group("ref"),
        "base_image_digest_sha256": match.group("digest") or "",
    }


def _file_hash(path: Path) -> str:
    return sha256_hex(path.read_bytes()) if path.exists() and path.is_file() else ""


def _directory_hash(root: Path, pattern: str) -> str:
    if not root.exists():
        return ""
    entries = []
    for path in sorted(root.rglob(pattern), key=lambda item: item.as_posix()):
        if path.is_file():
            entries.append(
                {
                    "relative_path": path.relative_to(root).as_posix(),
                    "file_hash_sha256": sha256_hex(path.read_bytes()),
                }
            )
    return canonical_sha256(entries)
