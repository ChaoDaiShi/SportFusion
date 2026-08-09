"""
动态名录 API — Phase 4: finalized enterprise directory (read-only).

Only confirmed/locked/finalized enterprises are included.
Pending and disputed enterprises are excluded.
"""

from fastapi import APIRouter, Query
from fastapi.responses import Response
from services.batch_service import get_batch_store
from services.directory_service import DirectoryService
from services.export_service import export_to_xlsx_bytes

router = APIRouter()


@router.get("/", summary="动态名录")
async def list_directory(
    batch_id: str | None = Query(None, description="批次ID"),
    region: str | None = Query(None, description="区域筛选"),
    category: str | None = Query(None, description="业态筛选"),
    crossover: bool | None = Query(None, description="跨界筛选"),
    priority: str | None = Query(None, description="复核优先级"),
    review_status: str | None = Query(None, description="复核状态"),
):
    """获取动态名录 — 仅包含 finalized 企业。"""
    svc = DirectoryService()
    entries = svc.get_directory(
        batch_id=batch_id, region=region, category=category,
        crossover=crossover, priority=priority, review_status=review_status,
    )
    return {
        "code": 200,
        "status": "success",
        "message": f"名录查询完成，共 {len(entries)} 家",
        "data": {
            "total": len(entries),
            "entries": [
                {
                    "enterprise_id": e.enterprise_id,
                    "credit_code": e.credit_code,
                    "enterprise_name": e.enterprise_name,
                    "region": e.region,
                    "industry_code": e.industry_code,
                    "sport_score": e.sport_score,
                    "evidence_relation": e.evidence_relation,
                    "model_share": e.model_share,
                    "fallback_share": e.fallback_share,
                    "manual_share": e.manual_share,
                    "effective_share": e.effective_share,
                    "share_source": e.share_source,
                    "sport_category": e.sport_category,
                    "crossover_type": e.crossover_type,
                    "review_status": e.review_status,
                    "priority": e.priority,
                    "batch_id": e.batch_id,
                    "is_finalized": e.is_finalized,
                    "provenance": e.provenance,
                }
                for e in entries
            ],
        },
    }


@router.get("/{enterprise_id}", summary="名录企业详情")
async def get_entry(enterprise_id: str, batch_id: str | None = Query(None)):
    """获取名录中单个企业详情"""
    svc = DirectoryService()
    entry = svc.get_entry(enterprise_id, batch_id=batch_id)
    if entry is None:
        return {"code": 404, "status": "not_found", "message": "企业未在名录中", "data": None}
    return {"code": 200, "status": "success", "data": {
        "enterprise_id": entry.enterprise_id,
        "credit_code": entry.credit_code,
        "enterprise_name": entry.enterprise_name,
        "region": entry.region,
        "sport_score": entry.sport_score,
        "evidence_relation": entry.evidence_relation,
        "model_share": entry.model_share,
        "fallback_share": entry.fallback_share,
        "manual_share": entry.manual_share,
        "effective_share": entry.effective_share,
        "share_source": entry.share_source,
        "sport_category": entry.sport_category,
        "crossover_type": entry.crossover_type,
        "review_status": entry.review_status,
        "priority": entry.priority,
        "batch_id": entry.batch_id,
        "provenance": entry.provenance,
    }}


@router.get("/export/xlsx", summary="导出动态名录XLSX")
async def export_directory_xlsx(batch_id: str = Query(..., description="批次ID")):
    """导出名录为 XLSX（锁定批次为 final，未锁定为 draft）"""
    store = get_batch_store()
    batch = store.get_batch(batch_id)
    if batch is None:
        return {"code": 404, "status": "not_found", "message": "批次不存在"}

    try:
        xlsx_bytes = export_to_xlsx_bytes(batch_id, sheets=["directory", "candidate_enterprises", "sportshare_results", "provenance_manifest"])
        export_type = "final" if store.is_locked(batch_id) else "draft"
        filename = f"directory_{batch_id}_{export_type}.xlsx"
        return Response(
            content=xlsx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:  # noqa: BLE001 — API-level catch is intentional
        return {"code": 500, "status": "error", "message": f"导出失败: {e!s}"}
