"""
人工复核工作流服务 v1.0

核心机制：
  - P1-P4 四级优先级自动分级
  - 双人独立复核
  - 分歧自动仲裁
  - 完整审计记录

复核优先级定义：
  P1: 代码与文本明显冲突、模型与人工差异大、SportShare在阈值边界
  P2: 潜在跨界企业、置信度中等（0.5-0.7）
  P3: 文本证据较弱、词典边界样本、单一关键词命中
  P4: 代码与文本一致、直接体育代码+高置信度（>0.85）、证据充分
"""

from typing import List, Dict, Any, Optional
from datetime import datetime


# ============================================================
# 优先级判定
# ============================================================

def determine_priority(recognition_result: Dict[str, Any]) -> str:
    """
    根据识别结果自动判定复核优先级

    返回: "P1" / "P2" / "P3" / "P4"
    """
    code_type = recognition_result.get("code_type", "none")
    sport_category = recognition_result.get("sport_category", "")
    confidence = recognition_result.get("confidence", 0)
    sport_ratio = recognition_result.get("sport_ratio", 0)
    is_crossover = recognition_result.get("is_crossover", False)
    keywords = recognition_result.get("keywords", [])
    total_lines = recognition_result.get("total_business_lines", 0)
    sport_lines = recognition_result.get("sport_business_lines", 0)
    crossover_type = recognition_result.get("crossover_type", "")

    # P1: 代码与文本明显冲突
    if code_type == "none" and sport_ratio > 0.5:
        return "P1"
    if code_type == "direct" and sport_ratio < 0.15:
        return "P1"
    if sport_ratio > 0.4 and confidence < 0.6:
        return "P1"
    # 比重在关键边界（0.1 上下）的高影响力企业
    if 0.08 <= sport_ratio <= 0.15 and confidence > 0.7:
        return "P1"

    # P2: 潜在跨界、中等置信度
    if "纯跨界" in crossover_type:
        return "P2"
    if 0.5 <= confidence < 0.7:
        return "P2"
    if is_crossover and sport_ratio > 0.2:
        return "P2"

    # P3: 文本证据较弱
    if len(keywords) <= 2 and sport_ratio > 0:
        return "P3"
    if total_lines > 0 and sport_lines == 1 and sport_ratio < 0.3:
        return "P3"
    if confidence < 0.6 and sport_ratio > 0:
        return "P3"

    # P4: 证据充分，无需优先复核
    return "P4"


# ============================================================
# 任务生成
# ============================================================

def generate_review_tasks(
    batch_id: int,
    results: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    根据识别/比重结果自动生成复核任务列表

    输入：recognition results list (from recognize_sport_business or batch_recognize)
    输出：review task dicts
    """
    tasks = []
    for i, result in enumerate(results):
        # 只对体育企业或边界企业生成复核任务
        is_sport = result.get("is_sport", False)
        sport_ratio = result.get("sport_ratio", 0)
        if not is_sport and sport_ratio < 0.05:
            continue

        priority = determine_priority(result)
        tasks.append({
            "id": i + 1,  # 临时ID
            "enterprise_id": result.get("enterprise_id"),
            "credit_code": result.get("credit_code", ""),
            "enterprise_name": result.get("enterprise_name", ""),
            "priority": priority,
            "status": "pending",
            "status_label": "待分配",
            "sport_category": result.get("sport_category", ""),
            "sport_share": result.get("sport_ratio", 0),
            "industry_code": result.get("industry_code", ""),
            "confidence": result.get("confidence", 0),
            "crossover_type": result.get("crossover_type", ""),
            "assigned_to_a": None,
            "assigned_to_b": None,
            "arbiter": None,
            "batch_id": batch_id,
            "created_at": datetime.now().isoformat(),
        })

    # 按优先级排序
    priority_order = {"P1": 0, "P2": 1, "P3": 2, "P4": 3}
    tasks.sort(key=lambda t: priority_order.get(t["priority"], 4))

    return tasks


# ============================================================
# 双人复核 / 一致性检查 / 仲裁
# ============================================================

def assign_reviewers(
    tasks: List[Dict[str, Any]],
    task_ids: List[int],
    reviewer_a: str,
    reviewer_b: str,
) -> List[Dict[str, Any]]:
    """分配复核员（双人）"""
    for task in tasks:
        if task["id"] in task_ids:
            task["assigned_to_a"] = reviewer_a
            task["assigned_to_b"] = reviewer_b
            task["status"] = "assigned"
            task["status_label"] = "已分配"
    return tasks


def submit_review(
    task: Dict[str, Any],
    reviewer_name: str,
    reviewer_role: str,
    sport_attribute: str,
    sport_category_override: Optional[str],
    sport_share_override: Optional[float],
    reason: str,
) -> Dict[str, Any]:
    """提交单条复核意见"""
    record = {
        "review_task_id": task["id"],
        "reviewer_name": reviewer_name,
        "reviewer_role": reviewer_role,
        "sport_attribute": sport_attribute,
        "sport_category_override": sport_category_override,
        "sport_share_override": sport_share_override,
        "reason": reason,
        "reviewed_at": datetime.now().isoformat(),
    }
    return record


def check_consensus(
    record_a: Dict[str, Any],
    record_b: Dict[str, Any],
) -> Dict[str, Any]:
    """
    检查双人复核结论是否一致

    三个维度同时一致才算共识：
      1. 体育属性判定（yes/no/uncertain）
      2. 体育业态
      3. SportShare（差值<10%）
    """
    attr_match = record_a.get("sport_attribute") == record_b.get("sport_attribute")
    cat_match = record_a.get("sport_category_override") == record_b.get("sport_category_override")

    share_a = record_a.get("sport_share_override")
    share_b = record_b.get("sport_share_override")
    share_match = True
    if share_a is not None and share_b is not None:
        share_match = abs(share_a - share_b) < 0.10

    is_consensus = attr_match and cat_match and share_match

    return {
        "is_consensus": is_consensus,
        "attr_match": attr_match,
        "cat_match": cat_match,
        "share_match": share_match,
        "detail": f"属性{'一致' if attr_match else '不一致'} | "
                  f"业态{'一致' if cat_match else '不一致'} | "
                  f"比重{'一致' if share_match else '不一致'}"
    }


def arbitrate(
    task: Dict[str, Any],
    record_a: Dict[str, Any],
    record_b: Dict[str, Any],
    arbiter_name: str,
    final_sport_attribute: str,
    final_sport_category: Optional[str],
    final_sport_share: Optional[float],
    decision_reason: str,
) -> Dict[str, Any]:
    """仲裁裁决"""
    return {
        "review_task_id": task["id"],
        "arbiter_name": arbiter_name,
        "reviewer_a_opinion": _format_opinion(record_a),
        "reviewer_b_opinion": _format_opinion(record_b),
        "final_sport_attribute": final_sport_attribute,
        "final_sport_category": final_sport_category,
        "final_sport_share": final_sport_share,
        "decision_reason": decision_reason,
        "created_at": datetime.now().isoformat(),
    }


def _format_opinion(record: Dict[str, Any]) -> str:
    parts = [f"体育属性: {record.get('sport_attribute', 'N/A')}"]
    if record.get("sport_category_override"):
        parts.append(f"业态: {record['sport_category_override']}")
    if record.get("sport_share_override") is not None:
        parts.append(f"比重: {record['sport_share_override']:.1%}")
    if record.get("reason"):
        parts.append(f"理由: {record['reason'][:100]}")
    return " | ".join(parts)


# ============================================================
# 统计
# ============================================================

def get_review_stats(tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """复核任务统计"""
    total = len(tasks)
    status_counts = {}
    priority_counts = {}
    for t in tasks:
        st = t.get("status", "pending")
        status_counts[st] = status_counts.get(st, 0) + 1
        pr = t.get("priority", "P4")
        priority_counts[pr] = priority_counts.get(pr, 0) + 1

    confirmed = status_counts.get("confirmed", 0)
    locked = status_counts.get("locked", 0)
    disputed = status_counts.get("disputed", 0)
    resolved = confirmed + locked
    total_with_decision = resolved + disputed

    return {
        "total_tasks": total,
        "pending": status_counts.get("pending", 0),
        "assigned": status_counts.get("assigned", 0),
        "reviewing": status_counts.get("reviewing", 0),
        "disputed": disputed,
        "confirmed": confirmed,
        "locked": locked,
        "info_insufficient": status_counts.get("info_insufficient", 0),
        "p1_count": priority_counts.get("P1", 0),
        "p2_count": priority_counts.get("P2", 0),
        "p3_count": priority_counts.get("P3", 0),
        "p4_count": priority_counts.get("P4", 0),
        "consensus_rate": round(confirmed / total_with_decision * 100, 1) if total_with_decision > 0 else 0,
        "arbitration_rate": round(disputed / total_with_decision * 100, 1) if total_with_decision > 0 else 0,
    }
