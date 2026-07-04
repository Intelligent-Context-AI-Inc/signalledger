# MLOps Governance Pack

The MLOps Governance Pack turns a normal SignalLedger run into a local,
buyer-readable release readiness artifact.

It does not add SaaS submission, dataset upload, raw payload inspection, private
Atlas scoring weights, or proprietary pack internals. It summarizes existing
metadata-only evidence from the local report bundle.

## Command

```bash
ecl-trainer mlops-pack build \
  --reports-dir .ecl-trainer/reports \
  --ledger-path .ecl-trainer/events.jsonl \
  --output-dir .ecl-trainer/reports
```

Optional drift comparison:

```bash
ecl-trainer mlops-pack build \
  --previous-pack previous/mlops-governance-pack.json
```

Optional public catalog import:

```bash
ecl-trainer mlops-pack build \
  --catalog-check-json docs/ecl_learning_ledger/huggingface_live_checks/hf_public_model_checks_2026-07-03.json
```

## Outputs

- `.ecl-trainer/reports/mlops-governance-pack.json`
- `.ecl-trainer/reports/mlops-governance-pack.md`
- `.ecl-trainer/reports/catalog-drift-snapshot.json`

The GitHub Action generates these files by default and includes the readiness
summary in the PR comment and job summary.

## Readiness Signal

The public readiness score is intentionally coarse. It starts at `100` and
applies only public-safe deductions:

- payload policy failure blocks release readiness;
- invalid hash-chain verification blocks release readiness;
- `BLOCK` or `ADMIT_WITH_WARNINGS` risk-gate results reduce readiness;
- missing or invalid compliance passport reduces readiness;
- stale Atlas lifecycle reduces readiness;
- missing supply-chain evidence reduces readiness;
- imported public catalog gaps reduce readiness.

Statuses:

- `pass`: score `85-100`
- `watch`: score `70-84`
- `review_recommended`: score `50-69`
- `block`: score below `50` or hard-block condition

## Drift Snapshot

When a previous pack is supplied, SignalLedger compares:

- readiness status;
- readiness score;
- public catalog gap indicators;
- lifecycle status;
- risk-gate status;
- expected evidence-file presence.

The snapshot emits `improved`, `unchanged`, or `regressed`.

## Policy Progression

Use the pack to move teams gradually:

1. `report_only`
2. `warn`
3. `block_on_payload_violation`
4. `block_on_high_risk`
5. `block_on_release_risk`

`block_on_release_risk` fails only when the payload policy fails, hash-chain
verification fails, or the MLOps readiness status is `block`.

## Boundary

The pack contains hashes, counts, controlled labels, statuses, and portable
metadata indicators. It must not contain raw datasets, prompts, completions,
token sequences, embeddings, model weights, checkpoint bytes, raw diffs,
customer data, private Atlas rows, private scoring weights, or proprietary
correlation recipes.

MLflow/DVC evidence attachment and spend-readiness signals remain follow-on
items.
