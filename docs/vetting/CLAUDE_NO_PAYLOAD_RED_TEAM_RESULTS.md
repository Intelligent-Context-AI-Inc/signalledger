# Claude Code No-Payload Red-Team Results

## Summary

Claude Code identified three concrete no-payload hardening gaps before commit. All three were accepted and remediated before branch publication.

## Accepted Findings

### Rendered Markdown Length Bypass

- Severity: Critical
- Disposition: Fixed.
- Finding: `markdown_summary` was a safe metadata key, and long-string validation skipped safe keys. Rendered PR comments, reports, cards, and passport text validated under that key could bypass the long unstructured string guard.
- Action: Removed the safe-key length escape hatch. Any string longer than 1024 characters now fails closed regardless of key. `markdown_summary` is no longer treated as a safe key.
- Regression test: `test_markdown_summary_cannot_bypass_long_text_guard`.

### Concatenated Payload-Like Key Bypass

- Severity: High
- Disposition: Fixed.
- Finding: Payload-like keys such as `rawdata`, `fulltext`, `userprompt`, `bodytext`, and `embeddingvec` could avoid segment-based key detection.
- Action: Payload-like key detection now substring-matches all forbidden key patterns after normalization. Added `token` as a forbidden pattern to catch compact token-bearing keys.
- Regression test: `test_validator_rejects_concatenated_payload_like_keys`.

### Atlas URL Query Text Exemption

- Severity: Medium
- Disposition: Fixed.
- Finding: Long URL strings could carry arbitrary query or fragment text while bypassing the Atlas source-record long-text guard.
- Action: Atlas source URLs must now parse as short `http` or `https` URLs with a host, no query string, no fragment, and total length at or below 120 characters. Existing public seed references were normalized to remove query parameters.
- Regression tests: `test_source_records_reject_url_with_long_embedded_payload_text` and `test_source_records_reject_short_url_query_text`.

## Verification

- Targeted red-team/Atlas tests: 51 passed.
- Full pytest suite: 105 passed.
- Ruff: passed.
- Mypy: passed.
- Pyright: passed.
- Bandit: passed.
- Pip audit: no known vulnerabilities.
- Package build: passed.

