"""人工复核工作台 API"""
from fastapi import APIRouter, Query
from models.schemas import (
    ReviewTaskGenerateRequest, ReviewTaskAssignRequest,
    ReviewRecordSubmitRequest, ArbitrationRequest, ReviewStatsOut,
)
from services.review_workflow_service import (
    generate_review_tasks, assign_reviewers,
    submit_review, check_consensus, arbitrate, get_review_stats,
)

# Note: submit_review and arbitrate in the service operate on ReviewTask objects.
# The API stores tasks as dicts; we convert on the fly where needed.
from services.review_workflow_service import ReviewTask as _ReviewTask


def _dict_to_task(t: dict) -> _ReviewTask:
    """Convert a stored task dict back to a ReviewTask for service calls."""
    return _ReviewTask(
        task_id=t.get("task_id", t.get("id", "")),
        batch_id=str(t.get("batch_id", "")),
        enterprise_id=str(t.get("enterprise_id", "")),
        credit_code=t.get("credit_code", ""),
        enterprise_name=t.get("enterprise_name", ""),
        priority=t.get("priority", ""),
        status=t.get("status", "pending"),
        sport_score=t.get("sport_score", 0.0),
        sport_category=t.get("sport_category", ""),
        code_type=t.get("code_type", ""),
        evidence_relation=t.get("evidence_relation", ""),
        confidence=t.get("confidence", 0.0),
        effective_share=t.get("effective_share", 0.0),
        share_source=t.get("share_source", ""),
        reviewer_a=t.get("assigned_to_a", ""),
        reviewer_b=t.get("assigned_to_b", ""),
        trigger_rules=t.get("trigger_rules", []),
        risk_reasons=t.get("risk_reasons", []),
        evidence_summary=t.get("evidence_summary", ""),
        created_at=t.get("created_at", ""),
        updated_at=t.get("updated_at", ""),
    )

router = APIRouter()

# 内存存储（后续可迁移到数据库）
_review_tasks: list = []
_review_records: dict = {}  # task_id -> {"A": record, "B": record}
_arbitration_records: dict = {}  # task_id -> arbitration_record


@router.post("/tasks/generate", summary="生成复核任务")
async def generate_tasks(req: ReviewTaskGenerateRequest):
    """根据识别结果自动生成P1-P4分级复核任务"""
    if not req.recognition_results:
        return {"code": 400, "message": "请提供识别结果列表", "data": None}

    tasks = generate_review_tasks(req.batch_id, req.recognition_results)
    _review_tasks.clear()
    _review_tasks.extend(tasks)
    _review_records.clear()
    _arbitration_records.clear()

    stats = get_review_stats(tasks)

    return {
        "code": 200,
        "message": f"已生成 {len(tasks)} 个复核任务",
        "data": {
            "tasks": tasks,
            "stats": stats,
        },
    }


@router.get("/tasks", summary="复核任务列表")
async def list_tasks(
    batch_id: int = Query(None, description="批次ID"),
    status: str = Query("", description="筛选状态"),
    priority: str = Query("", description="筛选优先级"),
    assignee: str = Query("", description="筛选分配人"),
    page: int = Query(1, description="页码"),
    page_size: int = Query(20, description="每页数量"),
):
    """获取复核任务列表（支持筛选和分页）"""
    tasks = list(_review_tasks)

    if status:
        tasks = [t for t in tasks if t.get("status") == status]
    if priority:
        tasks = [t for t in tasks if t.get("priority") == priority]
    if assignee:
        tasks = [
            t for t in tasks
            if t.get("assigned_to_a") == assignee or t.get("assigned_to_b") == assignee
        ]

    total = len(tasks)
    start = (page - 1) * page_size
    end = start + page_size
    paged = tasks[start:end]

    return {
        "code": 200,
        "data": {
            "tasks": paged,
            "total": total,
            "page": page,
            "page_size": page_size,
            "stats": get_review_stats(_review_tasks),
        },
    }


@router.get("/tasks/{task_id}", summary="任务详情")
async def task_detail(task_id: int):
    """获取单个复核任务详情（含已有复核意见）"""
    task = next((t for t in _review_tasks if t.get("id") == task_id), None)
    if not task:
        return {"code": 404, "message": "任务不存在", "data": None}

    records = _review_records.get(task_id, {})
    arbitration = _arbitration_records.get(task_id)

    return {
        "code": 200,
        "data": {
            "task": task,
            "record_a": records.get("A"),
            "record_b": records.get("B"),
            "arbitration": arbitration,
        },
    }


@router.post("/tasks/{task_id}/assign", summary="分配复核员")
async def assign_task(task_id: int, req: ReviewTaskAssignRequest):
    """为指定任务分配双人复核员"""
    task = next((t for t in _review_tasks if t.get("id") == task_id), None)
    if not task:
        return {"code": 404, "message": "任务不存在", "data": None}

    task["assigned_to_a"] = req.reviewer_a
    task["assigned_to_b"] = req.reviewer_b
    task["status"] = "assigned"
    task["status_label"] = "已分配"

    return {"code": 200, "message": "复核员已分配", "data": task}


@router.post("/records", summary="提交复核意见")
async def submit_record(req: ReviewRecordSubmitRequest):
    """提交一条复核意见"""
    task = next((t for t in _review_tasks if t.get("id") == req.review_task_id), None)
    if not task:
        return {"code": 404, "message": "任务不存在", "data": None}

    review_task = _dict_to_task(task)
    review_task = submit_review(
        task=review_task,
        reviewer_role=req.reviewer_role,
        sport_attribute=req.sport_attribute,
        sport_category=req.sport_category_override or "",
        sport_share=req.sport_share_override,
        reason=req.reason,
    )
    # Convert result back to dict for storage
    record = {
        "reviewer_name": req.reviewer_name,
        "reviewer_role": req.reviewer_role,
        "sport_attribute": req.sport_attribute,
        "sport_category": req.sport_category_override,
        "sport_share": req.sport_share_override,
        "reason": req.reason,
        "submitted_at": review_task.updated_at,
    }

    # 存储记录
    if req.review_task_id not in _review_records:
        _review_records[req.review_task_id] = {}
    _review_records[req.review_task_id][req.reviewer_role] = record

    # 更新任务状态
    task["status"] = "reviewing"
    task["status_label"] = "复核中"

    # 检查双方是否都已提交
    task_records = _review_records.get(req.review_task_id, {})
    if "A" in task_records and "B" in task_records:
        consensus = check_consensus(task_records["A"], task_records["B"])
        if consensus["is_consensus"]:
            task["status"] = "confirmed"
            task["status_label"] = "已确认"
        else:
            task["status"] = "disputed"
            task["status_label"] = "待仲裁"

    return {"code": 200, "message": "复核意见已提交", "data": record}


@router.get("/tasks/{task_id}/consensus", summary="检查一致性")
async def get_consensus(task_id: int):
    """检查双人复核是否达成共识"""
    records = _review_records.get(task_id, {})
    if "A" not in records or "B" not in records:
        return {
            "code": 200,
            "data": {
                "is_consensus": False,
                "detail": "双方尚未全部提交复核意见",
                "records_submitted": list(records.keys()),
            },
        }

    consensus = check_consensus(records["A"], records["B"])
    return {"code": 200, "data": consensus}


@router.post("/arbitrate", summary="提交仲裁")
async def do_arbitrate(req: ArbitrationRequest):
    """对分歧任务进行仲裁"""
    task = next((t for t in _review_tasks if t.get("id") == req.review_task_id), None)
    if not task:
        return {"code": 404, "message": "任务不存在", "data": None}

    records = _review_records.get(req.review_task_id, {})
    record_a = records.get("A", {})
    record_b = records.get("B", {})

    review_task = _dict_to_task(task)
    review_task = arbitrate(
        task=review_task,
        arbiter_name=req.arbiter_name,
        final_attribute=req.final_sport_attribute,
        final_category=req.final_sport_category or "",
        final_share=req.final_sport_share,
        reason=req.decision_reason,
    )
    arbitration_record = {
        "arbiter": req.arbiter_name,
        "final_sport_attribute": req.final_sport_attribute,
        "final_sport_category": req.final_sport_category,
        "final_sport_share": req.final_sport_share,
        "decision_reason": req.decision_reason,
        "arbitrated_at": review_task.updated_at,
    }

    _arbitration_records[req.review_task_id] = arbitration_record
    task["status"] = "locked"
    task["status_label"] = "已锁定"

    return {"code": 200, "message": "仲裁完成，任务已锁定", "data": arbitration_record}


@router.get("/stats", summary="复核统计")
async def get_stats(batch_id: int = Query(None)):
    """获取复核工作统计"""
    stats = get_review_stats(_review_tasks)
    return {"code": 200, "data": stats}
