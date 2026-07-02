# Successful GitHub Action Run

This folder captures a real successful GitHub-hosted run of the SignalLedger action from an end-user-style pull request.

## Run Summary

- Action version: `v0.1.0-alpha.3`
- Workflow: `workflow.yml`
- Input manifest: `input-manifest.json`
- GitHub run: `28607801331`
- Result: `success`
- Mode: local-only
- SaaS account: not required
- Dataset upload: not performed
- Payload policy: passed
- Ledger verification: valid
- Atlas source records: 125

The original smoke repository was private, so this folder stores the generated artifacts directly for public inspection.

## What To Inspect

| File | What it proves |
| --- | --- |
| `artifacts/events.jsonl` | Append-only metadata ledger with hash-chained events. |
| `artifacts/reports/pr-comment.md` | The PR comment body posted by the Action. |
| `artifacts/reports/risk-report.md` | Reviewer-facing risk summary. |
| `artifacts/reports/compliance-passport.md` | Local compliance-support passport. |
| `artifacts/reports/verification.json` | Hash-chain verification result. |
| `artifacts/reports/diff-free-pr-proof.json` | Evidence that raw diffs were not captured. |
| `artifacts/reports/manifest.json` | Local artifact manifest and policy outcome. |
| `artifacts/reports/supply-chain/` | Local supply-chain evidence generated with the run. |

## No-Payload Boundary

These artifacts are intentionally metadata-only. They contain hashes, IDs, policy assertions, risk summaries, local evidence, aggregate Atlas counts, and verification results. They do not contain raw dataset rows, prompts, completions, embeddings, token sequences, model weights, raw diffs, secrets, or uploaded datasets.

## Recreate The Shape

Use the workflow in `workflow.yml` and start with `risk_policy: report_only` for a first trial. Once the team trusts the no-payload gate, move toward `block_on_payload_violation`.
