from ecl_trainer.integrations.axolotl import ECLAxolotlPlugin, load_axolotl_config_metadata


def test_axolotl_plugin_parses_metadata(tmp_path):
    config = tmp_path / "axolotl.yaml"
    config.write_text("base_model: base\nsequence_len: 2048\n", encoding="utf-8")
    metadata = load_axolotl_config_metadata(config)
    assert metadata["base_model"] == "base"
    plugin = ECLAxolotlPlugin(
        project_namespace="project",
        training_run_id="run",
        config_path=config,
        ledger_path=tmp_path / "events.jsonl",
    )
    event = plugin.on_train_start()
    assert event["event_type"] == "data_ingest"
