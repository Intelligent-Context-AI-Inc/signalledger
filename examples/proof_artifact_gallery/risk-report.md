# ECL Trainer Risk Report

- Status: `high_risk`
- Policy: `report_only`
- Metadata files scanned: `2`
- Payload policy: `passed`

## Risk Flags

- `high` `benchmark_contamination`: benchmark alias overlap detected from metadata aliases only.

## Step-Zero Curriculum Optimization

- Pre-flight state: `CRITICAL`
- Recommended action: `QUARANTINE`
- Structural signals used: hashes, controlled tags, benchmark aliases, lineage IDs, and aggregate distributions.

### Remediation Checklist

- `remove_benchmark_overlap`
- `regenerate_metadata_fingerprint`
- `review_lineage_source`
- `rerun_ecl_preflight`
