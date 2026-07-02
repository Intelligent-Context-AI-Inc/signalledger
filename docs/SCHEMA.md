# ECL Trainer Schema

Schema version: `1.0`

All ledger records are immutable Pydantic models with unknown fields forbidden. Event IDs are UUIDs, timestamps are timezone-aware UTC, and hash fields ending in `_hash_sha256` must be SHA-256 hex.

## DataIngestEvent

Records metadata for a dataset or source reference: source-root URI, source-root hash, content fingerprint, schema hash, chunk-manifest hash, token count estimates, semantic tags, provenance descriptors, license descriptors, mutation trail, payload policy assertion, previous event hash, event hash, and optional signature.

## TrainingCheckpointEvent

Records checkpoint metadata only: project namespace, training run ID, checkpoint ID, exposed dataset hash, checkpoint reference hash, payload policy assertion, previous event hash, event hash, and optional signature. Checkpoint bytes and model weights are forbidden.

## EvalOutcomeEvent

Records evaluation deltas only: checkpoint ID, exposed dataset hashes, metric deltas, priority vector, scalar delta, old and new value multipliers, payload policy assertion, previous event hash, event hash, and optional signature. Evaluation examples are forbidden.

## CIScanEvent

Records CI scan metadata: repository-root hash, CI provider, CI run ID, commit hash, hashed PR/MR identifiers, changed path hashes, risk summary, report hash, payload policy assertion, previous event hash, event hash, and optional signature. Raw path names are not stored by default.

## SignedLedgerEnvelope

Wraps validated metadata for explicit transport: schema version, event type, event ID, tenant ID hash, project namespace, creation time, payload hash, validated payload, previous event hash, signature, SDK version, and payload policy assertion.

## PayloadPolicyAssertion

Records the enforcement state for the No-Payload Policy, including policy name, policy version, validator version, absence flags for raw payloads, model weights, token sequences, embeddings, and validation timestamp.

## Hash Chain

The local ledger writes canonical JSONL in append mode. Each event hash is computed from deterministic canonical JSON after setting `event_hash_sha256` empty and `signature` null for hashing. Every event links to the previous event hash. Verification detects modification, deletion, insertion, and reordering.

## Atlas Lifecycle Report

Records local Atlas freshness metadata only: atlas version tag, UTC compiled timestamp, active age in days, lifecycle status, domain enforcement messages, Atlas metadata digest hash, and payload policy status. The report is non-blocking by default and never performs network freshness checks.

## Offline Patch Report

Records explicit air-gapped Atlas patch application metadata: patch ID, patch manifest hash, Ed25519 publisher key ID, new Atlas version tag, verified compile timestamp, Atlas metadata digest hash, member hashes, operation count, record count, domain-status update count, and payload policy status. Patch application fails closed unless the publisher signature verifies against a locally configured trusted public key. Patch reports do not include archive paths, SQL, raw source rows, raw documents, prompts, embeddings, token sequences, model weights, or raw diffs.

## Corrections And Supersession

Prior events are never updated or deleted. Corrections or supersessions must be appended as later events that reference earlier event IDs or hashes.

## Forbidden Fields

Raw text, prompts, completions, messages, rows, examples, samples, token IDs, embeddings, vectors, weights, checkpoint bytes, notebook cells, raw diffs, file contents, and secrets are forbidden at every schema boundary.
