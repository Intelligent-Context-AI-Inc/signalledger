# Landing-Page Proof Kit

## Headline

ECL Learning Ledger gives LLM teams a local, metadata-only pre-flight shield before training starts.

## Buyer Promise

A GitHub PR gets a training-data risk report, compliance passport, hash-chain verification, PR comment body, and append-only ledger locally.

No SaaS account. No dataset upload. No raw payload in the audit trail.

## Current Tools Vs. ECL

| Question | Current tools | With ECL Learning Ledger |
| --- | --- | --- |
| What changed in the PR? | Git diff, code owners, manual review | Metadata-only changed-file scanner, no raw diff capture |
| Are secrets present? | Secret scanners | Secret scanners plus No-Payload validation before reports and ledger append |
| Is training metadata risky? | Manual dataset-card review | Atlas-backed risk flags from hashes, tags, lineage IDs, benchmark aliases, and distributions |
| Can compliance review the run? | Hand-written notes | Local compliance passport generated from the ledger |
| Can the artifact be verified later? | Static CI artifact | Hash-chained append-only ledger plus `verification.json` |
| Does the vendor need data access? | Often yes for hosted tooling | No SaaS account and no upload required |

## Public Proof-Point Snippets

These snippets are sanitized examples intended for landing-page and demo use. They show the shape of local artifacts without exposing private Atlas rows or raw training data.

### Risk Report

```md
## Step-Zero Curriculum Optimization
- Structural similarity baseline: `FineWebEduPublicAlpha`
- Pre-flight state: `CRITICAL`
- Oracle alert count: `2`
- `CRITICAL` `model inbreeding` `QUARANTINE`
- `CRITICAL` `benchmark leak` `QUARANTINE`

### Remediation Checklist
- `regenerate_metadata_fingerprint`
- `remove_benchmark_overlap`
- `review_synthetic_data_origin`
- `rotate_lineage_source`
```

### Compliance Passport

```md
# ECL Learning Ledger Passport
- Profile: `internal_audit`
- Events: `1`
- Hash chain: `valid`
- Global structural core: `enabled`
- Enabled domains: `financial_services`
- SaaS exfiltration: `not executed`
- Dataset upload: `not executed`

## Domain Evidence
- SEC EDGAR tax structures tracked
- FINRA oversight definitions tracked
- 2026 Federal Reserve macro scenario matrices tracked
```

### PR Comment

```md
### Local Evidence
- SaaS account: `not required`
- Dataset upload: `not performed`
- Payload policy: `passed`
- Ledger verification: `valid`
- Supply-chain evidence: `generated`

### Intelligent Context Atlas
- Oracle status: `completed`
- Enabled domains: `financial_services`
- Atlas source records: `65`
- Atlas seeded domains: `20`
```

## No-SaaS / No-Upload Story

The Dockerized GitHub Action runs inside the customer's CI workspace. It reads safe metadata files, validates that the metadata contains no payload-like fields, compares structural signals against the local Atlas, writes local reports, appends a ledger event, verifies the hash chain, and optionally posts a PR comment.

The action does not execute repo code, load raw datasets, inspect dataset rows, send metadata to ECL SaaS, or require customer credentials.

## Landing-Page Narrative

Before ECL, a training-data PR looked like a diff and a reviewer checklist.

After ECL, the PR becomes a local, cryptographically verifiable training-data risk event. The same CI run produces the risk report, compliance passport, verification file, PR comment, supply-chain evidence, and append-only ledger. Reviewers get an actionable signal before GPUs spin up, while security teams get proof that no raw payload crossed into the vendor path.

## CTA Copy

Copy one workflow into `.github/workflows/ecl-trainer.yml`, open a PR that changes training metadata, and inspect the local artifacts under `.ecl-trainer/reports/`.

Start in `report_only`. Graduate to `block_on_payload_violation` once the team is comfortable with the signal.
