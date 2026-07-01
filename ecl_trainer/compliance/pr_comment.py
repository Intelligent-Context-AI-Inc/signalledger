from __future__ import annotations

from typing import Any

from ecl_trainer.core.policy import NoPayloadValidator, validate_rendered_text


class PullRequestCommentRenderer:
    def render(self, report: dict[str, Any]) -> str:
        NoPayloadValidator().validate(report)
        risk_flags = report.get("risk_flags") or report.get("risk_summary", {}).get("risk_flags", [])
        hash_chain = report.get("hash_chain_verification", {"valid": True})
        status = report.get("status", "pass")
        lines = [
            "## ECL Pre-Flight Shield",
            f"- Scan status: `{status}`",
            "- No-payload policy: `passed`",
            f"- Risk flags: `{len(risk_flags)}`",
            f"- Hash chain: `{'valid' if hash_chain.get('valid', True) else 'invalid'}`",
            "- Mode: `local-only`",
            "",
            "### Remediation Checklist",
            "- Review missing license descriptors.",
            "- Review provenance descriptors.",
            "- Review benchmark and lineage risk flags.",
        ]
        markdown = "\n".join(lines) + "\n"
        validate_rendered_text(markdown)
        return markdown
