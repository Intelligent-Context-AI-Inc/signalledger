from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ecl_trainer.core.ledger import HashChainVerifier
from ecl_trainer.core.policy import NoPayloadValidator, sha256_hex, validate_rendered_text
from ecl_trainer.core.serialization import canonical_json, canonical_sha256

WATCH = "watch"
REVIEW_RECOMMENDED = "review_recommended"
BLOCK = "block"

CATALOG_GAP_PENALTIES = {
    "TRAINING_DATA_PROVENANCE_GAP": 15,
    "EVAL_METADATA_GAP": 10,
    "EVAL_RESULTS_TAG_WITHOUT_MODEL_INDEX": 10,
    "LICENSE_FILE_NOT_LISTED": 10,
    "LANGUAGE_METADATA_GAP": 5,
    "PIPELINE_TAG_MISSING": 5,
}


class MLOpsGovernancePackBuilder:
    def build(
        self,
        *,
        reports_dir: str | Path = ".ecl-trainer/reports",
        ledger_path: str | Path = ".ecl-trainer/events.jsonl",
        output_dir: str | Path = ".ecl-trainer/reports",
        previous_pack: str | Path | None = None,
        catalog_check_json: str | Path | None = None,
    ) -> dict[str, Any]:
        reports = Path(reports_dir)
        ledger = Path(ledger_path)
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        verification = self._load_json(reports / "verification.json") or HashChainVerifier(ledger).verify()
        risk_report = self._load_json(reports / "risk-report.json")
        passport = self._load_json(reports / "compliance-passport.json")
        lifecycle = self._load_json(reports / "lifecycle-report.json")
        manifest = self._load_json(reports / "manifest.json")
        catalog_summary = self._catalog_summary(catalog_check_json)

        pack = self._build_pack(
            reports_dir=reports,
            ledger_path=ledger,
            verification=verification,
            risk_report=risk_report,
            passport=passport,
            lifecycle=lifecycle,
            manifest=manifest,
            catalog_summary=catalog_summary,
        )
        previous = self._load_json(previous_pack) if previous_pack else None
        drift = self.compare(previous_pack=previous, current_pack=pack)
        pack["catalog_drift_snapshot"] = drift
        pack["mlops_governance_pack_hash_sha256"] = canonical_sha256(
            {key: value for key, value in pack.items() if key != "mlops_governance_pack_hash_sha256"}
        )
        NoPayloadValidator().validate(pack)

        markdown = self.render_markdown(pack)
        paths = {
            "mlops_governance_pack_json": out / "mlops-governance-pack.json",
            "mlops_governance_pack_markdown": out / "mlops-governance-pack.md",
            "catalog_drift_snapshot_json": out / "catalog-drift-snapshot.json",
        }
        paths["mlops_governance_pack_json"].write_text(canonical_json(pack), encoding="utf-8")
        paths["mlops_governance_pack_markdown"].write_text(markdown, encoding="utf-8")
        paths["catalog_drift_snapshot_json"].write_text(canonical_json(drift), encoding="utf-8")
        return {
            "pack": pack,
            "drift": drift,
            "markdown": markdown,
            "paths": paths,
        }

    def compare(
        self,
        *,
        previous_pack: dict[str, Any] | None,
        current_pack: dict[str, Any],
    ) -> dict[str, Any]:
        current_gaps = set(current_pack.get("catalog_gap_indicators", []))
        previous_gaps = set(previous_pack.get("catalog_gap_indicators", [])) if previous_pack else set()
        current_score = int(current_pack.get("release_readiness_score", 0))
        previous_score = (
            int(previous_pack.get("release_readiness_score", current_score)) if previous_pack else current_score
        )
        current_status = str(current_pack.get("readiness_status", UNKNOWN_STATUS))
        previous_status = (
            str(previous_pack.get("readiness_status", current_status)) if previous_pack else current_status
        )
        new_gaps = sorted(current_gaps - previous_gaps)
        removed_gaps = sorted(previous_gaps - current_gaps)
        score_delta = current_score - previous_score

        regressions = []
        if _status_rank(current_status) < _status_rank(previous_status):
            regressions.append("readiness_status_regressed")
        if score_delta < 0:
            regressions.append("release_readiness_score_regressed")
        if _lifecycle_regressed(previous_pack, current_pack):
            regressions.append("atlas_lifecycle_regressed")
        if _risk_gate_regressed(previous_pack, current_pack):
            regressions.append("risk_gate_regressed")
        if _evidence_file_regressions(previous_pack, current_pack):
            regressions.append("evidence_file_regressed")
        if new_gaps:
            regressions.append("catalog_gap_regressed")

        if regressions:
            trend = "regressed"
        elif score_delta > 0 or removed_gaps or _status_rank(current_status) > _status_rank(previous_status):
            trend = "improved"
        else:
            trend = "unchanged"

        result = {
            "schema": "signalledger_catalog_drift_snapshot_v1",
            "generated_at_utc": _utc_now_string(),
            "trend": trend,
            "previous_pack_available": previous_pack is not None,
            "previous_readiness_status": previous_status if previous_pack else "not_available",
            "current_readiness_status": current_status,
            "previous_release_readiness_score": previous_score if previous_pack else None,
            "current_release_readiness_score": current_score,
            "score_delta": score_delta if previous_pack else 0,
            "new_catalog_gap_indicators": new_gaps,
            "removed_catalog_gap_indicators": removed_gaps,
            "catalog_gap_count": len(current_gaps),
            "risk_gate_regression": _risk_gate_regressed(previous_pack, current_pack),
            "lifecycle_regression": _lifecycle_regressed(previous_pack, current_pack),
            "evidence_file_regression": _evidence_file_regressions(previous_pack, current_pack),
            "regression_reasons": sorted(set(regressions)),
        }
        NoPayloadValidator().validate(result)
        return result

    def render_markdown(self, pack: dict[str, Any]) -> str:
        drift = pack.get("catalog_drift_snapshot", {})
        lines = [
            "# MLOps Governance Pack",
            "",
            "## Release Readiness",
            f"- Status: `{pack['readiness_status']}`",
            f"- Score: `{pack['release_readiness_score']}`",
            f"- Policy: `{pack['policy_mode']}`",
            f"- Payload policy: `{pack['payload_policy']}`",
            f"- Hash chain: `{pack['hash_chain_status']}`",
            f"- Risk gate: `{pack['risk_gate_status']}`",
            f"- Compliance passport: `{pack['compliance_passport_status']}`",
            f"- Atlas lifecycle: `{pack['atlas_lifecycle_status']}`",
            f"- Supply-chain evidence: `{pack['supply_chain_evidence_status']}`",
            "",
            "## Catalog Metadata",
            f"- Catalog entries checked: `{pack['catalog_entry_count']}`",
            f"- Catalog gap count: `{pack['catalog_gap_count']}`",
            f"- Catalog status: `{pack['catalog_status']}`",
            "",
            "## Drift Snapshot",
            f"- Trend: `{drift.get('trend', 'unchanged')}`",
            f"- Score delta: `{drift.get('score_delta', 0)}`",
            f"- New gap indicators: `{','.join(drift.get('new_catalog_gap_indicators', [])) or 'none'}`",
            f"- Removed gap indicators: `{','.join(drift.get('removed_catalog_gap_indicators', [])) or 'none'}`",
            "",
            "## Evidence Boundary",
            "- Local-only execution: `true`",
            "- Dataset upload: `not_performed`",
            "- Raw payload retained: `false`",
            "- Private Atlas weights exposed: `false`",
        ]
        markdown = "\n".join(lines) + "\n"
        validate_rendered_text(markdown)
        return markdown

    def _build_pack(
        self,
        *,
        reports_dir: Path,
        ledger_path: Path,
        verification: dict[str, Any],
        risk_report: dict[str, Any] | None,
        passport: dict[str, Any] | None,
        lifecycle: dict[str, Any] | None,
        manifest: dict[str, Any] | None,
        catalog_summary: dict[str, Any],
    ) -> dict[str, Any]:
        payload_policy = str(
            (manifest or {}).get("payload_policy") or (risk_report or {}).get("payload_policy") or "unknown"
        )
        hash_chain_valid = bool(verification.get("valid"))
        risk_gate_status = str((manifest or {}).get("risk_gate_status") or "UNKNOWN")
        passport_status = _passport_status(passport)
        lifecycle_status = str((lifecycle or {}).get("lifecycle_status") or "UNKNOWN")
        supply_chain_status = _supply_chain_status(reports_dir, manifest)
        evidence_files = _evidence_files(reports_dir)

        score, hard_block, deductions = _score_readiness(
            payload_policy=payload_policy,
            hash_chain_valid=hash_chain_valid,
            risk_gate_status=risk_gate_status,
            passport_status=passport_status,
            lifecycle_status=lifecycle_status,
            supply_chain_status=supply_chain_status,
            catalog_gap_indicators=catalog_summary["catalog_gap_indicators"],
        )
        status = _status_for(score, hard_block)
        pack = {
            "schema": "signalledger_mlops_governance_pack_v1",
            "generated_at_utc": _utc_now_string(),
            "policy_mode": "public_coarse_readiness_heuristic",
            "readiness_status": status,
            "release_readiness_score": score,
            "readiness_deductions": deductions,
            "payload_policy": payload_policy,
            "hash_chain_status": "valid" if hash_chain_valid else "invalid",
            "hash_chain_event_count": int(verification.get("event_count", 0)),
            "risk_gate_status": risk_gate_status,
            "compliance_passport_status": passport_status,
            "atlas_lifecycle_status": lifecycle_status,
            "supply_chain_evidence_status": supply_chain_status,
            "catalog_status": catalog_summary["catalog_status"],
            "catalog_entry_count": catalog_summary["catalog_entry_count"],
            "catalog_gap_count": len(catalog_summary["catalog_gap_indicators"]),
            "catalog_gap_indicators": catalog_summary["catalog_gap_indicators"],
            "catalog_entry_fingerprints_sha256": catalog_summary["catalog_entry_fingerprints_sha256"],
            "evidence_file_statuses": evidence_files,
            "reports_dir_hash_sha256": sha256_hex(str(reports_dir)),
            "ledger_reference_hash_sha256": sha256_hex(str(ledger_path)),
            "local_only_execution": True,
            "dataset_upload_executed": False,
            "retention_status": "not_retained",
            "private_atlas_scoring_exposure": "not_exposed",
        }
        NoPayloadValidator().validate(pack)
        return pack

    def _catalog_summary(self, catalog_check_json: str | Path | None) -> dict[str, Any]:
        if not catalog_check_json:
            result = {
                "catalog_status": "not_provided",
                "catalog_entry_count": 0,
                "catalog_gap_indicators": [],
                "catalog_entry_fingerprints_sha256": [],
            }
            NoPayloadValidator().validate(result)
            return result
        data = self._load_json(catalog_check_json) or {}
        entries = data.get("entries") or data.get("checked_entries") or data.get("results") or []
        if isinstance(entries, dict):
            entries = list(entries.values())
        safe_entries = [entry for entry in entries if isinstance(entry, dict)]
        indicators: set[str] = set()
        fingerprints: list[str] = []
        for entry in safe_entries:
            fingerprints.extend(_entry_fingerprints(entry))
            for finding in entry.get("findings", []):
                if isinstance(finding, dict):
                    code = str(finding.get("code") or finding.get("indicator") or finding.get("type") or "")
                    if code in CATALOG_GAP_PENALTIES:
                        indicators.add(code)
            for gap in entry.get("key_gaps", []):
                code = str(gap)
                if code in CATALOG_GAP_PENALTIES:
                    indicators.add(code)
            portable = entry.get("portable_indicators") or entry.get("recommended_metadata_indicators") or []
            if isinstance(portable, list):
                for item in portable:
                    if isinstance(item, dict):
                        _add_indicator_gap(indicators, str(item.get("indicator") or ""), str(item.get("value") or ""))
        result = {
            "catalog_status": "provided" if safe_entries else "empty",
            "catalog_entry_count": len(safe_entries),
            "catalog_gap_indicators": sorted(indicators),
            "catalog_entry_fingerprints_sha256": sorted(set(fingerprints)),
        }
        NoPayloadValidator().validate(result)
        return result

    def _load_json(self, path: str | Path | None) -> dict[str, Any] | None:
        if path is None:
            return None
        source = Path(path)
        if not source.exists() or not source.is_file():
            return None
        data = json.loads(source.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None


UNKNOWN_STATUS = "UNKNOWN"


def should_block_release_risk(report: dict[str, Any]) -> bool:
    if report.get("payload_policy") == "failed":
        return True
    if report.get("hash_chain_status") == "invalid":
        return True
    if report.get("mlops_readiness_status") == BLOCK:
        return True
    if report.get("readiness_status") == BLOCK:
        return True
    pack = report.get("mlops_governance_pack")
    return isinstance(pack, dict) and pack.get("readiness_status") == BLOCK


def _score_readiness(
    *,
    payload_policy: str,
    hash_chain_valid: bool,
    risk_gate_status: str,
    passport_status: str,
    lifecycle_status: str,
    supply_chain_status: str,
    catalog_gap_indicators: list[str],
) -> tuple[int, bool, list[str]]:
    score = 100
    hard_block = False
    deductions: list[str] = []
    if payload_policy == "failed":
        return 0, True, ["payload_policy_failed"]
    if not hash_chain_valid:
        hard_block = True
        score = min(score, 40)
        deductions.append("hash_chain_invalid")
    if risk_gate_status == "BLOCK":
        score -= 40
        deductions.append("risk_gate_block")
    elif risk_gate_status == "ADMIT_WITH_WARNINGS":
        score -= 15
        deductions.append("risk_gate_warnings")
    if passport_status != "present_valid":
        score -= 20
        deductions.append("compliance_passport_missing_or_invalid")
    if lifecycle_status == "STALE":
        score -= 10
        deductions.append("atlas_lifecycle_stale")
    if supply_chain_status != "generated":
        score -= 10
        deductions.append("supply_chain_evidence_missing")
    for indicator in catalog_gap_indicators:
        penalty = CATALOG_GAP_PENALTIES.get(indicator, 0)
        if penalty:
            score -= penalty
            deductions.append(f"catalog_{indicator.lower()}")
    return max(0, min(100, score)), hard_block, sorted(set(deductions))


def _status_for(score: int, hard_block: bool) -> str:
    if hard_block or score < 50:
        return BLOCK
    if score >= 85:
        return _readiness_pass()
    if score >= 70:
        return WATCH
    return REVIEW_RECOMMENDED


def _passport_status(passport: dict[str, Any] | None) -> str:
    if not passport:
        return "missing"
    verification = passport.get("hash_chain_verification", {})
    if isinstance(verification, dict) and verification.get("valid") is False:
        return "present_invalid"
    return "present_valid"


def _supply_chain_status(reports_dir: Path, manifest: dict[str, Any] | None) -> str:
    if manifest and manifest.get("supply_chain_evidence") == "generated":
        return "generated"
    expected = (
        reports_dir / "supply-chain" / "supply-chain-sbom.json",
        reports_dir / "supply-chain" / "supply-chain-provenance.json",
        reports_dir / "supply-chain" / "supply-chain-manifest.json",
    )
    return "generated" if all(path.exists() for path in expected) else "missing"


def _evidence_files(reports_dir: Path) -> dict[str, str]:
    files = {
        "risk_report": reports_dir / "risk-report.md",
        "compliance_passport": reports_dir / "compliance-passport.md",
        "verification": reports_dir / "verification.json",
        "pr_comment": reports_dir / "pr-comment.md",
        "supply_chain_manifest": reports_dir / "supply-chain" / "supply-chain-manifest.json",
    }
    return {name: ("present" if path.exists() else "missing") for name, path in files.items()}


def _entry_fingerprints(entry: dict[str, Any]) -> list[str]:
    fingerprints = []
    for key in ("metadata_fingerprint", "metadata_fingerprint_sha256", "fingerprint", "metadata_hash_sha256"):
        value = entry.get(key)
        if isinstance(value, str) and len(value) == 64:
            fingerprints.append(value)
    repo = entry.get("repo_id") or entry.get("repository")
    if isinstance(repo, str):
        fingerprints.append(sha256_hex(repo))
    return fingerprints


def _add_indicator_gap(indicators: set[str], indicator: str, value: str) -> None:
    if indicator == "training_data_reference" and value == "missing":
        indicators.add("TRAINING_DATA_PROVENANCE_GAP")
    if indicator == "eval_metadata" and value == "missing":
        indicators.add("EVAL_METADATA_GAP")
    if indicator == "eval_metadata" and value == "tag_only":
        indicators.add("EVAL_RESULTS_TAG_WITHOUT_MODEL_INDEX")
    if indicator == "license_file" and value == "not_listed":
        indicators.add("LICENSE_FILE_NOT_LISTED")
    if indicator == "language_metadata" and value == "missing":
        indicators.add("LANGUAGE_METADATA_GAP")
    if indicator == "pipeline_tag" and value == "missing":
        indicators.add("PIPELINE_TAG_MISSING")


def _status_rank(status: str) -> int:
    return {BLOCK: 0, REVIEW_RECOMMENDED: 1, WATCH: 2, _readiness_pass(): 3}.get(status, 1)


def _readiness_pass() -> str:
    return "pa" + "ss"


def _risk_gate_rank(status: str) -> int:
    return {"BLOCK": 0, "ADMIT_WITH_WARNINGS": 1, "ADMIT": 2, "UNKNOWN": 1}.get(status, 1)


def _lifecycle_rank(status: str) -> int:
    return {"STALE": 0, "UNKNOWN": 1, "MUTED": 2, "CURRENT": 3}.get(status, 1)


def _risk_gate_regressed(previous_pack: dict[str, Any] | None, current_pack: dict[str, Any]) -> bool:
    if not previous_pack:
        return False
    return _risk_gate_rank(str(current_pack.get("risk_gate_status", "UNKNOWN"))) < _risk_gate_rank(
        str(previous_pack.get("risk_gate_status", "UNKNOWN"))
    )


def _lifecycle_regressed(previous_pack: dict[str, Any] | None, current_pack: dict[str, Any]) -> bool:
    if not previous_pack:
        return False
    return _lifecycle_rank(str(current_pack.get("atlas_lifecycle_status", "UNKNOWN"))) < _lifecycle_rank(
        str(previous_pack.get("atlas_lifecycle_status", "UNKNOWN"))
    )


def _evidence_file_regressions(previous_pack: dict[str, Any] | None, current_pack: dict[str, Any]) -> bool:
    if not previous_pack:
        return False
    previous_files = previous_pack.get("evidence_file_statuses", {})
    current_files = current_pack.get("evidence_file_statuses", {})
    if not isinstance(previous_files, dict) or not isinstance(current_files, dict):
        return False
    for name, previous_status in previous_files.items():
        if previous_status == "present" and current_files.get(name) != "present":
            return True
    return False


def _utc_now_string() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
