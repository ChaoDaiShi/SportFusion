"""SportShare 比重测算 API — 单企业/批量估计 + 统计 + 人工校准"""
from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from models.database import get_db
from models.schemas import (
    SportShareEstimateRequest, SportShareResultOut,
    SportShareManualAdjustRequest, SportShareStatsOut,
)
from services.sport_share_service import (
    estimate_sport_share, batch_estimate_share, get_share_stats,
    apply_manual_adjustment,
)
from services.sport_recognition import recognize_sport_business

router = APIRouter()

# 内存缓存（后续可迁移到数据库）
_share_results_cache: dict = {}


@router.post("/estimate", summary="单企业比重估计")
async def estimate_single(req: SportShareEstimateRequest):
    """
    对单企业进行 SportShare 比重估计。
    可传入已有的识别结果（recognition_result），或在服务端重新识别。
    """
    # 使用已有识别结果或重新识别
    if req.recognition_result:
        rec_result = req.recognition_result
    else:
        # 需要 business_text 来重新识别（通过查询预处理缓存）
        return {
            "code": 400,
            "message": "请提供 business_text 字段或已有的 recognition_result",
            "data": None,
        }

    share_result = estimate_sport_share(rec_result)
    share_result["enterprise_id"] = req.enterprise_id
    share_result["credit_code"] = req.credit_code or rec_result.get("credit_code", "")

    return {"code": 200, "message": "比重估计完成", "data": share_result}


@router.post("/batch-estimate", summary="批量比重估计")
async def estimate_batch(data: list):
    """
    批量比重估计。
    输入：识别结果列表（每项为 recognize_sport_business() 的输出）
    """
    if not data:
        return {"code": 400, "message": "数据不能为空", "data": None}

    results = batch_estimate_share(data)
    stats = get_share_stats(results)

    # 缓存（按时间戳简单缓存）
    import time
    cache_key = str(int(time.time()))
    _share_results_cache[cache_key] = {"results": results, "stats": stats}

    return {
        "code": 200,
        "message": f"批量比重估计完成，共 {len(results)} 家企业",
        "data": {
            "cache_key": cache_key,
            "results": results,
            "stats": stats,
        },
    }


@router.get("/result/{enterprise_id}", summary="查询企业比重结果")
async def get_share_result(enterprise_id: int):
    """根据企业ID查询 SportShare 结果"""
    # 遍历缓存查找
    for cache_key, cache_data in _share_results_cache.items():
        for r in cache_data.get("results", []):
            if r.get("enterprise_id") == enterprise_id:
                return {"code": 200, "data": r}

    return {"code": 404, "message": "未找到该企业的比重结果，请先执行比重估计", "data": None}


@router.get("/stats", summary="比重统计")
async def get_stats(cache_key: str = Query("", description="缓存键（来自batch-estimate返回值）")):
    """获取比重估计的统计信息"""
    if cache_key and cache_key in _share_results_cache:
        stats = _share_results_cache[cache_key]["stats"]
        return {"code": 200, "data": stats}

    # 返回最近一次缓存的数据
    if _share_results_cache:
        latest_key = list(_share_results_cache.keys())[-1]
        stats = _share_results_cache[latest_key]["stats"]
        return {"code": 200, "data": stats}

    return {"code": 404, "message": "暂无比重统计数据，请先执行比重估计", "data": None}


@router.post("/manual-adjust", summary="人工校准比重")
async def manual_adjust(req: SportShareManualAdjustRequest):
    """提交人工校准后的比重值"""
    # 查找原始结果
    found = None
    for cache_key, cache_data in _share_results_cache.items():
        for i, r in enumerate(cache_data.get("results", [])):
            if r.get("enterprise_id") == req.share_result_id or i == req.share_result_id:
                found = r
                break
        if found:
            break

    if not found:
        return {"code": 404, "message": "未找到该比重结果", "data": None}

    adjusted = apply_manual_adjustment(
        found, req.manual_share, req.adjusted_by, req.reason
    )

    return {"code": 200, "message": "人工校准已记录", "data": adjusted}


@router.get("/bands", summary="比重档位定义")
async def get_bands():
    """获取比重档位定义，供前端使用"""
    from services.sport_share_service import SHARE_BANDS
    return {"code": 200, "data": SHARE_BANDS}
