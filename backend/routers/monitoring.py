"""Monitoring overview and risk-event API."""

from typing import Optional

from fastapi import APIRouter, Query

from routers.chart_data import get_dashboard_data
from services.monitoring_service import build_monitoring_snapshot

router = APIRouter()


async def get_monitoring_snapshot(file_id: Optional[int]):
    response = await get_dashboard_data(file_id)
    mode = "demo" if response.get("note") else "real"
    return build_monitoring_snapshot(response.get("data") or {}, mode=mode)


@router.get("/overview", summary="获取统计监测驾驶舱快照")
async def overview(file_id: Optional[int] = Query(None)):
    return {
        "code": 200,
        "message": "获取监测快照成功",
        "data": await get_monitoring_snapshot(file_id),
    }


@router.get("/risks", summary="获取风险事件")
async def risks(
    file_id: Optional[int] = Query(None),
    level: Optional[str] = Query(None),
    risk_type: Optional[str] = Query(None),
):
    items = (await get_monitoring_snapshot(file_id))["risks"]
    if level:
        items = [item for item in items if item["level"] == level]
    if risk_type:
        items = [item for item in items if item["type"] == risk_type]
    return {
        "code": 200,
        "message": "获取风险事件成功",
        "data": {"items": items, "total": len(items)},
    }


@router.get("/risks/{risk_id}", summary="获取风险证据")
async def risk_detail(risk_id: str, file_id: Optional[int] = Query(None)):
    item = next(
        (
            risk
            for risk in (await get_monitoring_snapshot(file_id))["risks"]
            if risk["id"] == risk_id
        ),
        None,
    )
    if not item:
        return {"code": 404, "message": "风险事件不存在", "data": None}
    return {"code": 200, "message": "获取风险详情成功", "data": item}
