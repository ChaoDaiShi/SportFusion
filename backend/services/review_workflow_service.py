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
