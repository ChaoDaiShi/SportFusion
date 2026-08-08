"""企业识别路由 v2.0 — 单条/批量企业体育业务识别 + 业务边界 + 比重测算"""
from fastapi import APIRouter, Query
from models.schemas import BatchRecognitionRequest, RecognitionRequest
from services.output_calc import extract_region
from services.sport_recognition import (
    batch_recognize,
    batch_recognize_full,
    classify_business_line,
    get_recognition_stats,
    parse_business_lines,
    recognize_sport_business,
)

router = APIRouter()


@router.get("/categories", summary="获取体育业态分类定义")
async def get_categories():
    """返回体育业态分类及关键词定义（来自 text_tokenizer）"""
    from utils.text_tokenizer import SPORT_KEYWORDS_BY_CATEGORY
    return {
        "code": 200,
        "data": {
            cat: {"keywords": words[:8], "count": len(words)}
            for cat, words in SPORT_KEYWORDS_BY_CATEGORY.items()
        },
    }


@router.post("/single", summary="单条企业识别")
async def recognize_single(req: RecognitionRequest):
    """单企业体育业态识别 + 业务边界 + 比重测算"""
    result = recognize_sport_business(
        business_text=req.business_text,
        industry_code=req.industry_code,
        enterprise_name=req.enterprise_name,
    )
    result["enterprise_id"] = req.enterprise_id
    result["enterprise_name"] = req.enterprise_name

    return {"code": 200, "message": "识别完成", "data": result}


@router.post("/batch", summary="批量企业识别")
async def recognize_batch(req: BatchRecognitionRequest):
    """批量企业体育业态识别（保持兼容）"""
    enterprises = [
        {
            "enterprise_id": e.enterprise_id,
            "enterprise_name": e.enterprise_name,
            "business_text": e.business_text,
            "industry_code": e.industry_code,
            "_uid": e.uid,
        }
        for e in req.enterprises
    ]
    results = batch_recognize(enterprises)
    sport_count = sum(1 for r in results if r.get("sport_category") != "非体育")

    return {
        "code": 200,
        "message": f"批量识别完成，共{len(results)}家，体育相关{sport_count}家",
        "data": {"results": results, "total": len(results), "sport_count": sport_count},
    }


@router.post("/batch-full", summary="全量企业识别+比重测算")
async def recognize_batch_full(data: list):
    """
    全量批量识别（支持上传完整企业数据）
    每条: {"credit_code", "name", "industry_code", "business_text"}
    """
    results = batch_recognize_full(data)
    stats = get_recognition_stats(results)

    return {
        "code": 200,
        "message": f"全量识别完成，共{len(results)}家，体育相关{stats['sport_count']}家",
        "data": {
            "results": results,
            "stats": stats,
        },
    }


@router.get("/enterprise/{credit_code}", summary="单企业详细分析")
async def enterprise_detail(credit_code: str):
    """根据统一社会信用代码查询企业详细分析（需先上传数据）"""
    try:
        from routers.data_preprocess import _preprocess_results

        for file_id, cached in _preprocess_results.items():
            records = cached.get("records", [])
            for r in records:
                if r.get("统一社会信用代码") == credit_code:
                    detail = recognize_sport_business(
                        business_text=r.get("主要业务活动", ""),
                        industry_code=r.get("行业代码"),
                        enterprise_name=r.get("详细名称", ""),
                    )
                    region = extract_region(r.get("详细名称", ""))
                    detail["credit_code"] = credit_code
                    detail["enterprise_name"] = r.get("详细名称", "")
                    detail["region"] = region
                    detail["industry_code"] = r.get("行业代码")
                    return {"code": 200, "data": detail}

        return {"code": 404, "message": "未找到该企业数据", "data": None}
    except Exception as e:
        return {"code": 500, "message": f"查询企业详情失败: {e!s}", "data": None}


@router.get("/stats", summary="识别统计概览")
async def recognition_stats(file_id: int = Query(..., description="数据文件ID")):
    """获取某个已处理数据集的识别统计"""
    try:
        from routers.data_preprocess import _preprocess_results

        cached = _preprocess_results.get(file_id)
        if not cached:
            return {"code": 404, "message": "预处理数据不存在", "data": None}

        records = cached.get("records", [])
        enterprises = [
            {
                "credit_code": r.get("统一社会信用代码", ""),
                "name": r.get("详细名称", ""),
                "industry_code": r.get("行业代码"),
                "business_text": r.get("主要业务活动", ""),
            }
            for r in records
        ]

        results = batch_recognize_full(enterprises)
        stats = get_recognition_stats(results)

        region_dist = {}
        for ent in enterprises:
            region = extract_region(ent.get("name", ""))
            region_dist[region] = region_dist.get(region, 0) + 1

        stats["region_distribution"] = dict(
            sorted(region_dist.items(), key=lambda x: -x[1])[:20]
        )

        return {"code": 200, "data": stats}
    except Exception as e:
        return {"code": 500, "message": f"获取识别统计失败: {e!s}", "data": None}


@router.get("/business-lines", summary="业务线解析演示")
async def demo_business_lines(text: str = Query(..., description="业务活动文本")):
    """演示：将业务活动文本拆分为独立的业务线并分类"""
    lines = parse_business_lines(text)
    classified = [classify_business_line(line) for line in lines]

    return {
        "code": 200,
        "data": {
            "original_text": text,
            "total_lines": len(lines),
            "business_lines": lines,
            "classified": classified,
            "sport_lines": [c for c in classified if c["is_sport"]],
            "non_sport_lines": [c for c in classified if not c["is_sport"]],
        },
    }
