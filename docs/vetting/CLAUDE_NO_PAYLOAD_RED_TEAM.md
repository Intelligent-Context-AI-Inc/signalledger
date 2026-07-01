# Claude Code Vet Packet: No-Payload Red-Team

You are acting as an independent Principal Security Red-Team Engineer reviewing the ECL Trainer / Intelligent Context Atlas repository.

## Review Goal

Find any path where raw payload, proprietary text, prompts, completions, token sequences, embeddings, model weights, diffs, notebook cells, secrets, or local sensitive paths could enter or leave the system.

The core product promise is:

- local-first by default
- no SaaS account required
- no dataset upload
- no raw payload capture
- every event, report, card export, CI comment, envelope, atlas source, and transport path must pass `NoPayloadValidator` before append, render, serialize, or submit

## Files To Inspect First

- `ecl_trainer/core/policy.py`
- `ecl_trainer/core/models.py`
- `ecl_trainer/core/ledger.py`
- `ecl_trainer/core/client.py`
- `ecl_trainer/ci/scanner.py`
- `ecl_trainer/ci/reporting.py`
- `ecl_trainer/compliance/reports.py`
- `ecl_trainer/compliance/pr_comment.py`
- `ecl_trainer/hub/huggingface_cards.py`
- `ecl_trainer/integrations/`
- `atlas_pipeline/`
- `atlas_sources/`
- `examples/ecl_records/financial-services-atlas-seed-ledger.sample.json`
- `tests/test_no_payload_policy.py`
- `tests/test_red_team_no_payload_boundaries.py`
- `tests/test_financial_services_seed_fixture.py`

## Attack Cases To Try Mentally

- Base64-like payload hidden in metadata strings
- Prompt/completion examples stored under innocent keys
- Notebook cell content inside config metadata
- Raw git diff text included in a CI report
- Token IDs disguised as histograms or metrics
- Embeddings disguised as numeric arrays
- Model weights/checkpoints passed through integration callbacks
- Dataset preview rows from Hugging Face, Axolotl, PyTorch, or Ray integrations
- Secrets or local filesystem paths in source descriptors
- Long free-form descriptions inside atlas source manifests
- PR comments or compliance reports that render unsafe strings after validation

## Expected Output Format

Return findings only. If no issue is found, say so explicitly and list residual risks.

Use this format:

```text
Severity: Critical | High | Medium | Low
File: path:line
Finding:
Impact:
Evidence:
Recommended fix:
Suggested test:
```

## Review Standard

Be skeptical. Prefer concrete exploit paths over theoretical concerns. Do not suggest collecting raw examples for tests; use synthetic strings that represent forbidden classes without including real sensitive data.

