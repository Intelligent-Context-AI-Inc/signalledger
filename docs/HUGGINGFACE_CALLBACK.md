# Hugging Face Trainer Callback

`ECLTrainerCallback` captures training metadata from the Trainer lifecycle and appends local ledger events before any optional SaaS submission.

## Usage

```python
from ecl_trainer.integrations.huggingface import ECLTrainerCallback

trainer.add_callback(
    ECLTrainerCallback(
        project_namespace="org/project",
        training_run_id="run_001",
        dataset_ref="s3://training-data",
        ledger_path=".ecl/events.jsonl",
    )
)
```

## Logged Metadata

- dataset reference fingerprint
- source-root hash
- schema and chunk-manifest hashes
- checkpoint ID and checkpoint reference hash
- evaluation metric deltas
- priority vector
- local hash-chain linkage

## Never Logged

Raw dataset examples, prompts, completions, token sequences, labels, model weights, checkpoint bytes, embeddings, and raw local paths are never logged.

## SaaS Submission

SaaS submission is explicit opt-in through `SaaSControlPlaneClient`. The callback itself appends local events and does not phone home.
