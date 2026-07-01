# Sample ECL Records

This directory shows a minimal metadata-only ECL Trainer ledger at `sample-events.jsonl`.
It also includes a deterministic Financial Services Atlas seed verification fixture at
`financial-services-atlas-seed-ledger.sample.json`.

The public sample contains one append-only `ci_scan` record. It demonstrates:

- canonical JSONL shape
- hash-chain fields
- No-Payload Policy assertions
- local-only CI scan metadata

The sample intentionally contains no raw dataset rows, prompts, completions, raw diffs, token sequences, embeddings, model weights, notebook cells, secrets, or local paths.

Verify the sample hash chain:

```bash
ecl-trainer verify-log --ledger-path examples/ecl_records/sample-events.jsonl
```

Generate a local compliance passport from it:

```bash
ecl-trainer passport --project-namespace example/project --ledger-path examples/ecl_records/sample-events.jsonl
```

Full training/evaluation record chains are reserved for private pilot and evaluator packets.

The Financial Services Atlas fixture demonstrates four sequentially linked structural
seed records with statistical density bounds, financial regulatory tags, evaluation
delta trajectories, and pre-flight shield assertions. Each record is explicitly marked
`SYNTHETIC_ALPHA_SAMPLE_FOR_SCHEMA_VALIDATION_ONLY`; the values are illustrative test
fixtures, not production baseline coefficients. It contains no raw corpus text,
prompts, completions, token sequences, embeddings, model weights, raw diffs, or
dataset rows.
