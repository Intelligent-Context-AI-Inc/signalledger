# Axolotl Plugin

The Axolotl integration is config-only and metadata-only. It parses a small allowlist of safe configuration keys, hashes dataset configuration references, strips local paths, and appends local ledger events.

## Safe Config Fields

- `base_model`
- `datasets` as a hashed descriptor
- `dataset_prepared_path` stripped to source root
- `sequence_len`
- `output_dir` stripped to source root

## Usage

```python
from ecl_trainer.integrations.axolotl import ECLAxolotlPlugin

plugin = ECLAxolotlPlugin(
    project_namespace="org/project",
    training_run_id="run_001",
    config_path="examples/axolotl_plugin/axolotl_config.safe.yml",
    ledger_path=".ecl/events.jsonl",
)
plugin.on_train_start()
```

The plugin does not log prompts, completions, dataset rows, token arrays, notebook cells, checkpoint bytes, model weights, or embeddings.
