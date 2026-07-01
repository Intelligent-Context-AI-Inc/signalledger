from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx

from ecl_trainer.ci.artifacts import PR_COMMENT_MARKER
from ecl_trainer.core.policy import validate_rendered_text


class GitHubPRCommentPoster:
    def post(self, *, comment_path: str | Path, marker: str = PR_COMMENT_MARKER) -> dict[str, Any]:
        token = os.getenv("GITHUB_TOKEN")
        repository = os.getenv("GITHUB_REPOSITORY")
        event_path = os.getenv("GITHUB_EVENT_PATH")
        api_url = os.getenv("GITHUB_API_URL", "https://api.github.com").rstrip("/")
        if not token or not repository or not event_path:
            return {"posted": False, "reason": "missing_github_context"}

        event = json.loads(Path(event_path).read_text(encoding="utf-8"))
        pull_request = event.get("pull_request") or {}
        issue_number = pull_request.get("number") or event.get("number")
        if not issue_number:
            return {"posted": False, "reason": "not_pull_request"}

        body = Path(comment_path).read_text(encoding="utf-8")
        validate_rendered_text(body)

        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        comments_url = f"{api_url}/repos/{repository}/issues/{issue_number}/comments"
        with httpx.Client(headers=headers, timeout=20.0) as client:
            response = client.get(comments_url, params={"per_page": 100})
            response.raise_for_status()
            existing = next(
                (comment for comment in response.json() if marker in str(comment.get("body", ""))),
                None,
            )
            if existing:
                update = client.patch(str(existing["url"]), json={"body": body})
                update.raise_for_status()
                return {"posted": True, "operation": "updated"}
            created = client.post(comments_url, json={"body": body})
            created.raise_for_status()
            return {"posted": True, "operation": "created"}
