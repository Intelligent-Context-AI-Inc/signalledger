# Local Scan Example

This example uses a safe metadata manifest and local ledger path only.

```bash
ecl-trainer scan --changed-only --project-namespace org/project --ledger-path .ecl/events.jsonl
ecl-trainer verify-log --ledger-path .ecl/events.jsonl
```
