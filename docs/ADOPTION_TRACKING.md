# Adoption Tracking

SignalLedger is local-first by default. The GitHub Action does not phone home
unless a repository owner explicitly enables an adoption ping.

## What We Can See

- Public GitHub code search references to the action.
- Public issues opened with the `Using SignalLedger` issue template.
- Repository traffic, stars, forks, clones, referrals, and docs engagement for
  this public repository.
- Optional metadata-only usage pings from teams that set `report_usage: "true"`.

## What We Cannot See By Default

- Private repositories using the action.
- Exact run counts in external repositories.
- Private organization, dataset, model, prompt, embedding, token, checkpoint, or
  customer details.
- Failed experiments where a public workflow was added and removed before a
  search snapshot.

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

## Public Code Search Snapshot

Run this from the public repository to sample visible workflow references:

```bash
python3 scripts/track_public_action_usage.py
```

The script uses `gh search code`, filters out private matches that may be visible
to the authenticated user, and reports public repository samples for the released
action reference and local action path. It cannot see private repositories that
the authenticated account cannot access, and GitHub code search should be treated
as a directional adoption signal rather than an exact usage count.

## Recommended Dashboard Inputs

Track these separately:

- GitHub code-search snapshots.
- `Using SignalLedger` issues.
- Stars, forks, clones, referrers, and docs page traffic.
- Optional usage-ping counts.
- Outreach conversations and pilots.

This keeps adoption tracking honest: public signals are observable, private
usage remains private unless the adopter opts in.
