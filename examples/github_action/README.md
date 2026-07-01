# GitHub Action Example

Copy `ecl-trainer.yml` into `.github/workflows/`. A pull request will receive a metadata-only ECL risk report through the job summary, a local artifact bundle, and a sticky PR comment when the repository token has comment permission.

No ECL SaaS account is required, no dataset upload is performed, and the compliance passport is generated locally from the append-only ledger.

Use `ecl-trainer.manifest.json` as the first safe metadata manifest and `expected-pr-comment.md` as the review target for first-run validation.

The full first-run guide is in `docs/ecl_learning_ledger/GITHUB_ACTION_FIRST_RUN_UX.md`.
