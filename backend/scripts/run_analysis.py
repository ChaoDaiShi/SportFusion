"""
============================================================================
  体育产业规模测算与空间结构分析 — 全量运行脚本
============================================================================
  加载 step2 比重测算结果 → 区域/业态聚合 → 空间集中度 → 结构分析 → 导出报告

  用法：
    python run_analysis.py
    python run_analysis.py --input ../data/processed/sport_ratio_results_YYYYMMDD.csv
    python run_analysis.py --region-detail  # 输出详细区域数据
============================================================================
"""
import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from services.industry_analysis import generate_analysis_report
from services.output_calc import extract_region


def find_latest_ratio_file(data_dir: str = "../../data/processed") -> str:
    """查找最新的比重测算结果"""
    data_path = Path(data_dir)
    ratio_files = sorted(data_path.glob("sport_ratio_results_*.csv"))
    if not ratio_files:
        raise FileNotFoundError(f"未找到比重测算结果，请先运行 run_recognition.py")
    return str(ratio_files[-1])


def main():
    parser = argparse.ArgumentParser(description="体育产业规模测算与分析")
    parser.add_argument("--input", "-i", type=str, default=None,
                        help="比重测算结果路径（默认自动查找最新）")
    parser.add_argument("--output", "-o", type=str, default="../data/processed",
                        help="输出目录")
    parser.add_argument("--region-detail", action="store_true",
                        help="输出详细区域CSV")
    parser.add_argument("--category-detail", action="store_true",
                        help="输出详细业态CSV")
    args = parser.parse_args()

    input_file = args.input or find_latest_ratio_file()
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"\n{'='*70}")
    print(f"  体育产业规模测算与空间结构分析")
    print(f"  启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  输入数据: {input_file}")
    print(f"{'='*70}\n")

    # [1] 加载数据
    print("[1/3] 加载比重测算数据...")
    df = pd.read_csv(input_file, encoding="utf-8-sig")
    print(f"  加载完成: {len(df)} 行")

    enterprises = []
    results = []
    for _, row in df.iterrows():
        enterprises.append({
            "name": str(row.get("企业名称", "")),
            "industry_code": row.get("行业代码"),
            "business_text": str(row.get("主要业务活动", "")),
            "credit_code": str(row.get("统一社会信用代码", "")),
        })
        results.append({
            "is_sport": row.get("是否体育") == "是",
            "sport_category": str(row.get("体育业态", "")),
            "sport_ratio": float(row.get("体育业务占比", 0)),
            "confidence": float(row.get("置信度", 0)),
            "is_crossover": row.get("是否跨界") == "是",
            "crossover_type": str(row.get("跨界类型", "")),
            "total_business_lines": int(row.get("业务总线数", 0)),
            "sport_business_lines": int(row.get("体育业务线数", 0)),
        })

    # [2] 分析
    print("[2/3] 执行产业分析...")
    report = generate_analysis_report(results, enterprises)

    # 打印摘要
    ov = report["overview"]
    print(f"\n  {'─'*50}")
    print(f"  概览:")
    print(f"    企业总数:       {ov['total_enterprises']:>8,}")
    print(f"    体育企业:       {ov['sport_enterprises']:>8,}  ({ov['sport_ratio_pct']}%)")
    print(f"    跨界经营:       {ov['crossover_count']:>8,}  ({ov['crossover_pct']}%)")
    print(f"    平均体育占比:   {ov['avg_sport_ratio_pct']:>8.1f}%")
    print(f"    总产出指数:     {ov['total_output_index']:>10,.0f}")
    print(f"  {'─'*50}")

    sc = report["regional_analysis"]["spatial_concentration"]
    print(f"\n  空间集中度:")
    print(f"    CR3:  {sc['cr3_pct']}%  CR5: {sc['cr5_pct']}%")
    print(f"    HHI:  {sc['hhi']}  Gini: {sc['gini']}")
    print(f"    结论: {sc['conclusion']}")

    sa = report["structure_analysis"]
    print(f"\n  产业结构:")
    print(f"    多样性指数:  {sa['diversity_index']:.2f}")
    print(f"    业态均衡度:  {sa['balance_assessment']}")
    print(f"    跨界经营率:  {sa['crossover_rate_pct']}%")
    if sa["dominant_category"]:
        print(f"    主导业态:    {sa['dominant_category']['name']} ({sa['dominant_category']['share_pct']}%)")

    print(f"\n  区域TOP10:")
    for i, r in enumerate(report["regional_analysis"]["top_cities"][:10], 1):
        bar = "#" * max(1, int(r["sport_output_index"] / 100))
        print(f"    {i:2}. {r['region']:<8}: {r['sport_output_index']:>8.0f}  {r['enterprise_count']:>5}家  {bar}")

    print(f"\n  业态分布:")
    for c in report["category_analysis"]["categories"]:
        bar = "#" * max(1, int(c["output_index"] / 100))
        print(f"    {c['category']:<10}: {c['output_index']:>8.0f}  {c['enterprise_count']:>5}家  "
              f"跨界{c['crossover_pct']:.0f}%  {bar}")

    # [3] 导出
    print(f"\n[3/3] 导出结果 → {output_dir}")

    # 3a. 综合分析报告 JSON
    report_path = output_dir / f"industry_analysis_{timestamp}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"  [OK] 综合分析报告: {report_path}")

    # 3b. 区域详细数据
    if args.region_detail:
        region_rows = []
        for r in report["regional_analysis"]["top_cities"]:
            region_rows.append({
                "区域": r["region"],
                "体育企业数": r["enterprise_count"],
                "产出指数": r["sport_output_index"],
                "平均体育占比": r["avg_sport_ratio"],
                "主导业态": max(r.get("category_breakdown", {}), key=r["category_breakdown"].get) if r.get("category_breakdown") else "",
            })
        region_path = output_dir / f"region_detail_{timestamp}.csv"
        pd.DataFrame(region_rows).to_csv(region_path, index=False, encoding="utf-8-sig")
        print(f"  [OK] 区域详细: {region_path}")

    # 3c. 业态详细数据
    if args.category_detail:
        cat_path = output_dir / f"category_detail_{timestamp}.csv"
        pd.DataFrame(report["category_analysis"]["categories"]).to_csv(
            cat_path, index=False, encoding="utf-8-sig"
        )
        print(f"  [OK] 业态详细: {cat_path}")

    # 3d. 纯文本摘要（便于嵌入报告）
    summary_path = output_dir / f"analysis_summary_{timestamp}.txt"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(f"体育产业规模测算与空间结构分析报告\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{'='*60}\n\n")
        f.write(f"一、产业概况\n")
        f.write(f"  企业总数: {ov['total_enterprises']:,} 家\n")
        f.write(f"  体育企业: {ov['sport_enterprises']:,} 家 ({ov['sport_ratio_pct']}%)\n")
        f.write(f"  跨界经营: {ov['crossover_count']:,} 家 ({ov['crossover_pct']}%)\n")
        f.write(f"  总产出指数: {ov['total_output_index']:,.0f}\n\n")
        f.write(f"二、空间分布\n")
        f.write(f"  CR3集中度: {sc['cr3_pct']}%, CR5: {sc['cr5_pct']}%\n")
        f.write(f"  HHI指数: {sc['hhi']}, 基尼系数: {sc['gini']}\n")
        f.write(f"  {sc['conclusion']}\n\n")
        f.write(f"三、产业结构\n")
        f.write(f"  多样性指数: {sa['diversity_index']:.2f}\n")
        f.write(f"  {sa['balance_assessment']}\n")
        f.write(f"  跨界经营率: {sa['crossover_rate_pct']}%\n\n")
        f.write(f"四、区域排名TOP10\n")
        for i, r in enumerate(report["regional_analysis"]["top_cities"][:10], 1):
            f.write(f"  {i:2}. {r['region']:<8}: {r['sport_output_index']:>8.0f} ({r['enterprise_count']:>5}家)\n")
        f.write(f"\n五、业态分布\n")
        for c in report["category_analysis"]["categories"]:
            f.write(f"  {c['category']:<10}: {c['output_index']:>8.0f} ({c['enterprise_count']:>5}家, 跨界{c['crossover_pct']:.0f}%)\n")
    print(f"  [OK] 文本摘要: {summary_path}")

    print(f"\n{'='*70}")
    print(f"  分析完成!")
    print(f"  结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
