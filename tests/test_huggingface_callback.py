from ecl_trainer.integrations.huggingface import ECLTrainerCallback


def test_huggingface_callback_logs_metadata(tmp_path):
    callback = ECLTrainerCallback(
        project_namespace="project",
        training_run_id="run",
        dataset_ref="hf://dataset",
        ledger_path=str(tmp_path / "events.jsonl"),
    )
    callback.on_train_begin()
    assert callback.last_dataset_hash
