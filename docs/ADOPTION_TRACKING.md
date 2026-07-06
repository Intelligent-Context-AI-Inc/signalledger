# Adoption Tracking

SignalLedger is local-first by default. The GitHub Action does not phone home
unless a repository owner explicitly enables an adoption ping.

## What We Can See

- Public GitHub code search references to the action.
- Public issues opened with the `Using SignalLedger` issue template.
- Repository traffic, stars, forks, clones, referrals, and docs engagement for
  this public repository.
- GHCR package download counts for published ECL Trainer images.
- Optional metadata-only usage pings from teams that set `report_usage: "true"`.

## What We Cannot See By Default

- Private repositories using the action.
- Exact run counts in external repositories.
- Private organization, dataset, model, prompt, embedding, token, checkpoint, or
  customer details.
- Failed experiments where a public workflow was added and removed before a
  search snapshot.
- Exact run counts when a runner uses the local-build fallback instead of a
  published GHCR image.

## Traffic Archive

GitHub repository traffic is only retained for a short rolling window. The
`Archive Adoption Signals` workflow runs weekly and writes snapshots under:

```text
docs/adoption_snapshots/
```

Each snapshot includes:

- clone totals and unique cloners;
- view totals and unique visitors;
- popular paths;
- popular referrers;
- public external workflow references found through code search.

Clone traffic is a directional signal. It may include human clones, bots,
internal smoke tests, package installs, and GitHub Action executions.

## GHCR Pull Counts

The action supports a published-image mode:

```yaml
with:
  image_mode: auto
  image_ref: ghcr.io/intelligent-context-ai-inc/signalledger-ecl-trainer:v0.1.0-alpha.4
```

Defaults:

- `image_mode`: `auto`
- `image_ref`: `ghcr.io/intelligent-context-ai-inc/signalledger-ecl-trainer:v0.1.0-alpha.4`

In `auto` mode, the action pulls the published GHCR image first. If that image
is unavailable, it falls back to building `Dockerfile.ecl-trainer` locally in
the runner. Set `image_mode: "published"` when a team wants to require the
published image.

GHCR package download counts are a stronger proxy for workflow runs than clone
traffic because each uncached workflow image pull increments package activity.
They are still a proxy: runner cache behavior, retries, and manual pulls can
make them differ from exact workflow-run counts.

## Public Used-By Signal

Adopters can open a `Using SignalLedger` issue from the GitHub issue templates.
The issue template asks for public, non-sensitive information only.

Suggested public wording:

```text
We use SignalLedger in report_only mode to review metadata-only training-data
changes before GPU spend.
```

## Optional Usage Ping

The GitHub Action supports an explicit opt-in adoption ping:

```yaml
with:
  report_usage: "true"
  usage_ping_url: ${{ secrets.SIGNALLEDGER_USAGE_PING_URL }}
  include_repository_name_in_usage: "false"
```

Defaults:

- `report_usage`: `false`
- `usage_ping_url`: empty
- `include_repository_name_in_usage`: `false`

When `report_usage` is enabled, the action writes
`.ecl-trainer/reports/usage-ping.json` into the local artifact bundle. It sends
that JSON only when `usage_ping_url` is also provided.

The usage ping includes metadata such as action ref, repository visibility,
event name, runner OS, risk policy, domain-selection mode, payload-policy result,
and risk-gate status. It does not include raw paths, raw diffs, datasets,
prompts, completions, embeddings, token sequences, model weights, secrets, or
customer data. Repository name is excluded unless the adopter sets
`include_repository_name_in_usage: "true"`.

## Public Workflow Reference Snapshot

Run this from the public repository to sample visible external workflow
references and repository traffic:

```bash
python3 scripts/track_public_action_usage.py
```

The script uses `gh search code`, filters out private matches that may be visible
to the authenticated user, excludes this repository from external adopter
counts, and reports public repository samples for released workflow references.
It cannot see private repositories that the authenticated account cannot access,
and GitHub code search should be treated as a directional adoption signal rather
than an exact usage count.

## Recommended Dashboard Inputs

Track these separately:

- GitHub code-search snapshots.
- Archived traffic snapshots in `docs/adoption_snapshots/`.
- GHCR package download counts by image tag.
- `Using SignalLedger` issues.
- Stars, forks, clones, referrers, and docs page traffic.
- Optional usage-ping counts.
- Outreach conversations and pilots.

This keeps adoption tracking honest: public signals are observable, private
usage remains private unless the adopter opts in.
