"""
SportShare API — Phase 3: model/fallback/manual pipeline.

Endpoints:
    POST /estimate       — single enterprise share estimation
    POST /batch-estimate — batch share estimation
    POST /manual-adjust  — manual override
    GET  /stats          — share statistics
    GET  /bands          — share band definitions
    GET  /evaluation     — model evaluation results
"""
from fastapi import APIRouter, Query
from models.schemas import SportShareEstimateRequest, SportShareManualAdjustRequest
from services.sportshare.estimator import batch_estimate, estimate_sport_share

router = APIRouter()

_share_cache: dict = {}


@router.post("/estimate", summary="单企业SportShare估计")
async def estimate_single(req: SportShareEstimateRequest):
    """
    统一 SportShare 估计：
    model (RF) > fallback (分层回退) > manual (人工核定)
    """
    enterprise = {
        "enterprise_id": req.enterprise_id,
        "credit_code": req.credit_code,
        "business_text": req.recognition_result.get("business_text", "") if req.recognition_result else "",
    }
    rec_result = req.recognition_result

    est = estimate_sport_share(
        enterprise=enterprise,
        recognition_result=rec_result,
    )

    return {
        "code": 200,
        "message": "SportShare估计完成",
        "data": {
            "enterprise_id": est.enterprise_id,
            "credit_code": est.credit_code,
            "enterprise_name": est.enterprise_name,
            "model_share": est.model_share,
            "fallback_share": est.fallback_share,
            "manual_share": est.manual_share,
            "effective_share": est.effective_share,
            "share_source": est.share_source,
            "lower_bound": est.lower_bound,
            "upper_bound": est.upper_bound,
            "sport_score": est.sport_score,
            "sport_category": est.sport_category,
            "code_type": est.code_type,
            "is_model_eligible": est.is_model_eligible,
            "metadata": est.metadata,
        },
    }


@router.post("/batch-estimate", summary="批量SportShare估计")
async def estimate_batch(data: list):
    """批量 SportShare 估计"""
    if not data:
        return {"code": 400, "message": "数据不能为空", "data": None}

    enterprises = []
    for item in data:
        rec = item.get("recognition_result", item)
        enterprises.append({
            "enterprise_id": item.get("enterprise_id", rec.get("enterprise_id", "")),
            "credit_code": item.get("credit_code", rec.get("credit_code", "")),
            "enterprise_name": item.get("enterprise_name", rec.get("enterprise_name", "")),
            "business_text": item.get("business_text", rec.get("business_text", "")),
            "industry_code": item.get("industry_code", rec.get("industry_code")),
        })

    recognition_results = [item.get("recognition_result", item) for item in data]
    estimates = batch_estimate(enterprises, recognition_results)

    results = []
    for est in estimates:
        results.append({
            "enterprise_id": est.enterprise_id,
            "credit_code": est.credit_code,
            "model_share": est.model_share,
            "fallback_share": est.fallback_share,
            "effective_share": est.effective_share,
            "share_source": est.share_source,
            "lower_bound": est.lower_bound,
            "upper_bound": est.upper_bound,
            "sport_score": est.sport_score,
            "is_model_eligible": est.is_model_eligible,
        })

    import time
    cache_key = str(int(time.time()))
    _share_cache[cache_key] = results

    return {
        "code": 200,
        "message": f"批量SportShare估计完成，共{len(results)}家",
        "data": {"cache_key": cache_key, "results": results},
    }


@router.post("/manual-adjust", summary="人工校准SportShare")
async def manual_adjust(req: SportShareManualAdjustRequest):
    """人工核定 SportShare 值"""
    enterprise = {"enterprise_id": req.share_result_id}
    est = estimate_sport_share(
        enterprise=enterprise,
        manual_share_override=req.manual_share,
    )
    return {
        "code": 200,
        "message": "人工校准已记录",
        "data": {
            "effective_share": est.effective_share,
            "share_source": est.share_source,
            "manual_share": est.manual_share,
        },
    }


@router.get("/stats", summary="SportShare统计")
async def get_stats(cache_key: str = Query("", description="缓存键")):
    """SportShare 统计"""
    data = _share_cache.get(cache_key, [])
    if not data:
        return {"code": 404, "message": "无数据", "data": None}

    n = len(data)
    shares = [r["effective_share"] for r in data]
    model_count = sum(1 for r in data if r["share_source"] == "model")
    fallback_count = sum(1 for r in data if r["share_source"] == "fallback")

    return {
        "code": 200,
        "data": {
            "total": n,
            "model_estimated": model_count,
            "fallback_estimated": fallback_count,
            "avg_share": round(sum(shares) / n, 4) if n > 0 else 0.0,
            "bands": _compute_bands(shares),
        },
    }


def _compute_bands(shares: list[float]) -> dict:
    bands = {"very_low": 0, "low": 0, "medium": 0, "high": 0, "very_high": 0}
    for s in shares:
        if s < 0.2: bands["very_low"] += 1
        elif s < 0.4: bands["low"] += 1
        elif s < 0.6: bands["medium"] += 1
        elif s < 0.8: bands["high"] += 1
        else: bands["very_high"] += 1
    return bands


@router.get("/bands", summary="SportShare档位定义")
async def get_bands():
    return {
        "code": 200,
        "data": [
            {"key": "very_low", "label": "极低", "range": "[0, 0.2)"},
            {"key": "low", "label": "低", "range": "[0.2, 0.4)"},
            {"key": "medium", "label": "中", "range": "[0.4, 0.6)"},
            {"key": "high", "label": "高", "range": "[0.6, 0.8)"},
            {"key": "very_high", "label": "极高", "range": "[0.8, 1.0]"},
        ],
    }
