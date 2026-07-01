from ecl_trainer.core.engine import EvaluationValueProcessor


def test_value_processor_updates_multiplier():
    processor = EvaluationValueProcessor()
    delta = processor.scalar_delta({"quality": 0.2, "cost": -0.1}, {"quality": 2.0, "cost": 1.0})
    assert delta == 0.30000000000000004
    assert processor.update_multiplier(2.0, delta) == 2.6


def test_value_processor_clamps_delta():
    processor = EvaluationValueProcessor()
    assert processor.update_multiplier(1.0, -5.0) == 0.050000000000000044
    assert processor.update_multiplier(1.0, 99.0) == 6.0


def test_value_processor_rejects_negative_old_weight():
    processor = EvaluationValueProcessor()
    try:
        processor.update_multiplier(-1.0, 0.1)
    except ValueError as exc:
        assert "old_weight" in str(exc)
    else:
        raise AssertionError("negative old weight should fail")
