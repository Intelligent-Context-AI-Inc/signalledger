# GitHub Action First-Run UX

## Goal

An engineer should be able to add ECL to a repository in one PR and get a local training-data risk report automatically.

## Step 1: Add The Workflow

Copy this to `.github/workflows/ecl-trainer.yml`.

```yaml
name: ECL Trainer

on:
  pull_request:
    paths:
      - "configs/**"
      - "data/**"
      - "datasets/**"
      - "training/**"
      - "recipes/**"
      - "ecl-trainer.manifest.json"
      - ".github/workflows/ecl-trainer.yml"
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
      - uses: ./.github/actions/ecl-trainer-scan
        with:
          project_namespace: ${{ github.repository }}
          ledger_path: .ecl-trainer/events.jsonl
          risk_policy: report_only
          changed_only: "true"
          post_pr_comment: "true"
          upload_artifact: "true"
          domain_selection_mode: auto
          enabled_domains: ""
          fail_on_payload_violation: "true"
```

For external repositories consuming a released action, replace `./.github/actions/ecl-trainer-scan` with the published action reference.

## Step 2: Add A Metadata Manifest

Copy the sample from `examples/github_action/ecl-trainer.manifest.json`.

```json
{
  "project_namespace": "example-org/financial-model",
  "domain": "financial_services",
  "dataset_registry": [
    {
      "dataset_id": "fin_news_v2",
      "dataset_version": "2026Q1",
      "dataset_hash_sha256": "4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a",
      "schema_hash_sha256": "ef2d127de37b942baad06145e54b0c619a1f22327b2ebbcfbec78f5564afe39d4",
      "source_family": "public_financial_metadata",
      "license_descriptor": "public_reference_metadata",
      "token_count_estimate": 1200000000,
      "semantic_tags": ["sec_edgar_taxonomy", "finra_oversight", "frb_stress_scenario_2026"]
    }
  ],
  "training_profile": {
    "run_id_hash_sha256": "7902699be42c8a8e46fbbb4501726517e86b22c56a189f7625a6da49081b2451",
    "model_family": "decoder_lm",
    "training_stage": "pre_flight",
    "benchmark_aliases": ["mmlu_finance"],
    "lineage_ids": ["fin_compliance_v3"]
  },
  "payload_policy": {
    "raw_payload_absent": true,
    "no_dataset_rows": true,
    "no_prompts": true,
    "no_embeddings": true,
    "no_model_weights": true
  }
}
```

## Expected PR Comment

See `examples/github_action/expected-pr-comment.md` for a post-ready text sample.

The comment should show:

- Risk status and remediation steps.
- Local compliance passport summary.
- Ledger verification status.
- Atlas domains used or skipped.
- Local evidence that SaaS and dataset upload were not used.

## Common First-Run Failures

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `PayloadExfiltrationException` | A manifest contains payload-like keys such as raw previews, prompts, tokens, embeddings, or model weights | Replace the field with a hash, count, controlled tag, or source descriptor |
| No PR comment appears | Workflow permissions do not include `issues: write` or `pull-requests: write` | Add both permissions and rerun |
| Atlas domain skipped | `domain_selection_mode` is `auto` and no safe domain tag was found | Add `"domain": "financial_services"` or set `enabled_domains` |
| Action reports high risk in `report_only` | ECL found benchmark overlap, lineage loop, or structural risk | Keep `report_only`, review the checklist, then remediate metadata |
| Docker build cannot run | Runner does not allow Docker | Use a runner with Docker or run the CLI directly in a Python job |

## Suggested Policy Rollout

1. `report_only`: first two weeks. Build trust, collect false positives, show the PR comment.
2. `warn`: keep merges unblocked, but make risk visible to reviewers.
3. `block_on_payload_violation`: enforce the No-Payload Policy once manifests are clean.
4. `block_on_high_risk`: use for regulated projects after risk owners agree on threshold behavior.

## Success Criteria

- PR comment is posted.
- Artifact bundle contains `risk-report.md`, `compliance-passport.md`, `verification.json`, `pr-comment.md`, and `events.jsonl`.
- `verification.json` reports `"valid": true`.
- The manifest says `"mode": "local-only"` and `"payload_policy": "passed"`.
