"""人工复核工作台 API"""
from fastapi import APIRouter, Query
from models.schemas import (
    ArbitrationRequest,
    ReviewRecordSubmitRequest,
    ReviewTaskAssignRequest,
    ReviewTaskGenerateRequest,
)
from services.review_workflow_service import (
    ReviewTask,
    arbitrate,
    create_review_tasks,
    get_review_stats,
    submit_review,
)

router = APIRouter()

# 内存存储（后续可迁移到数据库）
_review_tasks: list = []
_review_records: dict = {}  # task_id -> {"A": record, "B": record}
_arbitration_records: dict = {}  # task_id -> arbitration_record

_STATUS_LABELS = {
    "pending": "待分配",
    "assigned": "已分配",
    "in_review": "复核中",
    "reviewing": "复核中",
    "disputed": "待仲裁",
    "confirmed": "已确认",
    "locked": "已锁定",
}


def _task_to_api(task: ReviewTask) -> dict:
    status = "reviewing" if task.status == "in_review" else task.status
    return {
        "id": task.task_id,
        "task_id": task.task_id,
        "enterprise_id": task.enterprise_id,
        "credit_code": task.credit_code,
        "enterprise_name": task.enterprise_name,
        "priority": task.priority,
        "status": status,
        "status_label": _STATUS_LABELS.get(task.status, task.status),
        "sport_score": task.sport_score,
        "sport_category": task.sport_category,
        "sport_share": task.effective_share,
        "confidence": task.confidence,
        "code_type": task.code_type,
        "evidence_relation": task.evidence_relation,
        "share_source": task.share_source,
        "assigned_to_a": task.reviewer_a,
        "assigned_to_b": task.reviewer_b,
        "arbiter": task.arbiter,
        "batch_id": task.batch_id,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }


def _stats_to_api(tasks: list[ReviewTask]) -> dict:
    stats = get_review_stats(tasks)
    by_priority = stats["by_priority"]
    by_status = stats["by_status"]
    return {
        "total_tasks": stats["total"],
        "pending": by_status.get("pending", 0),
        "assigned": by_status.get("assigned", 0),
        "reviewing": by_status.get("in_review", 0) + by_status.get("reviewing", 0),
        "disputed": by_status.get("disputed", 0),
        "confirmed": by_status.get("confirmed", 0),
        "locked": by_status.get("locked", 0),
        "p1_count": by_priority.get("P1", 0),
        "p2_count": by_priority.get("P2", 0),
        "p3_count": by_priority.get("P3", 0),
        "p4_count": by_priority.get("P4", 0),
        "consensus_rate": round(stats["consensus_rate"] * 100, 2),
        "arbitration_rate": round(stats["arbitration_rate"] * 100, 2),
    }


def _find_task(task_id: str) -> ReviewTask | None:
    return next((task for task in _review_tasks if task.task_id == str(task_id)), None)


@router.post("/tasks/generate", summary="生成复核任务")
async def generate_tasks(req: ReviewTaskGenerateRequest):
    """根据识别结果自动生成P1-P4分级复核任务"""
    if not req.recognition_results:
        return {"code": 400, "message": "请提供识别结果列表", "data": None}

    tasks = create_review_tasks(
        req.recognition_results,
        batch_id=str(req.batch_id),
    )
    _review_tasks.clear()
    _review_tasks.extend(tasks)
    _review_records.clear()
    _arbitration_records.clear()

    stats = _stats_to_api(tasks)

    return {
        "code": 200,
        "message": f"已生成 {len(tasks)} 个复核任务",
        "data": {
            "tasks": [_task_to_api(task) for task in tasks],
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

    if batch_id is not None:
        tasks = [t for t in tasks if t.batch_id == str(batch_id)]
    if status:
        domain_status = "in_review" if status == "reviewing" else status
        tasks = [t for t in tasks if t.status == domain_status]
    if priority:
        tasks = [t for t in tasks if t.priority == priority]
    if assignee:
        tasks = [
            t for t in tasks
            if t.reviewer_a == assignee or t.reviewer_b == assignee
        ]

    total = len(tasks)
    start = (page - 1) * page_size
    end = start + page_size
    paged = tasks[start:end]

    return {
        "code": 200,
        "data": {
            "tasks": [_task_to_api(task) for task in paged],
            "total": total,
            "page": page,
            "page_size": page_size,
            "stats": _stats_to_api(tasks),
        },
    }


@router.get("/tasks/{task_id}", summary="任务详情")
async def task_detail(task_id: str):
    """获取单个复核任务详情（含已有复核意见）"""
    task = _find_task(task_id)
    if not task:
        return {"code": 404, "message": "任务不存在", "data": None}

    records = _review_records.get(task_id, {})
    arbitration = _arbitration_records.get(task_id)

    return {
        "code": 200,
        "data": {
            "task": _task_to_api(task),
            "record_a": records.get("A") or task.a_result,
            "record_b": records.get("B") or task.b_result,
            "arbitration": arbitration,
        },
    }


@router.post("/tasks/{task_id}/assign", summary="分配复核员")
async def assign_task(task_id: str, req: ReviewTaskAssignRequest):
    """为指定任务分配双人复核员"""
    task = _find_task(task_id)
    if not task:
        return {"code": 404, "message": "任务不存在", "data": None}

    task.reviewer_a = req.reviewer_a
    task.reviewer_b = req.reviewer_b
    task.status = "assigned"

    return {"code": 200, "message": "复核员已分配", "data": _task_to_api(task)}


@router.post("/records", summary="提交复核意见")
async def submit_record(req: ReviewRecordSubmitRequest):
    """提交一条复核意见"""
    task_id = str(req.review_task_id)
    task = _find_task(task_id)
    if not task:
        return {"code": 404, "message": "任务不存在", "data": None}

    task = submit_review(
        task=task,
        reviewer_role=req.reviewer_role,
        sport_attribute=req.sport_attribute,
        sport_category=req.sport_category_override or "",
        sport_share=req.sport_share_override,
        reason=req.reason,
    )
    record = dict(task.a_result if req.reviewer_role == "A" else task.b_result)
    record["reviewer_name"] = req.reviewer_name

    # 存储记录
    _review_records.setdefault(task_id, {})[req.reviewer_role] = record

    return {"code": 200, "message": "复核意见已提交", "data": record}


@router.get("/tasks/{task_id}/consensus", summary="检查一致性")
async def get_consensus(task_id: str):
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

    is_consensus = records["A"]["sport_attribute"] == records["B"]["sport_attribute"]
    consensus = {
        "is_consensus": is_consensus,
        "detail": "双方意见一致" if is_consensus else "双方意见不一致，需仲裁",
        "records_submitted": ["A", "B"],
    }
    return {"code": 200, "data": consensus}


@router.post("/arbitrate", summary="提交仲裁")
async def do_arbitrate(req: ArbitrationRequest):
    """对分歧任务进行仲裁"""
    task_id = str(req.review_task_id)
    task = _find_task(task_id)
    if not task:
        return {"code": 404, "message": "任务不存在", "data": None}

    task = arbitrate(
        task=task,
        arbiter_name=req.arbiter_name,
        final_attribute=req.final_sport_attribute,
        final_category=req.final_sport_category or "",
        final_share=req.final_sport_share,
        reason=req.decision_reason,
    )
    task.status = "locked"
    arbitration_record = dict(task.arbiter_result)
    arbitration_record["status"] = "locked"
    _arbitration_records[task_id] = arbitration_record

    return {"code": 200, "message": "仲裁完成，任务已锁定", "data": arbitration_record}


@router.get("/stats", summary="复核统计")
async def get_stats(batch_id: int = Query(None)):
    """获取复核工作统计"""
    tasks = _review_tasks
    if batch_id is not None:
        tasks = [task for task in tasks if task.batch_id == str(batch_id)]
    stats = _stats_to_api(tasks)
    return {"code": 200, "data": stats}
