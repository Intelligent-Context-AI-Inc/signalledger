from ecl_trainer.compliance.registries import ModelLineageRegistry
from ecl_trainer.compliance.risk import RiskGatekeeper
from ecl_trainer.core.models import ModelLineageRecord


def test_benchmark_alias_flagged():
    summary = RiskGatekeeper().evaluate({"benchmark_family_indicator": "mmlu"})
    assert summary.risk_flags[0].risk_type == "benchmark_contamination"


def test_model_lineage_flagged():
    registry = ModelLineageRegistry()
    registry.add(ModelLineageRecord(model_id="child", parent_model_id="parent", ancestor_model_ids=["root"]))
    summary = RiskGatekeeper(lineage_registry=registry).evaluate({"origin_model_id": "parent"}, model_id="child")
    assert summary.risk_flags[0].risk_type == "model_lineage_feedback_loop"
