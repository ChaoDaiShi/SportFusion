"""
=============================================================================
  独立预处理流水线 — 体育产业企业微观数据标准化处理
  =============================================================================
  直接加载 data/ 目录下的 xlsx 数据文件，执行：
    1. 数据清洗（去重、缺失值处理、文本标准化）
    2. 分词 + 关键词提取（全部企业）
    3. 体育业务标签标注（文本匹配 + 行业代码辅助）
    4. 特征提取
    5. 导出标准化数据集 → data/processed/
=============================================================================
  用法：
    python run_preprocess.py                          # 处理默认文件
    python run_preprocess.py --input <path>           # 指定输入文件
    python run_preprocess.py --skip-clean             # 跳过清洗
    python run_preprocess.py --export-only results    # 导出摘要JSON
=============================================================================
"""
import sys
import os
import json
import argparse
import time
from pathlib import Path
from datetime import datetime

# 确保项目路径在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np

from utils.file_parser import parse_file, get_dataframe_info, preview_dataframe, detect_columns
from utils.data_cleaner import clean_dataframe, standardize_columns
from utils.text_tokenizer import get_sport_categories, get_sport_dict
from services.nlp_preprocess import (
    preprocess_enterprise,
    batch_preprocess_enterprises,
    get_preprocess_stats,
)


def find_data_file(data_dir: str = "../../data") -> str:
    """自动查找 data 目录下的 xlsx/csv 文件"""
    data_path = Path(data_dir)
    if not data_path.exists():
        raise FileNotFoundError(f"数据目录不存在: {data_dir}")

    for ext in ["*.xlsx", "*.xls", "*.csv"]:
        files = sorted(data_path.glob(ext))
        # 排除临时文件
        data_files = [f for f in files if not f.name.startswith("_") and not f.name.startswith("~")]
        if data_files:
            return str(data_files[0])

    raise FileNotFoundError(f"在 {data_dir} 中未找到数据文件（xlsx/xls/csv）")


def ensure_output_dir(output_dir: str = "../../data/processed"):
    """确保输出目录存在"""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    return output_dir


def load_and_clean(file_path: str, skip_clean: bool = False) -> pd.DataFrame:
    """加载并清洗数据"""
    print(f"\n{'='*60}")
    print(f"[1/5] 加载数据文件: {file_path}")
    print(f"{'='*60}")

    df = parse_file(file_path)
    print(f"  读取完成: {len(df)} 行 × {len(df.columns)} 列")
    print(f"  列名: {df.columns.tolist()}")

    # 统计信息
    info = get_dataframe_info(df)
    print(f"  内存占用: {info['memory_usage'] / 1024 / 1024:.2f} MB")

    if skip_clean:
        print("\n  跳过数据清洗...")
        return df

    print(f"\n{'='*60}")
    print(f"[2/5] 数据清洗")
    print(f"{'='*60}")

    original_rows = len(df)

    # 标准化列名
    df = standardize_columns(df)

    # 去重
    dup_count = df.duplicated().sum()
    df = df.drop_duplicates()
    print(f"  去重: 删除 {dup_count} 条重复数据")

    # 缺失值统计
    for col in df.columns:
        null_count = df[col].isnull().sum()
        if null_count > 0:
            pct = null_count / len(df) * 100
            print(f"  缺失值 [{col}]: {null_count} 条 ({pct:.2f}%)")

    # 清理：文本列填充空字符串，去除首尾空白
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].fillna("").astype(str).str.strip()

    # 数值列保持原样
    print(f"  清洗后: {len(df)} 行 (删除 {original_rows - len(df)} 行)")
    return df


def run_nlp_preprocessing(df: pd.DataFrame) -> tuple:
    """执行NLP预处理"""
    print(f"\n{'='*60}")
    print(f"[3/5] NLP文本预处理（分词 + 关键词提取 + 体育标签标注）")
    print(f"{'='*60}")

    # 自动检测列名（使用共享函数）
    col_map = detect_columns(df)

    business_col = col_map.get("business", df.columns[3])
    code_col = col_map.get("code", df.columns[2])
    name_col = col_map.get("name", df.columns[1])

    print(f"  业务文本列 → {business_col}")
    print(f"  行业代码列 → {code_col}")
    print(f"  企业名称列 → {name_col}")

    texts = df[business_col].tolist()
    codes = df[code_col].tolist() if code_col else None
    names = df[name_col].tolist() if name_col else None

    # 体育词典信息
    categories = get_sport_categories()
    sport_dict = get_sport_dict()
    print(f"  体育业态分类: {len(categories)} 类 → {categories}")
    print(f"  体育关键词库: {len(sport_dict)} 词")

    # 批量预处理
    print(f"\n  正在处理 {len(texts)} 条业务文本...")
    start_time = time.time()

    results = batch_preprocess_enterprises(texts, codes, names)

    elapsed = time.time() - start_time
    print(f"  处理完成! 耗时: {elapsed:.1f} 秒 ({len(texts) / elapsed:.0f} 条/秒)")

    # 统计
    stats = get_preprocess_stats(results)

    return results, stats, col_map


def print_stats(stats: dict):
    """打印预处理统计摘要"""
    print(f"\n{'='*60}")
    print(f"[4/5] 预处理统计")
    print(f"{'='*60}")
    print(f"  企业总数:       {stats['total']:>8,}")
    print(f"  体育企业数:     {stats['sport_enterprise_count']:>8,}  ({stats['sport_ratio']}%)")
    print(f"  直接体育代码:   {stats['code_direct_count']:>8,}")
    print(f"  间接相关代码:   {stats['code_indirect_count']:>8,}")
    print(f"  文本匹配体育:   {stats['text_sport_count']:>8,}")
    print(f"  纯跨界经营:     {stats['crossover_count']:>8,}")
    print(f"\n  业态分布:")
    for cat, count in sorted(stats["category_distribution"].items(),
                             key=lambda x: x[1], reverse=True):
        bar = "█" * max(1, count // (stats["total"] // 80 + 1))
        print(f"    {cat:<8}: {count:>6,}  {bar}")
    print(f"\n  置信度分布:")
    for level, count in stats["confidence_distribution"].items():
        print(f"    {level:<6}: {count:>6,}")


def export_results(
    df: pd.DataFrame,
    results: list,
    stats: dict,
    col_map: dict,
    output_dir: str = "../data/processed",
):
    """导出标准化数据集和统计报告"""
    print(f"\n{'='*60}")
    print(f"[5/5] 导出结果 → {output_dir}")
    print(f"{'='*60}")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 1. 将预处理结果合并到DataFrame
    df_out = df.copy()
    df_out["分词结果"] = [" ".join(r["tokens"]) for r in results]
    df_out["关键词"] = [";".join(r["keywords"]) for r in results]
    df_out["体育关键词"] = [";".join(r["sport_keywords"]) for r in results]
    df_out["是否体育业务"] = ["是" if r["is_sport"] else "否" for r in results]
    df_out["体育业态分类"] = [r["sport_category"] for r in results]
    df_out["识别置信度"] = [round(r["confidence"], 2) for r in results]
    df_out["行业代码类型"] = [r.get("code_type", "none") for r in results]
    df_out["文本长度"] = [r["features"]["text_length"] for r in results]
    df_out["体育词命中数"] = [r["features"]["sport_keyword_count"] for r in results]

    # 导出完整数据集 CSV
    csv_path = output_path / f"enterprise_dataset_{timestamp}.csv"
    df_out.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"  [OK] 标准化数据集: {csv_path} ({len(df_out)} 行 x {len(df_out.columns)} 列)")

    # 2. 导出特征数据（仅数值特征）
    feature_cols = [
        "统一社会信用代码", "详细名称", "行业代码",
        "是否体育业务", "体育业态分类", "识别置信度",
        "体育关键词", "文本长度", "体育词命中数",
    ]
    available_feature_cols = [c for c in feature_cols if c in df_out.columns]
    df_features = df_out[available_feature_cols]
    feat_path = output_path / f"enterprise_features_{timestamp}.csv"
    df_features.to_csv(feat_path, index=False, encoding="utf-8-sig")
    print(f"  [OK] 特征数据:     {feat_path}")

    # 3. 导出统计报告 JSON
    stats_path = output_path / f"preprocess_stats_{timestamp}.json"

    # 精简 stats 以便 JSON 序列化
    serializable_stats = {
        "pipeline_version": "1.0.0",
        "processed_at": datetime.now().isoformat(),
        "input_file": str(csv_path),
        "total_enterprises": stats["total"],
        "sport_enterprise_count": stats["sport_enterprise_count"],
        "sport_ratio_pct": stats["sport_ratio"],
        "code_direct_count": stats["code_direct_count"],
        "code_indirect_count": stats["code_indirect_count"],
        "text_sport_count": stats["text_sport_count"],
        "crossover_count": stats["crossover_count"],
        "category_distribution": stats["category_distribution"],
        "confidence_distribution": stats["confidence_distribution"],
        "sport_categories_used": stats["all_categories"],
        "column_mapping": col_map,
    }
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(serializable_stats, f, ensure_ascii=False, indent=2)
    print(f"  [OK] 统计报告:     {stats_path}")

    # 4. 导出体育企业子集
    sport_df = df_out[df_out["是否体育业务"] == "是"]
    if len(sport_df) > 0:
        sport_path = output_path / f"sport_enterprises_{timestamp}.csv"
        sport_df.to_csv(sport_path, index=False, encoding="utf-8-sig")
        print(f"  [OK] 体育企业子集: {sport_path} ({len(sport_df)} 家)")

    return {
        "full_dataset": str(csv_path),
        "features": str(feat_path),
        "stats": str(stats_path),
    }


def main():
    parser = argparse.ArgumentParser(
        description="体育产业企业数据预处理流水线"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        default=None,
        help="输入 xlsx/csv 文件路径（默认自动查找 data/ 目录）",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="../data/processed",
        help="输出目录（默认 ../data/processed）",
    )
    parser.add_argument(
        "--skip-clean",
        action="store_true",
        help="跳过数据清洗步骤",
    )
    parser.add_argument(
        "--sample", "-n",
        type=int,
        default=0,
        help="只处理前 N 条（用于快速测试）",
    )
    args = parser.parse_args()

    # 查找输入文件
    input_file = args.input or find_data_file()
    output_dir = ensure_output_dir(args.output)

    print(f"\n{'█'*60}")
    print(f"  体育产业企业微观数据 — 标准化预处理流水线")
    print(f"  启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'█'*60}")

    # [1-2] 加载 + 清洗
    df = load_and_clean(input_file, skip_clean=args.skip_clean)

    # 采样模式
    if args.sample > 0:
        df = df.head(args.sample)
        print(f"  [采样模式] 仅处理前 {args.sample} 条")

    # [3] NLP预处理
    results, stats, col_map = run_nlp_preprocessing(df)

    # [4] 统计打印
    print_stats(stats)

    # [5] 导出
    export_paths = export_results(df, results, stats, col_map, output_dir)

    print(f"\n{'█'*60}")
    print(f"  流水线执行完毕!")
    print(f"  结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'█'*60}\n")

    return export_paths


if __name__ == "__main__":
    main()
