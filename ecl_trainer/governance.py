from __future__ import annotations

from pathlib import Path
from typing import Any

from ecl_trainer.core.ledger import AppendOnlyEventLog, HashChainVerifier, LocalEventReplay
from ecl_trainer.core.models import (
    HumanApprovalRecordedEvent,
    RiskGateDecisionEvent,
)
from ecl_trainer.core.policy import NoPayloadValidator
from ecl_trainer.core.serialization import canonical_sha256
from ecl_trainer.oracle.atlas import _EclInternalCore
from ecl_trainer.oracle.domains import IndustryDomain
from ecl_trainer.oracle.shield import EclPreFlightShield

ADMIT = "ADMIT"
ADMIT_WITH_WARNINGS = "ADMIT_WITH_WARNINGS"
BLOCK = "BLOCK"

RISK_ACCEPTANCE_CODES = frozenset(
    {
        "accepted_non_release_eval",
        "mitigated_by_dataset_filter",
        "approved_private_benchmark",
        "approved_lineage_exception",
    }
)


class RiskScoreProcessor:
    def score_events(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        oracle_events = [event for event in events if event.get("event_type") == "oracle_shield_run"]
        latest_oracle = oracle_events[-1] if oracle_events else {}
        passport_events = [event for event in events if event.get("event_type") == "compliance_passport_generated"]
        latest_passport = passport_events[-1] if passport_events else {}

        critical = int(latest_oracle.get("critical_count", 0))
        warn = int(latest_oracle.get("warn_count", 0))
        review = int(latest_oracle.get("review_count", 0))
        quarantine = int(latest_oracle.get("quarantine_count", 0))
        benchmark = int(latest_oracle.get("benchmark_alert_count", 0))
        lineage = int(latest_oracle.get("lineage_alert_count", 0))
        provenance = int(latest_oracle.get("provenance_gap_count", 0))

        training_data_risk_score = min(100, critical * 45 + warn * 20 + quarantine * 15 + review * 10)
        benchmark_contamination_score = min(100, benchmark * 85 + quarantine * 10)
        lineage_loop_score = min(100, lineage * 90)
        provenance_completeness_score = max(0, 100 - provenance * 40 - review * 15)
        passport_valid = bool(latest_passport.get("hash_chain_valid", True))
        compliance_readiness_score = max(
            0,
            min(100, provenance_completeness_score - critical * 25 + (10 if passport_events and passport_valid else 0)),
        )

        if critical or quarantine or benchmark_contamination_score >= 80 or lineage_loop_score >= 80:
            risk_gate_status = BLOCK
        elif warn or review or compliance_readiness_score < 80:
            risk_gate_status = ADMIT_WITH_WARNINGS
        else:
            risk_gate_status = ADMIT

        recommendations: list[str] = []
        if benchmark_contamination_score >= 80:
            recommendations.append("restrict_eval_overlap_context")
        if lineage_loop_score >= 80:
            recommendations.append("require_external_grounding")
        if provenance_completeness_score < 90:
            recommendations.append("require_provenance_review")
        if risk_gate_status == BLOCK:
            recommendations.append("block_runtime_binding")

        scorecard = {
            "risk_gate_status": risk_gate_status,
            "training_data_risk_score": training_data_risk_score,
            "benchmark_contamination_score": benchmark_contamination_score,
            "lineage_loop_score": lineage_loop_score,
            "provenance_completeness_score": provenance_completeness_score,
            "compliance_readiness_score": compliance_readiness_score,
            "runtime_policy_recommendations": sorted(set(recommendations)),
        }
        NoPayloadValidator().validate(scorecard)
        return scorecard


class RiskGateDecisionRecorder:
    def append_decision(
        self,
        *,
        ledger_path: str | Path,
        project_namespace: str,
        scorecard: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        path = Path(ledger_path)
        events = list(LocalEventReplay(path).iter_events())
        scorecard = scorecard or RiskScoreProcessor().score_events(events)
        event = RiskGateDecisionEvent(
            project_namespace=project_namespace,
            risk_gate_status=str(scorecard["risk_gate_status"]),
            training_data_risk_score=int(scorecard["training_data_risk_score"]),
            benchmark_contamination_score=int(scorecard["benchmark_contamination_score"]),
            lineage_loop_score=int(scorecard["lineage_loop_score"]),
            provenance_completeness_score=int(scorecard["provenance_completeness_score"]),
            compliance_readiness_score=int(scorecard["compliance_readiness_score"]),
            runtime_policy_recommendations=list(scorecard.get("runtime_policy_recommendations", [])),
            risk_scorecard_hash_sha256=canonical_sha256(scorecard),
        )
        return AppendOnlyEventLog(path).append(event)


class AtlasMaturityReporter:
    def __init__(self, core: _EclInternalCore | None = None) -> None:
        self.core = core or _EclInternalCore()

    def summarize(self) -> dict[str, Any]:
        statuses = self.core.domain_statuses()
        priority_domains = [
            IndustryDomain.FINANCIAL_SERVICES.value,
            IndustryDomain.HEALTHCARE_CLINICAL.value,
            IndustryDomain.LEGAL_REGULATORY.value,
            IndustryDomain.IT_SOFTWARE.value,
        ]
        summary = {
            "active_domain_count": sum(1 for status in statuses.values() if status == "active"),
            "registered_domain_count": sum(1 for status in statuses.values() if status == "registered"),
            "priority_domains": {domain: statuses.get(domain, "missing_seed") for domain in priority_domains},
            "domain_maturity_summary_hash_sha256": canonical_sha256(statuses),
        }
        NoPayloadValidator().validate(summary)
        return summary


class PolicySimulator:
    def simulate(
        self,
        *,
        manifest: dict[str, Any],
        project_namespace: str,
        enabled_domains: str = "",
        domain_selection_mode: str = "auto",
        risk_policy: str = "report_only",
    ) -> dict[str, Any]:
        alerts = EclPreFlightShield(
            enabled_domains=enabled_domains,
            domain_selection_mode=domain_selection_mode,
        ).validate_run_manifest(manifest)
        pseudo_event = {
            "event_type": "oracle_shield_run",
            "project_namespace": project_namespace,
            "critical_count": sum(1 for alert in alerts if alert.get("severity") == "CRITICAL"),
            "warn_count": sum(1 for alert in alerts if alert.get("severity") == "WARN"),
            "review_count": sum(1 for alert in alerts if alert.get("action_required") == "REVIEW"),
            "quarantine_count": sum(1 for alert in alerts if alert.get("action_required") == "QUARANTINE"),
            "benchmark_alert_count": sum(1 for alert in alerts if alert.get("category") == "BENCHMARK_LEAK"),
            "lineage_alert_count": sum(1 for alert in alerts if alert.get("category") == "MODEL_INBREEDING"),
            "provenance_gap_count": sum(1 for alert in alerts if alert.get("category") == "PROVENANCE_GAP"),
        }
        scorecard = RiskScoreProcessor().score_events([pseudo_event])
        result = {
            "simulation_mode": "no_append",
            "project_namespace": project_namespace,
            "risk_policy": risk_policy,
            "predicted_gate": scorecard["risk_gate_status"],
            "expected_event_types": [
                "ci_scan",
                "curriculum_blueprint_generated",
                "oracle_shield_run",
                "compliance_passport_generated",
                "risk_gate_decision",
                "diff_free_pr_evidence",
                "local_artifact_export",
            ],
            "alert_count": len(alerts),
            "scorecard": scorecard,
            "alerts_hash_sha256": canonical_sha256(alerts),
            "payload_policy": "passed",
        }
        NoPayloadValidator().validate(result)
        return result


class HumanApprovalRecorder:
    def record(
        self,
        *,
        ledger_path: str | Path,
        project_namespace: str,
        risk_id: str,
        approver_role: str,
        reason_code: str,
    ) -> dict[str, Any]:
        if reason_code not in RISK_ACCEPTANCE_CODES:
            raise ValueError(f"Unsupported risk acceptance reason code: {reason_code}")
        approval = {
            "project_namespace": project_namespace,
            "risk_id": risk_id,
            "approver_role": approver_role,
            "reason_code": reason_code,
            "accepted_risk_status": "accepted_with_controls",
        }
        event = HumanApprovalRecordedEvent(
            project_namespace=project_namespace,
            risk_id=risk_id,
            approver_role=approver_role,
            reason_code=reason_code,
            accepted_risk_status="accepted_with_controls",
            human_approval_hash_sha256=canonical_sha256(approval),
        )
        return AppendOnlyEventLog(ledger_path).append(event)


class LedgerQueryService:
    def __init__(self, ledger_path: str | Path) -> None:
        self.ledger_path = Path(ledger_path)

    def history(self, *, event_type: str | None = None, project_namespace: str | None = None) -> dict[str, Any]:
        events = list(
            LocalEventReplay(self.ledger_path).iter_events(
                event_type=event_type,
                project_namespace=project_namespace,
            )
        )
        result = {
            "event_count": len(events),
            "event_types": [str(event.get("event_type")) for event in events],
            "event_hashes_sha256": [str(event.get("event_hash_sha256")) for event in events],
            "hash_chain_verification": HashChainVerifier(self.ledger_path).verify(),
        }
        NoPayloadValidator().validate(result)
        return result

    def explain_chain(self) -> dict[str, Any]:
        events = list(LocalEventReplay(self.ledger_path).iter_events())
        edges = [
            {
                "from_event_hash_sha256": str(previous.get("event_hash_sha256")),
                "to_event_hash_sha256": str(current.get("event_hash_sha256")),
                "to_event_type": str(current.get("event_type")),
            }
            for previous, current in zip(events, events[1:], strict=False)
        ]
        result = {
            "event_count": len(events),
            "chain_edge_count": len(edges),
            "chain_edges": edges,
            "hash_chain_verification": HashChainVerifier(self.ledger_path).verify(),
        }
        NoPayloadValidator().validate(result)
        return result
