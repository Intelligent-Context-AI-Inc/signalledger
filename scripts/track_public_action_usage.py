from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime


QUERIES = {
    "released_action_reference": "Intelligent-Context-AI-Inc/signalledger/.github/actions/ecl-trainer-scan",
    "released_action_tag_alpha4": "ecl-trainer-scan@v0.1.0-alpha.4",
    "local_action_path": "./.github/actions/ecl-trainer-scan",
}


def search_public_references(query: str) -> dict[str, object]:
    result = subprocess.run(
        ["gh", "search", "code", query, "--limit", "100", "--json", "repository,path"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {
            "status": "error",
            "query": query,
            "error": result.stderr.strip() or result.stdout.strip(),
        }
    payload = json.loads(result.stdout or "[]")
    public_matches = [item for item in payload if not item.get("repository", {}).get("isPrivate")]
    public_repositories = sorted({item["repository"]["nameWithOwner"] for item in public_matches})
    return {
        "status": "ok",
        "query": query,
        "result_limit": 100,
        "public_match_sample_count": len(public_matches),
        "public_repository_sample_count": len(public_repositories),
        "public_repositories": public_repositories,
    }


def main() -> None:
    snapshot = {
        "schema": "signalledger_public_action_usage_search_v1",
        "captured_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source": "gh_search_code",
        "visibility": "public_only",
        "note": "Authenticated gh search may return private matches; this snapshot filters them out.",
        "queries": {name: search_public_references(query) for name, query in QUERIES.items()},
    }
    print(json.dumps(snapshot, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
