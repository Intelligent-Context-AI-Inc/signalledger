# Artifact Viewer

## Command

```bash
ecl-trainer artifact-viewer build \
  --reports-dir .ecl-trainer/reports \
  --ledger-path .ecl-trainer/events.jsonl \
  --output .ecl-trainer/reports/artifact-viewer.html
```

## Purpose

The viewer turns the local artifact folder into a single static HTML page for demos and internal review. It summarizes file hashes, safe previews, and ledger verification status.

## Boundaries

- Reads local artifacts only.
- Does not upload reports.
- Does not expose private Atlas rows.
- Reuses rendered-text validation before writing the HTML.

## Recommended Use

After a PR scan, attach `artifact-viewer.html` to a buyer walkthrough or open it locally during a security review.
