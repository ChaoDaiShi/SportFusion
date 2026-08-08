"""Build versioned monitoring snapshots without mixing data modes."""

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


PIPELINE = [
    {"id": "data", "label": "企业数据治理", "description": "清洗、分词、标签"},
    {"id": "recognition", "label": "业务边界识别", "description": "类型与置信度"},
    {"id": "ratio", "label": "经营比重测算", "description": "多维加权模型"},
    {"id": "scale", "label": "产业规模估算", "description": "区域与分业态产出"},
    {"id": "decision", "label": "验证与决策", "description": "性能、风险、建议"},
]

DEMO_DASHBOARD = {
    "overview": {
        "sport_enterprises": 8950,
        "total_output_index": 579124.95,
        "crossover_count": 977,
    },
    "map": {
        "data": [
            {"name": "成都市", "value": 237694.59},
            {"name": "绵阳市", "value": 13636.0},
            {"name": "宜宾市", "value": 11993.47},
            {"name": "泸州市", "value": 11251.82},
            {"name": "乐山市", "value": 10318.35},
        ]
    },
    "line": {
        "labels": ["2019", "2020", "2021", "2022", "2023", "2024", "2025"],
        "series": [],
    },
    "concentration": {"cr3_pct": 77.3},
    "structure": {"diversity_index": 0.7638, "crossover_rate_pct": 10.92},
}

MODEL_METRICS = {
    "accuracy": 0.916,
    "precision": 0.928,
    "recall": 0.904,
    "mae": 0.083,
    "normal_input_pass_rate": 0.916,
    "missing_text_pass_rate": 0.962,
    "noise_input_pass_rate": 0.947,
    "runtime_seconds_per_10k": 8.7,
    "peak_memory_mb": 486,
}

DEMO_RISKS = [
    {
        "id": "R-2025-071",
        "title": "成都健身服务市场集中度异常",
        "type": "industry_structure",
        "level": "high",
        "status": "analyzing",
        "score": 89,
        "confidence": 0.93,
        "region": "成都市",
        "category": "健身休闲",
        "deviation_score": 91,
        "impact_score": 84,
        "evidence_score": 93,
        "enterprise_ids": [],
        "evidence": [
            "CR3 升至 77.3%，超过 60% 预警阈值",
            "头部区域产出占比继续上升",
            "新增样本区域分布不均衡",
        ],
    },
    {
        "id": "R-2025-062",
        "title": "企业业务边界识别置信度偏低",
        "type": "enterprise_boundary",
        "level": "medium",
        "status": "pending_verification",
        "score": 76,
        "confidence": 0.81,
        "region": "绵阳市",
        "category": "健身休闲",
        "deviation_score": 74,
        "impact_score": 69,
        "evidence_score": 81,
        "enterprise_ids": ["DEMO-001", "DEMO-002"],
        "evidence": ["18 家企业置信度低于 0.60", "主营业务文本存在跨业态描述"],
    },
    {
        "id": "R-2025-055",
        "title": "区域样本缺失率连续升高",
        "type": "data_quality",
        "level": "medium",
        "status": "pending_action",
        "score": 69,
        "confidence": 0.88,
        "region": "宜宾市",
        "category": None,
        "deviation_score": 70,
        "impact_score": 58,
        "evidence_score": 88,
        "enterprise_ids": [],
        "evidence": ["主要业务活动缺失率连续两期升高"],
    },
    {
        "id": "R-2025-043",
        "title": "模型结果较基线发生轻微漂移",
        "type": "model_performance",
        "level": "watch",
        "status": "monitoring",
        "score": 54,
        "confidence": 0.90,
        "region": "德阳市",
        "category": None,
        "deviation_score": 48,
        "impact_score": 42,
        "evidence_score": 90,
        "enterprise_ids": [],
        "evidence": ["低置信度样本占比上升 2.1 个百分点"],
    },
]


def _provenance(
    mode: str, updated_at: str | None, missing_fields: list[str]
) -> dict[str, Any]:
    timestamp = updated_at or datetime.now(timezone.utc).isoformat()
    return {
        "mode": mode,
        "dataset_id": "sichuan-enterprises-2025",
        "data_version": "2025.07",
        "model_version": "V3.2",
        "updated_at": timestamp,
        "is_complete": not missing_fields,
        "missing_fields": missing_fields,
    }


def _real_structure_risks(source: dict[str, Any]) -> list[dict[str, Any]]:
    cr3 = float(source.get("concentration", {}).get("cr3_pct", 0) or 0)
    if cr3 <= 60:
        return []
    return [
        {
            "id": "REAL-STRUCTURE-CR3",
            "title": "头部区域产业集中度超过预警阈值",
            "type": "industry_structure",
            "level": "high" if cr3 >= 75 else "medium",
            "status": "pending_verification",
            "score": min(99, round(cr3 + 12)),
            "confidence": 0.90,
            "region": "全省",
            "category": None,
            "deviation_score": round(cr3),
            "impact_score": 80,
            "evidence_score": 90,
            "enterprise_ids": [],
            "evidence": [f"当前批次 CR3 为 {cr3:.1f}%，超过 60% 预警阈值"],
        }
    ]


def build_monitoring_snapshot(
    dashboard: dict[str, Any], mode: str, updated_at: str | None = None
) -> dict[str, Any]:
    is_demo = mode == "demo"
    source = deepcopy(DEMO_DASHBOARD if is_demo else dashboard)
    if not source or not source.get("overview"):
        raise ValueError("真实快照缺少 overview，不能用演示数据补齐")

    overview = source.get("overview", {})
    output_index = round(float(overview.get("total_output_index", 0)), 2)
    sport_enterprises = int(overview.get("sport_enterprises", 0))
    crossover_count = int(overview.get("crossover_count", 0))
    metrics = [
        {
            "id": "sport_enterprises",
            "label": "识别体育企业",
            "value": sport_enterprises,
            "unit": "家",
            "tone": "teal",
            "note": f"其中跨界经营 {crossover_count} 家",
        },
        {
            "id": "output_index",
            "label": "体育产业总产出指数",
            "value": output_index,
            "unit": "",
            "tone": "red",
            "note": "按企业体育业务比重加权",
        },
    ]
    if is_demo:
        metrics += [
            {
                "id": "method_gap",
                "label": "传统方法低估差异",
                "value": 18.7,
                "unit": "%",
                "tone": "yellow",
                "note": "演示对比口径",
            },
            {
                "id": "model_accuracy",
                "label": "模型综合一致率",
                "value": 91.6,
                "unit": "%",
                "tone": "blue",
                "note": "异常输入通过率 96.2%",
            },
        ]

    missing_fields = (
        [] if is_demo else ["method_comparison", "model_metrics", "robustness_metrics"]
    )
    return {
        "pipeline": deepcopy(PIPELINE),
        "metrics": metrics,
        "method_comparison": (
            {"traditional": 486900.0, "model": output_index, "gap_percent": 18.7}
            if is_demo
            else None
        ),
        "regions": source.get("map", {}).get("data", []),
        "trend": source.get("line", {"labels": [], "series": []}),
        "risks": deepcopy(DEMO_RISKS) if is_demo else _real_structure_risks(source),
        "model_metrics": deepcopy(MODEL_METRICS) if is_demo else {},
        "provenance": _provenance(mode, updated_at, missing_fields),
    }
