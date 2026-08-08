"""数据预处理路由 - Excel上传、数据清洗、数据集预览&导出、NLP预处理"""
from fastapi import APIRouter, UploadFile, File, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from models.database import get_db
from models.tables import DataSource
from models.schemas import PreprocessRequest
from utils.file_parser import parse_uploaded_bytes, preview_dataframe, get_dataframe_info, detect_columns
from utils.data_cleaner import clean_dataframe, standardize_columns
from services.nlp_preprocess import (
    batch_preprocess_enterprises, get_preprocess_stats, preprocess_enterprise,
)
import pandas as pd
import io
import json
import numpy as np
import hashlib

router = APIRouter()

_uploaded_data: dict = {}
_preprocess_results: dict = {}


def convert_numpy_types(obj):
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    else:
        return obj


@router.post("/upload", summary="上传Excel/CSV文件")
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """上传企业数据文件（Excel/CSV）"""
    content = await file.read()
    filename = file.filename

    try:
        df = parse_uploaded_bytes(content, filename)
    except Exception as e:
        return {"code": 400, "message": f"文件解析失败: {str(e)}", "data": None}

    df = standardize_columns(df)
    info = get_dataframe_info(df)

    ds = DataSource(filename=filename, file_type=filename.split(".")[-1], row_count=len(df), status="uploaded")
    db.add(ds)
    db.commit()
    db.refresh(ds)

    _uploaded_data[ds.id] = convert_numpy_types(df.to_dict(orient="records"))

    # 自动创建批次记录
    file_hash = hashlib.sha256(content).hexdigest()[:16]
    from api.system import register_batch
    batch = register_batch(
        data_mode="formal",
        file_name=filename,
        file_hash=file_hash,
        total_rows=len(df),
        operator_name="system",
    )

    return {
        "code": 200,
        "message": "文件上传成功",
        "data": {
            "file_id": ds.id,
            "filename": filename,
            "file_type": filename.split(".")[-1],
            "row_count": len(df),
            "columns": df.columns.tolist(),
            "info": info,
            "batch_number": batch["batch_number"],
            "batch_id": batch["id"],
            "file_hash": file_hash,
            "data_mode": "formal",
        },
    }


@router.get("/preview/{file_id}", summary="数据预览")
async def preview_data(file_id: int, page: int = Query(1), page_size: int = Query(20)):
    """分页预览数据集"""
    records = _uploaded_data.get(file_id, [])
    if not records:
        return {"code": 404, "message": "数据不存在，请先上传文件", "data": None}

    total = len(records)
    start = (page - 1) * page_size
    end = start + page_size
    page_data = records[start:end]

    return {
        "code": 200,
        "data": {"total": total, "page": page, "page_size": page_size, "records": page_data},
    }


@router.post("/clean/{file_id}", summary="数据清洗")
async def clean_data(file_id: int, req: PreprocessRequest, db: Session = Depends(get_db)):
    """执行数据清洗"""
    try:
        records = _uploaded_data.get(file_id, [])
        if not records:
            return {"code": 404, "message": "数据不存在", "data": None}

        df = pd.DataFrame(records)
        clean_rules = req.clean_rules or {}

        df = clean_dataframe(
            df,
            drop_duplicates=clean_rules.get("drop_duplicates", True),
            fill_na_strategy=clean_rules.get("fill_na_strategy", "zero"),
            drop_null_rows=clean_rules.get("drop_null_rows", False),
            column_mapping=clean_rules.get("column_mapping"),
        )

        info = get_dataframe_info(df)
        _uploaded_data[file_id] = convert_numpy_types(df.to_dict(orient="records"))

        ds = db.query(DataSource).filter(DataSource.id == file_id).first()
        if ds:
            ds.status = "cleaned"
            ds.row_count = len(df)
            db.commit()

        return {
            "code": 200,
            "message": "数据清洗完成",
            "data": {"file_id": file_id, "row_count": len(df), "info": info},
        }
    except Exception as e:
        return {"code": 500, "message": f"数据清洗失败: {str(e)}", "data": None}


@router.get("/export/{file_id}", summary="导出数据集")
async def export_data(file_id: int, format: str = Query("csv")):
    """导出处理后的数据集为CSV"""
    records = _uploaded_data.get(file_id, [])
    if not records:
        return {"code": 404, "message": "数据不存在", "data": None}

    df = pd.DataFrame(records)
    if format == "csv":
        stream = io.StringIO()
        df.to_csv(stream, index=False, encoding="utf-8-sig")
        stream.seek(0)
        return StreamingResponse(
            iter([stream.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=data_{file_id}.csv"},
        )
    elif format == "json":
        return {"code": 200, "data": records}
    return {"code": 400, "message": "不支持导出格式"}


@router.post("/preprocess/{file_id}", summary="NLP预处理")
async def nlp_preprocess(file_id: int):
    """对已上传数据执行中文分词、关键词提取、体育业务标签标注"""
    try:
        records = _uploaded_data.get(file_id, [])
        if not records:
            return {"code": 404, "message": "数据不存在，请先上传文件", "data": None}

        df = pd.DataFrame(records)

        col_map = detect_columns(df)
        business_col = col_map.get("business", df.columns[3])
        code_col = col_map.get("code", df.columns[2])
        name_col = col_map.get("name", df.columns[1])

        texts = df[business_col].fillna("").astype(str).tolist()
        codes = df[code_col].tolist() if code_col else None
        names = df[name_col].tolist() if name_col else None

        results = batch_preprocess_enterprises(texts, codes, names)
        stats = get_preprocess_stats(results)

        df["_tokens"] = [r["tokens"] for r in results]
        df["_keywords"] = [r["keywords"] for r in results]
        df["_sport_keywords"] = [r["sport_keywords"] for r in results]
        df["_is_sport"] = [r["is_sport"] for r in results]
        df["_sport_category"] = [r["sport_category"] for r in results]
        df["_confidence"] = [r["confidence"] for r in results]

        _preprocess_results[file_id] = {
            "results": results,
            "stats": stats,
            "records": convert_numpy_types(df.to_dict(orient="records")),
        }
        _uploaded_data[file_id] = convert_numpy_types(df.to_dict(orient="records"))

        return {
            "code": 200,
            "message": "NLP预处理完成",
            "data": {
                "file_id": file_id,
                "total_rows": len(df),
                "stats": stats,
                "sample_results": results[:5],
            },
        }
    except Exception as e:
        return {"code": 500, "message": f"NLP预处理失败: {str(e)}", "data": None}


@router.get("/preprocess-result/{file_id}", summary="预处理结果统计")
async def get_preprocess_result(file_id: int):
    """获取NLP预处理统计结果和标签分布"""
    cached = _preprocess_results.get(file_id, {})
    if not cached:
        return {"code": 404, "message": "预处理结果不存在，请先执行预处理", "data": None}

    return {
        "code": 200,
        "data": {
            "file_id": file_id,
            "stats": cached["stats"],
        },
    }


@router.get("/preprocess-sport/{file_id}", summary="体育企业明细")
async def get_sport_enterprises(
    file_id: int,
    category: str = Query("", description="按业态筛选"),
    page: int = Query(1),
    page_size: int = Query(20),
):
    """分页获取识别出的体育业务企业"""
    cached = _preprocess_results.get(file_id, {})
    if not cached:
        return {"code": 404, "message": "预处理结果不存在", "data": None}

    records = cached.get("records", [])
    sport_records = [r for r in records if r.get("_is_sport")]
    if category:
        sport_records = [r for r in sport_records if r.get("_sport_category") == category]

    total = len(sport_records)
    start = (page - 1) * page_size
    end = start + page_size

    return {
        "code": 200,
        "data": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "records": sport_records[start:end],
        },
    }


@router.get("/export-sport/{file_id}", summary="导出体育企业子集")
async def export_sport_data(file_id: int, format: str = Query("csv")):
    """导出识别出的体育企业数据"""
    cached = _preprocess_results.get(file_id, {})
    if not cached:
        return {"code": 404, "message": "预处理结果不存在，请先执行NLP预处理", "data": None}

    records = cached.get("records", [])
    sport_records = [r for r in records if r.get("_is_sport")]

    if format == "csv":
        df = pd.DataFrame(sport_records)
        stream = io.StringIO()
        df.to_csv(stream, index=False, encoding="utf-8-sig")
        stream.seek(0)
        return StreamingResponse(
            iter([stream.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=sport_enterprises_{file_id}.csv"},
        )
    elif format == "json":
        return {"code": 200, "data": sport_records}
    return {"code": 400, "message": "不支持导出格式"}


@router.get("/export-features/{file_id}", summary="导出特征数据集")
async def export_features(file_id: int, format: str = Query("csv")):
    """导出体育业务特征指标数据集"""
    cached = _preprocess_results.get(file_id, {})
    if not cached:
        return {"code": 404, "message": "预处理结果不存在", "data": None}

    records = cached.get("records", [])
    features = []
    for r in records:
        feat = r.get("features", {})
        features.append({
            "name": r.get("详细名称", ""),
            "credit_code": r.get("统一社会信用代码", ""),
            "industry_code": r.get("行业代码", ""),
            "is_sport": r.get("_is_sport", False),
            "sport_category": r.get("_sport_category", ""),
            "confidence": r.get("_confidence", 0),
            "text_length": feat.get("text_length", 0),
            "token_count": feat.get("token_count", 0),
            "keyword_count": feat.get("keyword_count", 0),
            "sport_keyword_count": feat.get("sport_keyword_count", 0),
            "sport_category_count": feat.get("sport_category_count", 0),
            "name_has_sport": feat.get("name_has_sport", False),
        })

    if format == "csv":
        df = pd.DataFrame(features)
        stream = io.StringIO()
        df.to_csv(stream, index=False, encoding="utf-8-sig")
        stream.seek(0)
        return StreamingResponse(
            iter([stream.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=features_{file_id}.csv"},
        )
    elif format == "json":
        return {"code": 200, "data": features}
    return {"code": 400, "message": "不支持导出格式"}
