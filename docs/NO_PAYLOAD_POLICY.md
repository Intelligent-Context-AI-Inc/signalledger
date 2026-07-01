# No-Payload Policy

`ecl-trainer` is metadata-only. Raw data stays local. Every event, report, comment, card export, envelope, and transport path must pass `NoPayloadValidator` before serialization, append, render, signing, or submission.

## Never Captured

- raw text
- prompts
- completions
- messages
- dataset rows
- examples
- samples
- raw tokens or token IDs
- embeddings or vectors
- model weights
- checkpoint bytes
- notebook cells
- raw diffs
- raw local absolute paths
- secrets, API keys, access tokens, or credentials

## Allowed Metadata

- SHA-256 hashes
- schema fingerprints
- source-root references stripped to root or bucket level
- source-root hashes
- token count estimates
- aggregate metadata
- controlled semantic tags
- provenance descriptors
- license descriptors
- mutation trails
- checkpoint IDs
- evaluation metric deltas
- risk flags
- event IDs
- signed metadata envelopes

## Enforcement

The SDK fails closed with `PayloadExfiltrationException` when forbidden material appears in model construction, canonical serialization, ledger append, hash-chain writes, envelope signing, SaaS transport, CI reports, PR/MR comments, compliance reports, CLI output, or Hugging Face card exports.
