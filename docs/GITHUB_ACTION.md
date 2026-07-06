# GitHub Action

The ECL Trainer GitHub Action runs a Dockerized static, metadata-only scan in pull requests or manual workflows. It does not execute repository code, load datasets, print raw diffs, upload datasets, or require SaaS credentials.

## Quickstart

For a complete first-run path with a copy/paste workflow, sample manifest, expected PR comment, common failures, and policy rollout sequence, see `docs/ecl_learning_ledger/GITHUB_ACTION_FIRST_RUN_UX.md`.

Helpful first-run commands:

```bash
ecl-trainer doctor github-action
ecl-trainer artifact-viewer build
ecl-trainer trial-bundle
```

```yaml
permissions:
  contents: read
  pull-requests: write
  issues: write

steps:
  - uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5
  - uses: ./.github/actions/ecl-trainer-scan
    with:
      project_namespace: org/project
      ledger_path: .ecl/events.jsonl
      risk_policy: report_only
      changed_only: "true"
      post_pr_comment: "true"
      upload_artifact: "true"
      domain_selection_mode: auto
      enabled_domains: ""
      ignore_staleness: "false"
      generate_mlops_pack: "true"
      image_mode: auto
      report_usage: "false"
```

Enterprise runner note: the Dockerized scanner maps the GitHub workspace into the
container and applies bounded `safe.directory` handling for that workspace path. It
does not require host root privileges, Docker socket access, repository code
execution, dataset mounts, or broad filesystem access outside the checked-out
workspace.

## Permissions

Job summaries and local artifacts work with read-only repository permissions. Sticky PR comments require `issues: write` on pull request workflows because GitHub stores PR comments as issue comments.

## Risk Policies

- `report_only`: produce report without failing.
- `warn`: produce report and warnings without failing.
- `block_on_high_risk`: fail on high-risk metadata findings.
- `block_on_payload_violation`: fail on No-Payload Policy violation.
- `block_on_release_risk`: fail only when payload policy fails, hash-chain
  verification fails, or MLOps readiness is `block`.

## Intelligent Context Atlas Toggles

The GitHub Action runs the global structural core by default. Domain extensions are controlled through:

- `domain_selection_mode`: `auto`, `explicit`, or `core_only`.
- `enabled_domains`: comma-separated domain IDs such as `financial_services`.

`auto` is the default. It enables the global core and selects a domain from safe manifest metadata when available. If no manifest domain is found, the Action stays in `core_only` mode.

The Docker image bakes a local DuckDB Atlas from metadata-only public seed manifests during image build. The public alpha Atlas includes top-20 domain seed coverage; PR comments and artifacts expose aggregate seed counts, not source rows.

Set `ignore_staleness: "true"` for long-running training branches when operators need to mute non-blocking Atlas lifecycle warnings.

## Docker Image Mode

The action runs in Docker and supports three image modes:

- `image_mode: auto`: pull the published GHCR image first; if it is unavailable,
  build `Dockerfile.ecl-trainer` locally in the runner.
- `image_mode: published`: require the published GHCR image and fail if it
  cannot be pulled.
- `image_mode: local`: always build `Dockerfile.ecl-trainer` locally.

The default is `auto`:

```yaml
with:
  image_mode: auto
  image_ref: ghcr.io/intelligent-context-ai-inc/signalledger-ecl-trainer:v0.1.0-alpha.4
```

Published-image pulls provide a stronger usage signal through GHCR package
download counts. The local fallback preserves the no-SaaS, no-upload trust path
and keeps the public alpha usable before a new image tag has been published.

## Safe Fork Behavior

Forked PRs should run in static scan mode. Do not execute repository code or load datasets from untrusted PRs.

## Artifacts And Comments

The action writes a job summary, uploads metadata-only artifacts, and can post a sticky PR comment. The artifact bundle includes:

- `risk-report.md`
- `risk-report.json`
- `compliance-passport.md`
- `compliance-passport.json`
- `pr-comment.md`
- `verification.json`
- `lifecycle-report.json`
- `mlops-governance-pack.json`
- `mlops-governance-pack.md`
- `catalog-drift-snapshot.json`
- aggregate Intelligent Context Atlas source counts in `manifest.json` and the PR comment
- `supply-chain/supply-chain-sbom.json`
- `supply-chain/supply-chain-provenance.json`
- `supply-chain/supply-chain-manifest.json`
- `oracle-alerts.json` when an oracle manifest is present
- `oracle-blueprint.json` when an oracle manifest is present
- the local append-only ledger

Every rendered file is validated before it is written. Reports contain hashes and summaries, never raw diffs, dataset rows, prompts, token sequences, embeddings, or model weights.

## Adoption Tracking

The action is local-first and does not phone home by default.

Optional metadata-only adoption pings are available for teams that want support
or want to be counted in ecosystem usage:

```yaml
with:
  report_usage: "true"
  usage_ping_url: ${{ secrets.SIGNALLEDGER_USAGE_PING_URL }}
  include_repository_name_in_usage: "false"
```

When enabled, the action writes `usage-ping.json` into the local artifact bundle.
It sends that JSON only when `usage_ping_url` is set. Repository name is excluded
unless `include_repository_name_in_usage` is explicitly set to `"true"`.

See `docs/ADOPTION_TRACKING.md` for the public used-by signal, optional usage
ping schema, GHCR pull-count signal, and scheduled adoption snapshot workflow.
