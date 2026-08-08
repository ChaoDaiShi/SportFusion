"""产业规模测算 API"""
from fastapi import APIRouter, Query
from services.scale_measure_service import (
    batch_calculate_scale, aggregate_regional_scale,
    compare_methods, calculate_category_scale, get_measurement_type_summary,
    SCALE_FIELD_CONFIG,
)
from services.sport_share_service import batch_estimate_share

router = APIRouter()

# 内存缓存
_scale_cache: dict = {}


@router.get("/fields", summary="规模字段定义")
async def get_scale_fields():
    """获取支持的规模字段及其优先级"""
    fields = []
    for key, cfg in sorted(SCALE_FIELD_CONFIG.items(), key=lambda x: x[1]["priority"]):
        fields.append({
            "key": key, "label": cfg["label"], "unit": cfg["unit"],
            "priority": cfg["priority"], "measurement_type": cfg["measurement_type"],
            "measurement_label": cfg["measurement_label"], "description": cfg["description"],
        })
    return {"code": 200, "data": fields}


@router.post("/calculate", summary="触发规模测算")
async def calculate(data: dict):
    """
    执行产业规模测算。
    输入：{
        "enterprises": [...],          # 企业数据列表
        "recognition_results": [...],  # 识别结果列表（可选，如不提供则使用share_results）
        "share_results": [...],        # 比重结果列表
        "preferred_field": "auto"      # 优先使用的规模字段
    }
    """
    enterprises = data.get("enterprises", [])
    share_results = data.get("share_results", [])
    recognition_results = data.get("recognition_results", [])

    if not enterprises:
        return {"code": 400, "message": "企业数据不能为空", "data": None}

    # 如无比重结果，先执行比重估计
    if not share_results and recognition_results:
        share_results = batch_estimate_share(recognition_results)
        share_results_processed = share_results
    elif share_results:
        share_results_processed = share_results
    else:
        return {"code": 400, "message": "请提供 share_results 或 recognition_results", "data": None}

    preferred_field = data.get("preferred_field", "auto")

    # 规模测算
    scale_results = batch_calculate_scale(enterprises, share_results_processed, preferred_field)

    # 汇总
    regional = aggregate_regional_scale(enterprises, share_results_processed, scale_results)
    comparison = compare_methods(enterprises, scale_results, share_results_processed)
    category = calculate_category_scale(scale_results, share_results_processed)
    type_summary = get_measurement_type_summary(scale_results)

    total_scale = sum(r.get("sport_scale", 0) for r in scale_results)

    import time
    cache_key = str(int(time.time()))
    _scale_cache[cache_key] = {
        "scale_results": scale_results,
        "regional": regional,
        "comparison": comparison,
        "category": category,
        "type_summary": type_summary,
        "total_scale": round(total_scale, 2),
    }

    return {
        "code": 200,
        "message": f"规模测算完成，共 {len(scale_results)} 家企业",
        "data": {
            "cache_key": cache_key,
            "total_scale": round(total_scale, 2),
            "enterprise_count": len(scale_results),
            "type_summary": type_summary,
            "category": category,
            "comparison": comparison,
        },
    }


@router.get("/summary", summary="规模总览")
async def get_summary(cache_key: str = Query("", description="缓存键")):
    """获取规模测算总览"""
    cached = _get_cached(cache_key)
    if not cached:
        return {"code": 404, "message": "暂未执行规模测算", "data": None}

    scale_results = cached["scale_results"]
    total_scale = sum(r.get("sport_scale", 0) for r in scale_results)

    # 估算区间（±15%）
    lower = round(total_scale * 0.85, 2)
    upper = round(total_scale * 1.15, 2)

    return {
        "code": 200,
        "data": {
            "total_estimated_scale": round(total_scale, 2),
            "lower_bound": lower,
            "upper_bound": upper,
            "enterprise_count": len(scale_results),
            "type_summary": cached.get("type_summary"),
            "comparison": cached.get("comparison"),
            "category": cached.get("category"),
        },
    }


@router.get("/category", summary="分业态规模")
async def get_category_scale(cache_key: str = Query("")):
    """获取九类业态的规模分布"""
    cached = _get_cached(cache_key)
    if not cached:
        return {"code": 404, "message": "暂未执行规模测算", "data": None}

    return {"code": 200, "data": cached.get("category", [])}


@router.get("/regional", summary="区域规模")
async def get_regional_scale(
    cache_key: str = Query(""),
    region: str = Query("", description="筛选特定区域"),
):
    """获取各区域体育产业规模"""
    cached = _get_cached(cache_key)
    if not cached:
        return {"code": 404, "message": "暂未执行规模测算", "data": None}

    regional = cached.get("regional", [])
    if region:
        regional = [r for r in regional if region in r.get("region", "")]

    return {"code": 200, "data": regional}


@router.get("/comparison", summary="方法对比")
async def get_comparison(cache_key: str = Query("")):
    """获取传统代码法与SportFusion的对比"""
    cached = _get_cached(cache_key)
    if not cached:
        return {"code": 404, "message": "暂未执行规模测算", "data": None}

    return {"code": 200, "data": cached.get("comparison")}


def _get_cached(cache_key: str = "") -> dict:
    """获取缓存的规模测算结果"""
    if cache_key and cache_key in _scale_cache:
        return _scale_cache[cache_key]
    if _scale_cache:
        return _scale_cache[list(_scale_cache.keys())[-1]]
    return {}
