# SignalLedger / ECL Trainer

SignalLedger is a local CI safety layer for LLM training-data changes.

It scans training-data and model-metadata PRs before GPU spend, blocks raw-payload leakage, compares metadata against a structural Atlas, and writes PR-ready risk, compliance, and hash-chain evidence.

This repository contains the source-available alpha of `ecl-trainer`, the Python CLI/SDK and GitHub Action behind the local pre-flight workflow.

## What It Produces

A run writes local artifacts only:

- `.ecl-trainer/events.jsonl`: append-only metadata ledger.
- `.ecl-trainer/reports/risk-report.md`: training-data risk summary.
- `.ecl-trainer/reports/compliance-passport.md`: compliance-support evidence.
- `.ecl-trainer/reports/verification.json`: hash-chain verification.
- `.ecl-trainer/reports/pr-comment.md`: PR-ready reviewer summary.

No SaaS account is required for the default workflow.

## No-Payload Boundary

ECL Trainer is designed to reject raw payloads before append, render, serialize, or transport.

It must not capture or upload:

- raw datasets
- prompts or completions
- token sequences
- embeddings or vectors
- model weights
- raw diffs
- notebook cells
- secrets

Allowed artifacts are metadata-only: hashes, IDs, schema fingerprints, source-root descriptors, license/provenance labels, policy results, risk flags, and aggregate metrics.

## GitHub Action Quickstart

Create `.github/workflows/ecl-trainer.yml`:

```yaml
name: ECL Trainer

on:
  pull_request:
  workflow_dispatch:

permissions:
  contents: read
  pull-requests: write
  issues: write

jobs:
  ecl-trainer:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5
        with:
          fetch-depth: 2
      - uses: Intelligent-Context-AI-Inc/signalledger/.github/actions/ecl-trainer-scan@v0.1.0-alpha.3
        with:
          project_namespace: ${{ github.repository }}
          ledger_path: .ecl-trainer/events.jsonl
          risk_policy: report_only
          changed_only: 'true'
          post_pr_comment: 'true'
          upload_artifact: 'true'
          domain_selection_mode: auto
          enabled_domains: ''
```

Recommended rollout:

1. Start with `risk_policy: report_only`.
2. Move to `risk_policy: warn` after the first few PRs.
3. Use `block_on_payload_violation` when the team trusts the no-payload gate.

## Local CLI Quickstart

Install from this repository tag:

```bash
python3 -m pip install "ecl-trainer @ git+https://github.com/Intelligent-Context-AI-Inc/signalledger.git@v0.1.0-alpha.3"
```

Run local checks:

```bash
ecl-trainer scan --changed-only
ecl-trainer verify-log --ledger-path .ecl-trainer/events.jsonl
ecl-trainer passport --ledger-path .ecl-trainer/events.jsonl
ecl-trainer render-pr-comment --ledger-path .ecl-trainer/events.jsonl
```

First-run diagnostics:

```bash
ecl-trainer doctor github-action
ecl-trainer atlas-pack status
ecl-trainer artifact-viewer build
```

## Intelligent Context Atlas

The alpha includes a metadata-only public/synthetic Atlas surface:

- global structural core scaffolding
- top-20 domain registry
- Financial Services active starter pack
- Healthcare/Clinical source template
- public proof artifacts and no-payload red-team fixtures

Private Atlas seed content and proprietary scoring assets are not included in this public alpha.

## Proof Artifacts

See:

- `examples/proof_artifact_gallery/`
- `docs/ecl_learning_ledger/LANDING_PAGE_PROOF_KIT.md`
- `docs/ecl_learning_ledger/GITHUB_ACTION_FIRST_RUN_UX.md`
- `docs/security/ecl_learning_ledger/ENTERPRISE_SECURITY_REVIEW_PACKET.md`

## Development Gate

```bash
python3 -m pytest -q
ruff check ecl_trainer atlas_pipeline tests verify_ecl_compliance.py
mypy ecl_trainer atlas_pipeline
pyright ecl_trainer atlas_pipeline
bandit -r ecl_trainer atlas_pipeline verify_ecl_compliance.py
pip-audit . --skip-editable
python3 -m build
docker build -f Dockerfile.ecl-trainer -t ecl-trainer:public-alpha .
docker run --rm ecl-trainer:public-alpha --help
python3 verify_ecl_compliance.py
python3 -m ecl_trainer.cli red-team-corpus
```

## License

This alpha is source-available under the repository license. Do not treat this repository as open source unless and until an explicit open-source license is published.

For licensing or private Atlas pack access, contact Intelligent Context AI, Inc.
