from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from paper_revision.audit_core import (  # noqa: E402
    compute_snapshot_from_counts,
    concentration_metrics,
)
from utils.industry_code import DIRECT_SPORT_CODES  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_record(path: Path, rows: int | None = None, columns: list[str] | None = None) -> dict:
    stat = path.stat()
    return {
        "path": str(path.resolve()),
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(),
        "sha256": sha256(path),
        "rows": rows,
        "columns": columns,
    }


def latest(directory: Path, pattern: str) -> Path:
    matches = sorted(directory.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"未找到 {directory / pattern}")
    return matches[-1]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    artifacts = ROOT / "paper_revision" / "artifacts"
    recomputed = ROOT / "paper_revision" / "recomputed"
    artifacts.mkdir(parents=True, exist_ok=True)

    raw_path = ROOT / "submission" / "原始数据" / "企业原始数据.xlsx"
    dataset_path = ROOT / "data" / "processed" / "enterprise_dataset_20260629_160902.csv"
    legacy_sport_path = ROOT / "data" / "processed" / "sport_enterprises_20260629_160902.csv"
    ratio_path = latest(recomputed, "sport_ratio_results_*.csv")
    validation_path = latest(recomputed, "model_validation_*.json")
    analysis_path = latest(recomputed, "industry_analysis_*.json")
    region_path = latest(recomputed, "region_detail_*.csv")
    category_path = latest(recomputed, "category_detail_*.csv")

    raw = pd.read_excel(raw_path, sheet_name="企业")
    dataset = pd.read_csv(dataset_path, encoding="utf-8-sig")
    legacy_sport = pd.read_csv(legacy_sport_path, encoding="utf-8-sig")
    ratio = pd.read_csv(ratio_path, encoding="utf-8-sig")
    regions = pd.read_csv(region_path, encoding="utf-8-sig")
    categories = pd.read_csv(category_path, encoding="utf-8-sig")
    validation = load_json(validation_path)
    analysis = load_json(analysis_path)

    total = len(ratio)
    fusion = int((ratio["是否体育"] == "是").sum())
    crossover = int((ratio["是否跨界"] == "是").sum())
    numeric_codes = pd.to_numeric(ratio["行业代码"], errors="coerce")
    traditional = int(numeric_codes.isin(set(DIRECT_SPORT_CODES)).sum())
    snapshot = compute_snapshot_from_counts(total, traditional, fusion, crossover)
    snapshot.update(
        {
            "formal_batch": ratio_path.stem.replace("sport_ratio_results_", ""),
            "average_sport_ratio_pct_among_sport_enterprises": round(
                ratio.loc[ratio["是否体育"] == "是", "体育业务占比"].mean() * 100,
                2,
            ),
            "total_output_index": round(
                ratio.loc[ratio["是否体育"] == "是", "体育业务占比"].sum() * 100,
                2,
            ),
            "output_index_definition": "体育企业的体育业务占比之和乘以100；属于相对指数，不是营业收入、增加值或货币产值。",
            "crossover_rate_among_sport_enterprises_pct": round(crossover / fusion * 100, 2),
            "region_source_limitation": "区域由企业名称字符串抽取，不等同于工商注册地址；四川省本级与地级市并存。",
        }
    )

    all_region_outputs = (
        ratio.loc[ratio["是否体育"] == "是"]
        .assign(产出指数=lambda frame: frame["体育业务占比"] * 100)
        .groupby("区域", dropna=False)["产出指数"]
        .sum()
        .sort_values(ascending=False)
    )
    concentration = concentration_metrics(all_region_outputs.tolist())
    snapshot["spatial_concentration_all_regions"] = concentration

    category_records = categories.rename(
        columns={
            "category": "category",
            "enterprise_count": "enterprise_count",
            "output_index": "output_index",
            "output_share_pct": "output_share_pct",
            "avg_sport_ratio": "avg_sport_ratio",
            "crossover_count": "crossover_count",
            "crossover_pct": "crossover_pct",
        }
    ).to_dict(orient="records")
    region_records = regions.to_dict(orient="records")

    conflicts = [
        {
            "id": "sport-enterprise-count",
            "legacy_value": len(legacy_sport),
            "formal_value": fusion,
            "decision": "采用全量边界识别结果8950；9023是预处理阶段的初筛子集，不作为最终识别结果。",
            "evidence_grade": "A/B",
        },
        {
            "id": "incremental-count-field",
            "legacy_value": validation.get("comparison", {}).get("incremental_count"),
            "formal_value": snapshot["incremental_enterprises"],
            "decision": "模型验证JSON的incremental_count记录的是截断案例列表长度100，不是总体增量；总体增量使用summary中的934。",
            "evidence_grade": "B",
        },
        {
            "id": "coverage-vs-accuracy",
            "legacy_value": "部分原稿将11.7%描述为准确率提升",
            "formal_value": "相对识别数量增加11.65%（四舍五入为11.7%）",
            "decision": "统一改为识别数量或识别覆盖范围的相对增加；没有人工金标准时不报告准确率提升。",
            "evidence_grade": "A/B",
        },
        {
            "id": "evaluation-evidence",
            "legacy_value": "AUC=0.91、Kappa=0.86、Pearson r=0.72、n=300",
            "formal_value": None,
            "decision": "当前工作区未找到逐条人工标签、预测分数或标注者记录，相关指标均删除，不作为实证结果。",
            "evidence_grade": "D",
        },
        {
            "id": "output-index-not-currency",
            "legacy_value": "部分原稿将产出指数写作产值或产业规模金额",
            "formal_value": snapshot["total_output_index"],
            "decision": "全文统一称相对产出指数；不得推断营业收入、增加值或货币规模。",
            "evidence_grade": "A/B",
        },
        {
            "id": "trend-and-economic-benefits",
            "legacy_value": "2020—2028趋势预测、成本节省和资源错配金额",
            "formal_value": None,
            "decision": "缺少时间序列、成本台账和对照试验，删除确定性数字，改为应用情景与待验证效益。",
            "evidence_grade": "D",
        },
    ]

    sources = [
        source_record(raw_path, len(raw), raw.columns.tolist()),
        source_record(dataset_path, len(dataset), dataset.columns.tolist()),
        source_record(legacy_sport_path, len(legacy_sport), legacy_sport.columns.tolist()),
        source_record(ratio_path, len(ratio), ratio.columns.tolist()),
        source_record(validation_path),
        source_record(analysis_path),
        source_record(region_path, len(regions), regions.columns.tolist()),
        source_record(category_path, len(categories), categories.columns.tolist()),
    ]

    audit = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "method": "对原始Excel、正式重跑CSV/JSON及历史输出进行交叉核验",
        "raw_data_quality": {
            "rows": len(raw),
            "duplicate_rows": int(raw.duplicated().sum()),
            "duplicate_credit_codes": int(raw["统一社会信用代码"].duplicated().sum()),
            "missing_business_activity": int(raw["主要业务活动"].isna().sum()),
            "missing_industry_code": int(raw["行业代码"].isna().sum()),
        },
        "snapshot": snapshot,
        "ratio_distribution": validation["recognition_stats"]["ratio_distribution"],
        "category_distribution": category_records,
        "city_top10": region_records,
        "all_region_top10": [
            {"region": str(name), "output_index": round(float(value), 2)}
            for name, value in all_region_outputs.head(10).items()
        ],
        "conflicts": conflicts,
        "unsupported_metrics": [
            "Accuracy",
            "Precision",
            "Recall",
            "F1",
            "AUC",
            "Kappa",
            "Pearson r",
            "平台压力测试耗时",
            "经济效益金额",
            "2020—2028预测值",
        ],
        "sources": sources,
        "cross_checks": {
            "analysis_overview_matches": analysis["overview"]["sport_enterprises"] == fusion,
            "validation_summary_matches": validation["comparison"]["summary"]["model_sport_count"] == fusion,
            "category_enterprise_total": int(categories["enterprise_count"].sum()),
            "category_output_total": round(float(categories["output_index"].sum()), 2),
            "region_city_table_note": "region_detail仅含脚本判定的城市TOP10；CR3/CR5使用all_regions，包含四川省本级。",
        },
    }

    json_path = artifacts / "data_audit.json"
    json_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# SportFusion 数据审计报告",
        "",
        f"生成时间：{audit['generated_at']}",
        "",
        "## 正式数据快照",
        "",
        f"- 企业总数：{total:,} 家",
        f"- 传统直接行业代码识别：{traditional:,} 家，占全部企业 {snapshot['traditional_coverage_pct']:.2f}%",
        f"- 融合识别体育企业：{fusion:,} 家，占全部企业 {snapshot['fusion_coverage_pct']:.2f}%",
        f"- 增量识别：{snapshot['incremental_enterprises']:,} 家，相对传统识别数量增加 {snapshot['relative_identification_increase_pct']:.2f}%",
        f"- 跨界经营：{crossover:,} 家，占全部企业 {snapshot['crossover_enterprises']/total*100:.2f}%，占体育企业 {snapshot['crossover_rate_among_sport_enterprises_pct']:.2f}%",
        f"- 相对产出指数：{snapshot['total_output_index']:,.2f}（不是货币产值）",
        f"- 空间集中度：CR3={concentration['cr3_pct']:.2f}%，CR5={concentration['cr5_pct']:.2f}%，HHI={concentration['hhi']:.2f}，Gini={concentration['gini']:.4f}",
        "",
        "## 必须纠正的口径",
        "",
    ]
    for conflict in conflicts:
        lines.append(f"- **{conflict['id']}**：{conflict['decision']}")
    lines.extend(
        [
            "",
            "## 数据边界",
            "",
            "- 产出指数由体育业务占比累加得到，只能用于样本内部的相对比较。",
            "- 区域字段由企业名称字符串抽取，不能替代工商注册地址。",
            "- 当前材料没有可复核的人工金标准，因此不报告准确率、精确率、召回率、F1、AUC、Kappa 或相关系数。",
            "- 当前数据是单一时间截面，不能支持确定性的2020—2028趋势预测。",
            "",
        ]
    )
    (artifacts / "data_audit.md").write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({"json": str(json_path), "formal_batch": snapshot["formal_batch"], "snapshot": snapshot}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
