# Human-Friendly Risk Explanations

## Report Pattern

Each risk finding should answer four questions:

1. What happened?
2. Why does it matter?
3. What should the team do next?
4. What was not inspected?

## Example

```md
### Benchmark Contamination

What happened: ECL found a benchmark alias overlap in metadata.

Why it matters: Training data that overlaps evaluation targets can inflate model quality signals.

What to do next: Remove benchmark-derived sources, regenerate the metadata fingerprint, and rerun ECL.

What was not inspected: ECL did not inspect raw examples, prompts, completions, or token sequences.
```

## Copy Rule

Use controlled labels and actions. Do not include raw snippets, rows, prompts, or document previews in explanations.
