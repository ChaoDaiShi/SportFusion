"""
================================================================================
  体育业务边界识别 & 比重测算 — 全量运行脚本
================================================================================
  加载 step1 预处理数据 → 执行全量识别 → 模型验证对比 → 导出结果

  用法：
    python run_recognition.py
    python run_recognition.py --input ../data/processed/enterprise_dataset_20260625_225803.csv
    python run_recognition.py --sample 5000
================================================================================
"""
import sys
import os
import json
import argparse
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from utils.file_parser import detect_columns
from services.sport_recognition import (
    batch_recognize_full, get_recognition_stats,
    parse_business_lines, classify_business_line,
)
from services.output_calc import extract_region, batch_calculate
from services.model_validate import compare_methods


def find_latest_dataset(data_dir: str = "../../data/processed") -> str:
    """自动查找最新的标准化数据集"""
    data_path = Path(data_dir)
    if not data_path.exists():
        raise FileNotFoundError(f"输出目录不存在: {data_dir}")

    datasets = sorted(data_path.glob("enterprise_dataset_*.csv"))
    if not datasets:
        raise FileNotFoundError(f"在 {data_dir} 中未找到预处理数据集，请先运行 run_preprocess.py")

    return str(datasets[-1])


def main():
    parser = argparse.ArgumentParser(description="体育业务边界识别与比重测算")
    parser.add_argument("--input", "-i", type=str, default=None,
                        help="预处理数据集路径（默认自动查找最新）")
    parser.add_argument("--output", "-o", type=str, default="../data/processed",
                        help="输出目录")
    parser.add_argument("--sample", "-n", type=int, default=0,
                        help="只处理前 N 条（测试用）")
    args = parser.parse_args()

    input_file = args.input or find_latest_dataset()
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"\n{'='*70}")
    print(f"  体育业务边界识别 & 比重测算")
    print(f"  启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  输入数据: {input_file}")
    print(f"{'='*70}\n")

    # [1] 加载数据
    print("[1/4] 加载预处理数据集...")
    df = pd.read_csv(input_file, encoding="utf-8-sig")
    print(f"  加载完成: {len(df)} 行 x {len(df.columns)} 列")

    if args.sample > 0:
        df = df.head(args.sample)
        print(f"  [采样模式] 仅处理前 {args.sample} 条")

    # 自动检测列名
    col_map = detect_columns(df)
    name_col = col_map["name"]
    code_col = col_map.get("code", df.columns[2])
    business_col = col_map.get("business", df.columns[3])

    print(f"  列映射: name={name_col}, code={code_col}, business={business_col}\n")

    # [2] 全量识别
    print("[2/4] 全量体育业务识别 + 比重测算...")
    enterprises = []
    for _, row in df.iterrows():
        enterprises.append({
            "name": str(row.get(name_col, "")),
            "industry_code": int(row[code_col]) if pd.notna(row.get(code_col)) else None,
            "business_text": str(row.get(business_col, "")),
            "credit_code": str(row.get(col_map.get("credit_code", df.columns[0]), "")),
        })

    start = time.time()
    results = batch_recognize_full(enterprises)
    elapsed = time.time() - start
    print(f"  识别完成! 耗时: {elapsed:.1f}s ({len(results)/elapsed:.0f} 条/秒)")

    # [3] 统计
    print("\n[3/4] 统计分析与模型验证...")
    stats = get_recognition_stats(results)

    print(f"  {'─'*50}")
    print(f"  企业总数:        {stats['total']:>8,}")
    print(f"  体育企业:        {stats['sport_count']:>8,}  ({stats['sport_ratio_pct']}%)")
    print(f"  跨界经营:        {stats['crossover_count']:>8,}  ({stats['crossover_pct']}%)")
    print(f"  平均体育占比:    {stats['avg_sport_ratio_pct']:>8}%")
    print(f"  {'─'*50}")

    print(f"\n  业态分布:")
    for cat, count in sorted(stats["category_distribution"].items(),
                             key=lambda x: -x[1]):
        if cat != "非体育":
            bar = "#" * max(1, count // (max(stats["sport_count"], 1) // 30 + 1))
            print(f"    {cat:<12}: {count:>6,}  {bar}")

    print(f"\n  比重区间分布:")
    for bin_name, count in stats["ratio_distribution"].items():
        bar = "|" * max(1, count // (stats["total"] // 50 + 1))
        print(f"    {bin_name:<10}: {count:>8,}  {bar}")

    # 模型对比
    comparison = compare_methods(enterprises, results)
    cs = comparison["comparison_summary"]
    print(f"\n  传统法 vs 模型法对比:")
    print(f"    传统法体育企业:    {cs['traditional_sport_count']:>8,}  ({cs['traditional_sport_pct']}%)")
    print(f"    模型法体育企业:    {cs['model_sport_count']:>8,}  ({cs['model_sport_pct']}%)")
    print(f"    仅模型发现(增量):  {cs['incremental_count']:>8,}  ({cs['incremental_pct']}%)")
    print(f"    仅传统法标记:      {cs['only_traditional']:>8,}")
    print(f"    跨界经营发现:      {cs['crossover_discovered']:>8,}")

    print(f"\n  结论:")
    for key, text in comparison.get("conclusion", {}).items():
        print(f"    [{key}] {text}")

    # [4] 导出结果
    print(f"\n[4/4] 导出结果 → {output_dir}")

    # 4a. 业务边界明细
    boundary_rows = []
    for r in results:
        if r.get("is_sport"):
            boundary_rows.append({
                "企业名称": r.get("enterprise_name", ""),
                "行业代码": r.get("industry_code", ""),
                "体育业态": r.get("sport_category", ""),
                "体育业务占比": r.get("sport_ratio", 0),
                "置信度": r.get("confidence", 0),
                "是否跨界": "是" if r.get("is_crossover") else "否",
                "跨界类型": r.get("crossover_type", ""),
                "业务总线数": r.get("total_business_lines", 0),
                "体育业务线数": r.get("sport_business_lines", 0),
                "体育业务线": "; ".join([sl["line"] for sl in r.get("sport_lines", [])]),
                "非体育业务线": "; ".join(r.get("non_sport_lines", [])),
                "体育关键词": "; ".join(r.get("keywords", [])),
                "特征W1业务范围": r.get("feature_weights", {}).get("w1_business_scope", 0),
                "特征W2关键词密度": r.get("feature_weights", {}).get("w2_keyword_density", 0),
                "特征W3代码权重": r.get("feature_weights", {}).get("w3_code_weight", 0),
                "特征W4业态覆盖": r.get("feature_weights", {}).get("w4_category_coverage", 0),
            })

    if boundary_rows:
        df_boundary = pd.DataFrame(boundary_rows)
        boundary_path = output_dir / f"enterprise_boundaries_{timestamp}.csv"
        df_boundary.to_csv(boundary_path, index=False, encoding="utf-8-sig")
        print(f"  [OK] 业务边界明细: {boundary_path} ({len(df_boundary)} 家体育企业)")

    # 4b. 比重测算结果（全部企业）
    ratio_rows = []
    for i, r in enumerate(results):
        ent = enterprises[i]
        ratio_rows.append({
            "统一社会信用代码": ent.get("credit_code", ""),
            "企业名称": ent.get("name", ""),
            "行业代码": ent.get("industry_code"),
            "主要业务活动": ent.get("business_text", ""),
            "是否体育": "是" if r.get("is_sport") else "否",
            "体育业态": r.get("sport_category", ""),
            "体育业务占比": r.get("sport_ratio", 0),
            "置信度": r.get("confidence", 0),
            "是否跨界": "是" if r.get("is_crossover") else "否",
            "跨界类型": r.get("crossover_type", ""),
            "业务总线数": r.get("total_business_lines", 0),
            "体育业务线数": r.get("sport_business_lines", 0),
            "区域": extract_region(ent.get("name", "")),
        })

    df_ratio = pd.DataFrame(ratio_rows)
    ratio_path = output_dir / f"sport_ratio_results_{timestamp}.csv"
    df_ratio.to_csv(ratio_path, index=False, encoding="utf-8-sig")
    print(f"  [OK] 比重测算结果: {ratio_path} ({len(df_ratio)} 家企业)")

    # 4c. 模型验证报告
    report = {
        "run_at": datetime.now().isoformat(),
        "input_file": input_file,
        "total_enterprises": len(enterprises),
        "recognition_stats": stats,
        "comparison": {
            "summary": comparison["comparison_summary"],
            "ratio_distribution": comparison["ratio_distribution_comparison"],
            "category_comparison": comparison["category_comparison"],
            "conclusion": comparison["conclusion"],
            "incremental_count": len(comparison.get("incremental_enterprises", [])),
        },
    }
    report_path = output_dir / f"model_validation_{timestamp}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"  [OK] 模型验证报告: {report_path}")

    # 4d. 业态+区域交叉统计
    sport_df = df_ratio[df_ratio["是否体育"] == "是"]
    if len(sport_df) > 0:
        print(f"\n  区域TOP10:")
        region_dist = sport_df["区域"].value_counts().head(10)
        for region, count in region_dist.items():
            print(f"    {region}: {count:>6,} 家")

        print(f"\n  业态x跨界交叉:")
        crossover_by_cat = sport_df[sport_df["是否跨界"] == "是"]["体育业态"].value_counts()
        for cat, count in crossover_by_cat.items():
            print(f"    {cat}: {count:>6,} 家")

    print(f"\n{'='*70}")
    print(f"  识别流程执行完毕!")
    print(f"  结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")

    return {
        "boundary_path": str(boundary_path) if boundary_rows else None,
        "ratio_path": str(ratio_path),
        "report_path": str(report_path),
    }


if __name__ == "__main__":
    main()
