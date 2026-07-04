from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ecl_trainer.ci.reporting import CIReportRenderer
from ecl_trainer.ci.scanner import CIScanner
from ecl_trainer.core.exceptions import PayloadExfiltrationException
from ecl_trainer.core.policy import NoPayloadValidator
from ecl_trainer.mlops_pack import should_block_release_risk


class GitHubActionRunner:
    def run(
        self,
        *,
        project_namespace: str,
        ledger_path: str,
        changed_only: bool = True,
        risk_policy: str = "report_only",
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
        markdown = CIReportRenderer().render_markdown(report)
        summary_path = os.getenv("GITHUB_STEP_SUMMARY")
        if summary_path:
            Path(summary_path).write_text(markdown, encoding="utf-8")
        report["risk_policy"] = risk_policy
        report["should_fail"] = self.should_fail(report, risk_policy)
        return report

    def should_fail(self, report: dict[str, Any], risk_policy: str) -> bool:
        if risk_policy == "block_on_payload_violation":
            return report.get("payload_policy") == "failed"
        if risk_policy == "block_on_high_risk":
            return report.get("risk_summary", {}).get("status") == "high_risk"
        if risk_policy == "block_on_release_risk":
            return should_block_release_risk(report)
        return False
