from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPOSITORY = "Intelligent-Context-AI-Inc/signalledger"
QUERIES = {
    "released_action_reference": (
        "Intelligent-Context-AI-Inc/signalledger/.github/actions/ecl-trainer-scan "
        "path:.github/workflows"
    ),
    "released_action_tag_alpha4": "ecl-trainer-scan@v0.1.0-alpha.4 path:.github/workflows",
    "local_action_path": "./.github/actions/ecl-trainer-scan path:.github/workflows",
}


def run_gh(args: list[str]) -> tuple[int, str, str]:
    gh_path = shutil.which("gh")
    if gh_path is None:
        return 127, "", "gh CLI not found"
    result = subprocess.run(  # noqa: S603 - args are assembled by this script, not shell text.
        [gh_path, *args],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def gh_json(args: list[str], fallback: Any) -> Any:
    returncode, stdout, stderr = run_gh(args)
    if returncode != 0:
        return {
            "status": "error",
            "error": (stderr.strip() or stdout.strip()),
            "args": args,
        }
    try:
        return json.loads(stdout or "null")
    except json.JSONDecodeError as exc:
        return {
            "status": "error",
            "error": f"invalid JSON from gh: {exc}",
            "args": args,
            "raw": stdout,
        }


def search_public_references(query: str) -> dict[str, object]:
    payload = gh_json(
        ["search", "code", query, "--limit", "100", "--json", "repository,path,url"],
        fallback=[],
    )
    if isinstance(payload, dict) and payload.get("status") == "error":
        return {"status": "error", "query": query, "error": payload["error"]}
    if not isinstance(payload, list):
        return {"status": "error", "query": query, "error": "unexpected search payload"}

    public_matches = [
        item
        for item in payload
        if not item.get("repository", {}).get("isPrivate")
        and item.get("repository", {}).get("nameWithOwner") != REPOSITORY
    ]
    public_repositories = sorted(
        {item["repository"]["nameWithOwner"] for item in public_matches if item.get("repository")}
    )
    return {
        "status": "ok",
        "query": query,
        "result_limit": 100,
        "public_external_match_sample_count": len(public_matches),
        "public_external_repository_sample_count": len(public_repositories),
        "public_external_repositories": public_repositories,
        "public_external_matches": [
            {
                "repository": item.get("repository", {}).get("nameWithOwner"),
                "path": item.get("path"),
                "url": item.get("url"),
            }
            for item in public_matches
        ],
    }


def traffic_snapshot() -> dict[str, object]:
    endpoints = {
        "clones": ["api", f"repos/{REPOSITORY}/traffic/clones"],
        "views": ["api", f"repos/{REPOSITORY}/traffic/views"],
        "popular_paths": ["api", f"repos/{REPOSITORY}/traffic/popular/paths"],
        "popular_referrers": ["api", f"repos/{REPOSITORY}/traffic/popular/referrers"],
    }
    return {name: gh_json(args, fallback={}) for name, args in endpoints.items()}


def build_snapshot() -> dict[str, object]:
    captured_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return {
        "schema": "signalledger_public_adoption_snapshot_v1",
        "captured_at_utc": captured_at,
        "repository": REPOSITORY,
        "source": "gh_api_and_search",
        "visibility": "public_and_repo_owner_traffic",
        "note": (
            "GitHub traffic is a directional interest signal and may include humans, bots, "
            "internal tests, package installs, and Action executions. Code search includes "
            "public external workflow references only."
        ),
        "traffic": traffic_snapshot(),
        "public_workflow_references": {
            name: search_public_references(query) for name, query in QUERIES.items()
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Capture public SignalLedger adoption and traffic signals."
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON output path. Parent directories are created.",
    )
    args = parser.parse_args()

    snapshot = build_snapshot()
    text = json.dumps(snapshot, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
