"""数据清洗工具 - 数据标准化、去重、缺失值处理"""
import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any


def clean_dataframe(
    df: pd.DataFrame,
    drop_duplicates: bool = True,
    fill_na_strategy: str = "zero",
    drop_null_rows: bool = False,
    column_mapping: Optional[Dict[str, str]] = None,
) -> pd.DataFrame:
    """
    基础数据清洗流程
    - drop_duplicates: 去重
    - fill_na_strategy: 缺失值填充策略 (zero / mean / median / mode)
    - drop_null_rows: 是否删除含空值的行
    - column_mapping: 列名映射
    """
    df = df.copy()

    # 列名映射
    if column_mapping:
        df.rename(columns=column_mapping, inplace=True)

    # 去重
    if drop_duplicates:
        df = df.drop_duplicates()

    # 缺失值处理
    if drop_null_rows:
        df = df.dropna()
    else:
        for col in df.columns:
            if df[col].dtype in (np.float64, np.int64):
                if fill_na_strategy == "zero":
                    df[col] = df[col].fillna(0)
                elif fill_na_strategy == "mean":
                    df[col] = df[col].fillna(df[col].mean())
                elif fill_na_strategy == "median":
                    df[col] = df[col].fillna(df[col].median())
            else:
                df[col] = df[col].fillna("")

    # 去除首尾空白
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].astype(str).str.strip()

    return df


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """标准化列名（去除空格、统一命名规范）"""
    df = df.copy()
    df.columns = [col.strip().replace(" ", "_").replace("（", "(").replace("）", ")") for col in df.columns]
    return df


def detect_outliers(df: pd.DataFrame, threshold: float = 3.0) -> dict:
    """基于Z-score检测异常值"""
    outliers = {}
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        z_scores = np.abs((df[col] - df[col].mean()) / df[col].std())
        outlier_indices = df[z_scores > threshold].index.tolist()
        if outlier_indices:
            outliers[col] = len(outlier_indices)
    return outliers
