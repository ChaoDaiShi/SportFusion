"""文件解析工具 - 支持 Excel/CSV 文件读取"""
import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any


def convert_numpy_types(value):
    """将numpy类型转换为Python原生类型"""
    if isinstance(value, np.integer):
        return int(value)
    elif isinstance(value, np.floating):
        return float(value)
    elif isinstance(value, np.ndarray):
        return value.tolist()
    elif pd.isna(value):
        return ""
    return value


def parse_file(file_path: str, file_type: Optional[str] = None) -> pd.DataFrame:
    """根据文件类型解析 Excel/CSV 文件"""
    if file_path.endswith(".csv") or file_type == "csv":
        return pd.read_csv(file_path, encoding="utf-8-sig")
    elif file_path.endswith((".xlsx", ".xls")) or file_type in ("xlsx", "xls"):
        return pd.read_excel(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {file_path}")


def parse_uploaded_bytes(content: bytes, filename: str) -> pd.DataFrame:
    """从上传的字节流解析文件"""
    if filename.endswith(".csv"):
        import io
        return pd.read_csv(io.BytesIO(content), encoding="utf-8-sig")
    elif filename.endswith((".xlsx", ".xls")):
        import io
        return pd.read_excel(io.BytesIO(content))
    else:
        raise ValueError(f"不支持的文件格式: {filename}")


def preview_dataframe(df: pd.DataFrame, rows: int = 50) -> List[Dict[str, Any]]:
    """将DataFrame转换为可JSON序列化的预览数据"""
    preview_df = df.head(rows).fillna("")
    records = preview_df.to_dict(orient="records")
    return [{k: convert_numpy_types(v) for k, v in record.items()} for record in records]


def get_dataframe_info(df: pd.DataFrame) -> dict:
    """获取数据集基本信息"""
    null_counts = df.isnull().sum().to_dict()
    null_counts = {k: convert_numpy_types(v) for k, v in null_counts.items()}
    memory_usage = df.memory_usage(deep=True).sum()
    return {
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": df.columns.tolist(),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "null_counts": null_counts,
        "memory_usage": convert_numpy_types(memory_usage),
    }


def detect_columns(df: pd.DataFrame) -> dict:
    """自动检测企业数据列名映射（支持中英文列名）

    返回: {"credit_code": str, "name": str, "code": str, "business": str}
    """
    cols = df.columns.tolist()
    result = {}
    for col in cols:
        col_str = str(col).strip()
        if col_str == "统一社会信用代码":
            result["credit_code"] = col
        elif col_str in ("详细名称", "企业名称"):
            result["name"] = col
        elif col_str == "行业代码":
            result["code"] = col
        elif col_str in ("主要业务活动", "主营业务"):
            result["business"] = col
    # fallback by position
    if "credit_code" not in result and len(cols) > 0:
        result["credit_code"] = cols[0]
    if "name" not in result and len(cols) > 1:
        result["name"] = cols[1]
    if "code" not in result and len(cols) > 2:
        result["code"] = cols[2]
    if "business" not in result and len(cols) > 3:
        result["business"] = cols[3]
    return result
