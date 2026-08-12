"""
复核工作流服务 — Phase 4: config-driven P1-P4, dual review, arbitration.

Consumes Phase 3: SportScore, EvidenceRelation, SportShare, confidence.
P1-P4 rules from config/review_priority_rules.json.
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


@dataclass
class ReviewTask:
    task_id: str = ""
    batch_id: str = ""
    enterprise_id: str = ""
    credit_code: str = ""
    enterprise_name: str = ""
    priority: str = ""
    status: str = "pending"
    sport_score: float = 0.0
    sport_category: str = ""
    code_type: str = ""
    evidence_relation: str = ""
    confidence: float = 0.0
    effective_share: float = 0.0
    share_source: str = ""
    reviewer_a: str = ""
    reviewer_b: str = ""
    arbiter: str = ""
    a_result: dict[str, Any] | None = None
    b_result: dict[str, Any] | None = None
    arbiter_result: dict[str, Any] | None = None
    final_sport_attribute: str = ""
    final_sport_category: str = ""
    final_share: float | None = None
    trigger_rules: list[str] = field(default_factory=list)
    risk_reasons: list[str] = field(default_factory=list)
    evidence_summary: str = ""
    created_at: str = ""
    updated_at: str = ""


def load_priority_rules() -> dict[str, Any]:
    path = _CONFIG_DIR / "review_priority_rules.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def determine_priority(rec: dict[str, Any]) -> tuple[str, list[str], list[str]]:
    """Determine P1-P4 from recognition evidence. Returns (priority, triggers, reasons)."""
    rules_config = load_priority_rules()
    ctx = {
        "is_sport": rec.get("is_sport", False),
        "sport_score": rec.get("sport_score", 0.0),
        "code_type": rec.get("code_type", "none"),
        "confidence": rec.get("confidence", 0.0),
        "evidence_relation": rec.get("evidence_relation", ""),
        "is_crossover": rec.get("is_crossover", False),
        "len(keywords)": len(rec.get("keywords", [])),
        "total_lines": rec.get("total_business_lines", 0),
        "sport_lines": rec.get("sport_business_lines", 0),
    }
    for priority in ["P1", "P2", "P3", "P4"]:
        prio = rules_config["priorities"].get(priority, {})
        triggers, reasons = [], []
        for rule in prio.get("rules", []):
            try:
                if eval(rule["condition"], {"__builtins__": {}}, ctx):
                    triggers.append(rule["name"])
                    reasons.append(rule["reason"])
            except Exception:  # noqa: BLE001, S110 — rule eval fallback is intentional
                pass
        if triggers:
            return (priority, triggers, reasons)
    return ("P4", ["default"], ["未触发明确规则"])


def generate_review_tasks(
    batch_id: str,
    recognition_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """API-compatible wrapper: generate review tasks and return as dicts."""
    tasks = create_review_tasks(recognition_results, None, str(batch_id))
    return [_task_to_dict(t) for t in tasks]


def _task_to_dict(task: ReviewTask) -> dict[str, Any]:
    return {
        "id": task.task_id,
        "task_id": task.task_id,
        "batch_id": task.batch_id,
        "enterprise_id": task.enterprise_id,
        "credit_code": task.credit_code,
        "enterprise_name": task.enterprise_name,
        "priority": task.priority,
        "status": task.status,
        "sport_score": task.sport_score,
        "sport_category": task.sport_category,
        "code_type": task.code_type,
        "evidence_relation": task.evidence_relation,
        "confidence": task.confidence,
        "effective_share": task.effective_share,
        "share_source": task.share_source,
        "assigned_to_a": task.reviewer_a,
        "assigned_to_b": task.reviewer_b,
        "final_sport_attribute": task.final_sport_attribute,
        "final_sport_category": task.final_sport_category,
        "final_share": task.final_share,
        "trigger_rules": task.trigger_rules,
        "risk_reasons": task.risk_reasons,
        "evidence_summary": task.evidence_summary,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }


def assign_reviewers(task: dict[str, Any], reviewer_a: str, reviewer_b: str) -> dict[str, Any]:
    """Assign dual reviewers to a task dict."""
    task["assigned_to_a"] = reviewer_a
    task["assigned_to_b"] = reviewer_b
    task["status"] = "assigned"
    task["status_label"] = "已分配"
    return task


def check_consensus(record_a: dict[str, Any], record_b: dict[str, Any]) -> dict[str, Any]:
    """Check whether two review records reach consensus."""
    if not record_a or not record_b:
        return {"is_consensus": False, "detail": "双方尚未全部提交复核意见"}
    attr_match = record_a.get("sport_attribute") == record_b.get("sport_attribute")
    cat_match = record_a.get("sport_category") == record_b.get("sport_category")
    share_a = record_a.get("sport_share")
    share_b = record_b.get("sport_share")
    share_match = (share_a == share_b) if (share_a is not None and share_b is not None) else True
    return {
        "is_consensus": attr_match,
        "detail": (
            "双方达成共识" if attr_match
            else f"分歧: 审核员A={record_a.get('sport_attribute')}, 审核员B={record_b.get('sport_attribute')}"
        ),
        "agreements": {
            "sport_attribute": attr_match,
            "sport_category": cat_match,
            "sport_share": share_match,
        },
    }


def create_review_tasks(
    recognition_results: list[dict[str, Any]],
    sportshare_estimates: list[Any] | None = None,
    batch_id: str = "",
) -> list[ReviewTask]:
    tasks = []
    for i, rec in enumerate(recognition_results):
        priority, triggers, reasons = determine_priority(rec)
        share = sportshare_estimates[i] if sportshare_estimates and i < len(sportshare_estimates) else None
        task = ReviewTask(
            task_id=f"REVIEW-{uuid.uuid4().hex[:12].upper()}",
            batch_id=batch_id,
            enterprise_id=str(rec.get("enterprise_id", i)),
            credit_code=rec.get("credit_code", ""),
            enterprise_name=rec.get("enterprise_name", ""),
            priority=priority, status="pending",
            sport_score=rec.get("sport_score", 0.0),
            sport_category=rec.get("sport_category", ""),
            code_type=rec.get("code_type", "none"),
            evidence_relation=rec.get("evidence_relation", ""),
            confidence=rec.get("confidence", 0.0),
            effective_share=share.effective_share if share else 0.0,
            share_source=share.share_source if share else "none",
            trigger_rules=triggers, risk_reasons=reasons,
            evidence_summary=(
                f"SportScore={rec.get('sport_score', 0):.3f}, "
                f"code={rec.get('code_type', 'none')}, "
                f"relation={rec.get('evidence_relation', '')}"
            ),
            created_at=datetime.now(UTC).isoformat(),
        )
        tasks.append(task)
    return tasks


def submit_review(
    task: ReviewTask, reviewer_role: str,
    sport_attribute: str, sport_category: str = "",
    sport_share: float | None = None, reason: str = "",
) -> ReviewTask:
    result = {
        "reviewer_role": reviewer_role,
        "sport_attribute": sport_attribute,
        "sport_category": sport_category,
        "sport_share": sport_share, "reason": reason,
        "submitted_at": datetime.now(UTC).isoformat(),
    }
    if reviewer_role == "A":
        task.a_result = result
    else:
        task.b_result = result
    if task.a_result and task.b_result:
        if task.a_result["sport_attribute"] == task.b_result["sport_attribute"]:
            task.status = "confirmed"
            task.final_sport_attribute = task.a_result["sport_attribute"]
            task.final_sport_category = task.a_result.get("sport_category", "")
        else:
            task.status = "disputed"
    else:
        task.status = "in_review"
    task.updated_at = datetime.now(UTC).isoformat()
    return task


def arbitrate(
    task: ReviewTask, arbiter_name: str,
    final_attribute: str, final_category: str = "",
    final_share: float | None = None, reason: str = "",
) -> ReviewTask:
    task.arbiter = arbiter_name
    task.arbiter_result = {
        "arbiter": arbiter_name,
        "final_sport_attribute": final_attribute,
        "final_sport_category": final_category,
        "final_sport_share": final_share,
        "decision_reason": reason,
        "arbitrated_at": datetime.now(UTC).isoformat(),
    }
    task.final_sport_attribute = final_attribute
    task.final_sport_category = final_category
    task.final_share = final_share
    task.status = "confirmed"
    task.updated_at = datetime.now(UTC).isoformat()
    return task


def get_review_stats(tasks: list[ReviewTask]) -> dict[str, Any]:
    total = len(tasks)
    by_prio: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for t in tasks:
        by_prio[t.priority] = by_prio.get(t.priority, 0) + 1
        by_status[t.status] = by_status.get(t.status, 0) + 1
    conf = by_status.get("confirmed", 0)
    disp = by_status.get("disputed", 0)
    return {
        "total": total,
        "by_priority": by_prio,
        "by_status": by_status,
        "p1_p2_count": by_prio.get("P1", 0) + by_prio.get("P2", 0),
        "consensus_rate": round(conf / (conf + disp), 4) if (conf + disp) > 0 else 0.0,
        "arbitration_rate": round(disp / total, 4) if total > 0 else 0.0,
    }
