# ECL Learning Ledger Security One-Pager

## What It Is

ECL Learning Ledger is a local-first, metadata-only training-data governance layer for LLM teams.

## What It Does Not Do

- Does not upload datasets.
- Does not require a SaaS account.
- Does not inspect raw dataset rows.
- Does not execute repository code in the CI scan path.
- Does not store prompts, completions, token sequences, embeddings, model weights, raw diffs, or secrets.

## What It Produces

- Risk report.
- Compliance passport.
- Hash-chain verification file.
- PR comment body.
- Append-only JSONL ledger.
- Supply-chain evidence.

## Core Controls

- `NoPayloadValidator` before append, render, serialize, or submit.
- Append-only hash-chain ledger.
- Dockerized static CI scan.
- Local Atlas query with aggregate outputs only.
- Optional SaaS submission disabled by default.

## Security Review Ask

Approve a `report_only` pilot first. Move to `block_on_payload_violation` after the first clean pass and manifest review.
