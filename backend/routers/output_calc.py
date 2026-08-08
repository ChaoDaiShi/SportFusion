"""产值测算路由 - 企业体育营收占比计算、分业态区域产业规模批量测算"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from models.schemas import MeasureRequest, BatchMeasureRequest
from services.output_calc import batch_calculate, calculate_model_metrics

router = APIRouter()


class MetricsRequest(BaseModel):
    predicted: List[float]
    actual: List[float]


@router.post("/single", summary="单企业产值测算")
async def measure_single(req: MeasureRequest):
    """对单个企业进行体育产值测算"""
    result = batch_calculate(
        [{
            "enterprise_id": req.enterprise_id,
            "enterprise_name": req.enterprise_name,
            "region": req.region,
            "sport_category": req.sport_category,
            "total_revenue": req.total_revenue,
            "sport_revenue_ratio": req.sport_revenue_ratio,
        }]
    )
    return {
        "code": 200,
        "message": "测算完成",
        "data": result["results"][0] if result["results"] else None,
    }


@router.post("/batch", summary="批量产值测算")
async def measure_batch(req: BatchMeasureRequest):
    """批量企业体育产值测算，含区域和业态汇总"""
    items = [
        {
            "enterprise_id": item.enterprise_id,
            "enterprise_name": item.enterprise_name,
            "region": item.region,
            "sport_category": item.sport_category,
            "total_revenue": item.total_revenue,
            "sport_revenue_ratio": item.sport_revenue_ratio,
        }
        for item in req.items
    ]

    result = batch_calculate(items)

    return {
        "code": 200,
        "message": f"批量测算完成，共{len(items)}家企业",
        "data": result,
    }


@router.post("/metrics", summary="计算模型精度指标")
async def model_metrics(req: MetricsRequest):
    """计算预测值与实际值的MAE/RMSE/R²指标"""
    result = calculate_model_metrics(req.predicted, req.actual)
    return {"code": 200, "data": result}
