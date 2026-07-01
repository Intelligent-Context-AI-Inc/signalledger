from __future__ import annotations

from typing import Any

from ecl_trainer.compliance.pr_comment import PullRequestCommentRenderer
from ecl_trainer.core.policy import NoPayloadValidator
from ecl_trainer.core.serialization import canonical_json


class CIReportRenderer:
    def render_markdown(self, report: dict[str, Any]) -> str:
        return PullRequestCommentRenderer().render(report)

    def render_json(self, report: dict[str, Any]) -> str:
        NoPayloadValidator().validate(report)
        return canonical_json(report)
