# Successful GitHub Action Run

This folder captures the artifact bundle from a real successful GitHub-hosted run of the SignalLedger action on the public repository.

## Run Summary

- Source PR: `Intelligent-Context-AI-Inc/signalledger#1`
- GitHub run: `28630471629`
- Workflow: `workflow.yml`
- Input manifest: `input-manifest.json`
- Result: `success`
- Mode: local-only
- SaaS account: not required
- Dataset upload: not performed
- Payload policy: passed
- Ledger verification: valid
- Oracle status: completed
- Enabled domain: financial_services
- Risk gate: ADMIT_WITH_WARNINGS
- Atlas source records: 125

The Action uploaded these files as `ecl-trainer-local-report`. They are checked in here so visitors can inspect the proof even after GitHub artifact retention expires.

## What To Inspect

| File | What it proves |
| --- | --- |
| `artifacts/events.jsonl` | Append-only metadata ledger with hash-chained events. |
| `artifacts/reports/pr-comment.md` | The PR comment body posted by the Action. |
| `artifacts/reports/risk-report.md` | Reviewer-facing risk summary. |
| `artifacts/reports/compliance-passport.md` | Local compliance-support passport. |
| `artifacts/reports/verification.json` | Hash-chain verification result. |
| `artifacts/reports/diff-free-pr-proof.json` | Evidence that raw diffs were not captured. |
| `artifacts/reports/oracle-alerts.json` | Step-zero alert evidence from the local Atlas. |
| `artifacts/reports/oracle-blueprint.json` | Step-zero curriculum blueprint metadata. |
| `artifacts/reports/manifest.json` | Local artifact manifest and policy outcome. |
| `artifacts/reports/supply-chain/` | Local supply-chain evidence generated with the run. |

## No-Payload Boundary

These artifacts are intentionally metadata-only. They contain hashes, IDs, policy assertions, risk summaries, local evidence, aggregate Atlas counts, and verification results. They do not contain raw dataset rows, prompts, completions, embeddings, token sequences, model weights, raw diffs, secrets, or uploaded datasets.

## Recreate The Shape

Use the workflow in `workflow.yml` and start with `risk_policy: report_only` for a first trial. Once the team trusts the no-payload gate, move toward `block_on_payload_violation`.
