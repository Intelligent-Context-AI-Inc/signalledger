<!-- ecl-trainer:local-risk-report -->
## ECL Pre-Flight Shield
- Scan status: `pass`
- No-payload policy: `passed`
- Risk flags: `0`
- Hash chain: `valid`
- Mode: `local-only`

### Remediation Checklist
- Review missing license descriptors.
- Review provenance descriptors.
- Review benchmark and lineage risk flags.

## Risk Scorecard
- Gate: `ADMIT_WITH_WARNINGS`
- Training data risk: `30`
- Benchmark contamination: `0`
- Lineage loop: `0`
- Provenance completeness: `45`
- Compliance readiness: `55`

## Step-Zero Curriculum Optimization
- Structural similarity baseline: `not_declared`
- Pre-flight state: `WARN`
- Oracle alert count: `1`
- `WARN` `provenance gap` `REVIEW`
  - Signal: `incomplete_source_descriptor`
  - Why: `missing_provenance_blocks_audit_signoff`
  - Action: `add_license_and_source_hashes`

### Remediation Checklist
- `add_financial_regulatory_framework_tags`

### Local Compliance Passport
# ECL Learning Ledger Passport
- Profile: `internal_audit`
- Events: `3`
- Hash chain: `valid`
- Global structural core: `enabled`
- Enabled domains: `financial_services`
- SaaS exfiltration: `not executed`
- Dataset upload: `not executed`

## Domain Evidence
- financial regulatory tags
- financial sector distribution
- financial fiscal bounds
- SEC EDGAR tax structures tracked
- FINRA oversight definitions tracked
- 2026 Federal Reserve macro scenario matrices tracked

### Local Evidence
- SaaS account: `not required`
- Dataset upload: `not performed`
- Payload policy: `passed`
- Ledger verification: `valid`
- Supply-chain evidence: `generated`

### Intelligent Context Atlas
- Oracle status: `completed`
- Enabled domains: `financial_services`
- Skipped domains: `none`
- Atlas source records: `125`
- Atlas seeded domains: `20`

### Atlas Lifecycle
- Status: `CURRENT`
- Atlas version: `v0.1.0rc1-2026.Q3`
- Active days: `3`