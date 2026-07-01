# Packaged Trial Bundle

## Command

```bash
ecl-trainer trial-bundle --output-dir trial_bundles/ecl_learning_ledger
```

## Contents

- `README.md`
- `ecl-trainer.manifest.json`
- `walkthrough.md`

## Trial Promise

In 15 minutes, a customer can add one metadata manifest, run ECL in `report_only`, inspect local artifacts, and decide whether to advance to `block_on_payload_violation`.

## Success Criteria

- PR comment appears.
- `verification.json` reports a valid hash chain.
- Compliance passport exists.
- No SaaS credentials are configured.
- No raw payload is accepted.
