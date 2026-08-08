"""系统管理 API — 批次管理 / 版本管理"""
from fastapi import APIRouter, Query
from datetime import datetime
import hashlib

router = APIRouter()

# 内存存储
_batches: list = []
_operation_logs: list = []
_next_batch_id = 1


def _hash_file(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()[:16]


def _generate_batch_number() -> str:
    today = datetime.now().strftime("%Y%m%d")
    return f"BATCH-{today}-{_next_batch_id:03d}"


@router.get("/batches", summary="批次列表")
async def list_batches(
    status: str = Query("", description="筛选状态"),
    data_mode: str = Query("", description="筛选模式: formal/demo"),
):
    """获取所有数据批次"""
    batches = list(_batches)
    if status:
        batches = [b for b in batches if b.get("status") == status]
    if data_mode:
        batches = [b for b in batches if b.get("data_mode") == data_mode]
    return {"code": 200, "data": {"batches": batches, "total": len(batches)}}


@router.get("/batches/{batch_id}", summary="批次详情")
async def batch_detail(batch_id: int):
    """获取单个批次的详细信息"""
    batch = next((b for b in _batches if b.get("id") == batch_id), None)
    if not batch:
        return {"code": 404, "message": "批次不存在", "data": None}
    return {"code": 200, "data": batch}


@router.post("/batches", summary="创建批次")
async def create_batch(data: dict):
    """手动创建数据批次"""
    global _next_batch_id
    batch_number = _generate_batch_number()

    batch = {
        "id": _next_batch_id,
        "batch_number": batch_number,
        "data_mode": data.get("data_mode", "formal"),
        "data_mode_label": "正式数据" if data.get("data_mode") != "demo" else "演示数据",
        "data_version": data.get("data_version", "v1.0"),
        "model_version": data.get("model_version", "v2.1.0"),
        "dictionary_version": data.get("dictionary_version", "DICT-20260801"),
        "code_map_version": data.get("code_map_version", "CODE-2025"),
        "share_model_version": data.get("share_model_version", ""),
        "file_hash": data.get("file_hash", ""),
        "file_name": data.get("file_name", ""),
        "total_rows": data.get("total_rows", 0),
        "sport_count": data.get("sport_count", 0),
        "operator_name": data.get("operator_name", ""),
        "status": "completed",
        "status_label": "已完成",
        "start_time": data.get("start_time", datetime.now().isoformat()),
        "end_time": datetime.now().isoformat(),
        "created_at": datetime.now().isoformat(),
    }
    _batches.append(batch)
    _next_batch_id += 1

    return {"code": 200, "message": f"批次 {batch_number} 已创建", "data": batch}


@router.post("/batches/{batch_id}/lock", summary="锁定批次")
async def lock_batch(batch_id: int):
    """锁定批次，防止修改"""
    batch = next((b for b in _batches if b.get("id") == batch_id), None)
    if not batch:
        return {"code": 404, "message": "批次不存在", "data": None}

    batch["status"] = "locked"
    batch["status_label"] = "已锁定"
    _log_operation("LOCK", "batch", batch_id, {"action": "lock"})

    return {"code": 200, "message": "批次已锁定", "data": batch}


@router.get("/batches/compare", summary="批次对比")
async def compare_batches(
    batch_a: int = Query(..., description="批次A ID"),
    batch_b: int = Query(..., description="批次B ID"),
):
    """对比两个批次的差异"""
    a = next((b for b in _batches if b.get("id") == batch_a), None)
    b = next((b for b in _batches if b.get("id") == batch_b), None)

    if not a or not b:
        return {"code": 404, "message": "批次不存在", "data": None}

    return {
        "code": 200,
        "data": {
            "batch_a": a,
            "batch_b": b,
            "diff": {
                "total_rows_diff": (b.get("total_rows", 0) - a.get("total_rows", 0)),
                "sport_count_diff": (b.get("sport_count", 0) - a.get("sport_count", 0)),
            },
        },
    }


@router.get("/logs", summary="操作日志")
async def list_logs(
    action: str = Query("", description="操作类型"),
    limit: int = Query(50, description="返回条数"),
):
    """获取操作审计日志"""
    logs = list(_operation_logs)
    if action:
        logs = [l for l in logs if l.get("action") == action]
    logs = logs[-limit:]
    return {"code": 200, "data": {"logs": list(reversed(logs)), "total": len(_operation_logs)}}


def _log_operation(action: str, target_type: str, target_id: int, detail: dict = None):
    """记录操作日志"""
    _operation_logs.append({
        "id": len(_operation_logs) + 1,
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "detail": detail or {},
        "created_at": datetime.now().isoformat(),
    })


# 注册一个全局函数供其他模块使用
def register_batch(
    data_mode: str = "formal",
    file_name: str = "",
    file_hash: str = "",
    total_rows: int = 0,
    sport_count: int = 0,
    operator_name: str = "",
) -> dict:
    """外部模块创建批次的便捷函数"""
    global _next_batch_id
    batch_number = _generate_batch_number()

    batch = {
        "id": _next_batch_id,
        "batch_number": batch_number,
        "data_mode": data_mode,
        "data_mode_label": "正式数据" if data_mode == "formal" else "演示数据",
        "data_version": "v1.0",
        "model_version": "v2.1.0",
        "dictionary_version": "DICT-20260801",
        "file_hash": file_hash,
        "file_name": file_name,
        "total_rows": total_rows,
        "sport_count": sport_count,
        "operator_name": operator_name,
        "status": "completed",
        "status_label": "已完成",
        "start_time": datetime.now().isoformat(),
        "end_time": datetime.now().isoformat(),
        "created_at": datetime.now().isoformat(),
    }
    _batches.append(batch)
    _next_batch_id += 1
    return batch
