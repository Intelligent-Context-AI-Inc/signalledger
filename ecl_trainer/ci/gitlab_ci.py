from __future__ import annotations

from pathlib import Path
from typing import Any

from ecl_trainer.ci.reporting import CIReportRenderer
from ecl_trainer.ci.scanner import CIScanner
from ecl_trainer.core.exceptions import PayloadExfiltrationException
from ecl_trainer.core.policy import NoPayloadValidator


class GitLabCIRunner:
    def run(
        self,
        *,
        project_namespace: str,
        ledger_path: str,
        changed_only: bool = True,
        risk_policy: str = "report_only",
        artifact_dir: str = "ecl-trainer-artifacts",
    ) -> dict[str, Any]:
        try:
            report = CIScanner(
                repository_root=".",
                ledger_path=ledger_path,
                project_namespace=project_namespace,
            ).scan(changed_only=changed_only)
        except PayloadExfiltrationException:
            report = {
                "status": "failed",
                "project_namespace": project_namespace,
                "metadata_file_count": 0,
                "changed_path_hashes": [],
                "payload_policy": "failed",
                "risk_summary": {"status": "high_risk", "risk_flags": []},
            }
            NoPayloadValidator().validate(report)
        renderer = CIReportRenderer()
        artifact_path = Path(artifact_dir)
        artifact_path.mkdir(parents=True, exist_ok=True)
        (artifact_path / "ecl-report.md").write_text(renderer.render_markdown(report), encoding="utf-8")
        (artifact_path / "ecl-report.json").write_text(renderer.render_json(report), encoding="utf-8")
        report["risk_policy"] = risk_policy
        report["should_fail"] = self.should_fail(report, risk_policy)
        return report

    def should_fail(self, report: dict[str, Any], risk_policy: str) -> bool:
        if risk_policy == "block_on_payload_violation":
            return report.get("payload_policy") == "failed"
        if risk_policy == "block_on_high_risk":
            return report.get("risk_summary", {}).get("status") == "high_risk"
        return False
