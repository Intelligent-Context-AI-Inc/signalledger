# Interactive First-Run Demo Repo

## Purpose

The demo repo is the fastest way for an engineer to believe the product. It should show one safe PR, one blocked metadata PR, and the exact ECL artifacts generated locally.

## Demo Shape

- `safe-manifest.json`: metadata-only, passes the No-Payload Policy.
- `bad-manifest.payload-demo.json`: deliberately unsafe key, fails closed.
- `expected-pr-comment.md`: what reviewers should see after the first successful scan.
- `README.md`: 10-minute walkthrough.

The demo must not contain raw dataset rows, prompts, completions, embeddings, token sequences, model weights, raw diffs, or private Atlas rows.

## Recommended Flow

1. Open a PR that adds the safe manifest.
2. ECL posts a `report_only` PR comment and uploads local artifacts.
3. Open a second PR that adds the unsafe manifest.
4. ECL raises `PayloadExfiltrationException` and prevents a ledger append.
5. Review `verification.json` from the safe PR and confirm the hash chain is valid.

## Files

Seed files live in `examples/interactive_demo_repo/`.

## Landing-Page Clip

"We opened a PR with only metadata. ECL generated a risk report, compliance passport, PR comment, verification file, and append-only ledger without a SaaS account. Then we opened a second PR with a payload-like metadata field; ECL failed closed before writing to the ledger."
