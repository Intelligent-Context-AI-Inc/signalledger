from ecl_trainer.integrations.huggingface import ECLTrainerCallback


def build_callback() -> ECLTrainerCallback:
    return ECLTrainerCallback(
        project_namespace="org/project",
        training_run_id="run_001",
        dataset_ref="s3://training-data",
        ledger_path=".ecl/events.jsonl",
    )
