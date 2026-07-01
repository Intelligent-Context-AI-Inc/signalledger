# GitLab CI

The GitLab CI template runs ECL Trainer in merge request pipelines using safe static metadata scanning by default.

## Usage

```yaml
include:
  - local: .gitlab-ci.ecl-trainer.yml
```

## Artifacts

The job writes metadata-only Markdown and JSON artifacts plus the local append-only ledger. Artifacts must not include raw diffs, notebook cells, dataset rows, model weights, embeddings, or secrets.

## Merge Request Notes

MR note posting is optional and requires an explicitly configured masked token when GitLab’s default token is insufficient. Tokens must never be printed.

## Risk Policies

Use `ECL_RISK_POLICY` with `report_only`, `warn`, `block_on_high_risk`, or `block_on_payload_violation`.

## Safe Static Scan Mode

The scanner detects training metadata paths and hashes changed paths. It does not execute project code or load datasets by default.
