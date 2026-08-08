"""Deterministic grounding for the monitoring analysis assistant."""

from typing import Any


def _citation(
    cid: str,
    label: str,
    value: str,
    snapshot: dict[str, Any],
) -> dict[str, str]:
    provenance = snapshot["provenance"]
    return {
        "id": cid,
        "label": label,
        "value": value,
        "data_version": provenance["data_version"],
        "model_version": provenance["model_version"],
    }


def build_grounding(message: str, snapshot: dict[str, Any]) -> dict[str, Any]:
    metrics = {item["id"]: item for item in snapshot["metrics"]}
    citations = [
        _citation(
            "metric-enterprises",
            "识别体育企业",
            f"{metrics['sport_enterprises']['value']} 家",
            snapshot,
        ),
        _citation(
            "metric-output",
            "总产出指数",
            str(metrics["output_index"]["value"]),
            snapshot,
        ),
    ]
    comparison = snapshot.get("method_comparison")
    if comparison:
        citations.insert(
            0,
            _citation(
                "metric-gap",
                "传统方法低估差异",
                f"{comparison['gap_percent']}%",
                snapshot,
            ),
        )

    asks_about_risk = any(keyword in message for keyword in ("集中度", "风险", "成都"))
    if asks_about_risk and snapshot.get("risks"):
        risk = snapshot["risks"][0]
        answer = (
            f"{risk['title']}的综合风险值为 {risk['score']}。主要依据包括："
            + "；".join(risk["evidence"][:2])
            + "。建议先核验关联样本，再运行校正测算。"
        )
        actions = [
            {
                "id": "open-risk",
                "type": "open_risk",
                "label": "查看风险证据",
                "payload": {"risk_id": risk["id"]},
            },
            {
                "id": "recalculate",
                "type": "preview_recalculation",
                "label": "预览校正测算",
                "payload": {"risk_id": risk["id"]},
            },
        ]
    elif comparison:
        gap = comparison["gap_percent"]
        answer = (
            f"当前模型测算结果较传统行业代码法高 {gap}%。差异主要来自多元经营企业的"
            f"漏识别修正；本批次识别体育企业 {metrics['sport_enterprises']['value']} 家。"
        )
        actions = [
            {
                "id": "compare",
                "type": "navigate",
                "label": "联动测算对比",
                "payload": {"path": "/compare"},
            },
            {
                "id": "report",
                "type": "preview_report",
                "label": "生成政策摘要",
                "payload": {"report_type": "policy"},
            },
        ]
    else:
        answer = (
            f"当前真实批次识别体育企业 {metrics['sport_enterprises']['value']} 家，"
            f"总产出指数为 {metrics['output_index']['value']}。该批次尚未生成方法对比和"
            "模型评测结果，因此不能判断低估幅度。"
        )
        actions = [
            {
                "id": "compare",
                "type": "navigate",
                "label": "运行测算对比",
                "payload": {"path": "/compare"},
            },
            {
                "id": "evaluation",
                "type": "navigate",
                "label": "查看模型评估",
                "payload": {"path": "/model-evaluation"},
            },
        ]

    context_text = "\n".join(
        f"{item['label']}: {item['value']}" for item in citations
    )
    return {
        "context_text": context_text,
        "citations": citations,
        "actions": actions,
        "fallback_answer": answer,
    }
