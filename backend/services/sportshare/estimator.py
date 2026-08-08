"""
统一 SportShare 估计服务。

每个企业的 SportShare 通过以下优先级确定：
    1. manual_share（人工复核后核定值）
    2. model_share（RandomForest 模型估计）
    3. fallback_share（分层回退估计）

所有路径输出统一结构，包含：
    - effective_share: 最终使用的比重值
    - share_source: "model" | "fallback" | "manual"
    - lower_bound / upper_bound: 预测区间
    - 完整 provenance 信息
"""

from dataclasses import dataclass, field
from typing import Any

from ml.sportshare.features import build_sportshare_features, sportshare_features_to_array
from ml.sportshare.interval import build_prediction_interval
from ml.sportshare.model import SportShareModelArtifact, predict_single


@dataclass
class SportShareEstimate:
    """单个企业的 SportShare 估计结果"""

    enterprise_id: str | None = None
    credit_code: str | None = None
    enterprise_name: str | None = None

    # 估计值
    model_share: float | None = None
    fallback_share: float | None = None
    manual_share: float | None = None
    effective_share: float = 0.0

    # 来源
    share_source: str = "none"  # "model" | "fallback" | "manual" | "none"

    # 区间
    lower_bound: float = 0.0
    upper_bound: float = 1.0

    # 元数据
    sport_category: str = ""
    sport_score: float = 0.0
    code_type: str = "none"
    total_lines: int = 0
    sport_lines: int = 0
    is_model_eligible: bool = False

    # Provenance
    model_version: str = ""
    residual_q90: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# ---- 分层回退规则 ----

def _fallback_by_structure(
    code_type: str,
    sport_score: float,
    sport_category: str,
    total_lines: int,
    sport_lines: int,
) -> float:
    """
    分层回退：对不能进入模型估计的企业使用基于结构的回退。

    回退优先级：
        1. direct code + sport_lines≥1 → 0.65
        2. indirect code + sport_lines≥1 → 0.35
        3. text-only sport + sport_lines≥1 → 0.25
        4. direct code + no text → 0.15
        5. 其他 → 0.0

    这些值是 documented defaults，可通过配置覆盖。
    正式值需由 formal artifact 确认。
    """
    if code_type == "direct" and sport_lines >= 1:
        return 0.65
    if code_type == "indirect" and sport_lines >= 1:
        return 0.35
    if code_type == "none" and sport_score >= 0.10 and sport_lines >= 1:
        return 0.25
    if code_type == "direct":
        return 0.15
    return 0.0


# ---- 统一估计入口 ----

def estimate_sport_share(
    enterprise: dict[str, Any],
    recognition_result: dict[str, Any] | None = None,
    model_artifact: SportShareModelArtifact | None = None,
    residual_q90: float | None = None,
    manual_share_override: float | None = None,
) -> SportShareEstimate:
    """
    统一 SportShare 估计 — 所有路径的单一入口。

    Priority:
        manual_share_override > model_share > fallback_share

    Args:
        enterprise: 企业数据 dict
        recognition_result: 识别结果（含 sport_score, code_type 等）
        model_artifact: 已加载的 RF 模型（None → 不走 model 路径）
        residual_q90: 残差分位数用于区间估计
        manual_share_override: 人工核定值

    Returns:
        SportShareEstimate
    """
    ent_id = str(enterprise.get("enterprise_id", enterprise.get("credit_code", "")))
    text = enterprise.get("business_text", enterprise.get("主要业务活动", ""))
    code = enterprise.get("industry_code", enterprise.get("行业代码"))
    name = enterprise.get("enterprise_name", enterprise.get("name", ""))

    # 从识别结果提取上下文
    sport_score = 0.0
    code_type = "none"
    sport_category = ""
    if recognition_result:
        sport_score = recognition_result.get("sport_score", 0.0)
        code_type = recognition_result.get("code_type", "none")
        sport_category = recognition_result.get("sport_category", "")
    else:
        from domain.industry_code import normalize_industry_code
        from utils.industry_code import get_code_type
        nc = normalize_industry_code(code)
        code_type = get_code_type(nc) if nc else "none"

    estimate = SportShareEstimate(
        enterprise_id=ent_id,
        credit_code=enterprise.get("credit_code", ""),
        enterprise_name=name,
        sport_category=sport_category,
        sport_score=sport_score,
        code_type=code_type,
    )

    # ---- Manual override (highest priority) ----
    if manual_share_override is not None:
        estimate.manual_share = manual_share_override
        estimate.effective_share = manual_share_override
        estimate.share_source = "manual"
        estimate.lower_bound = max(0.0, manual_share_override - 0.05)
        estimate.upper_bound = min(1.0, manual_share_override + 0.05)
        estimate.metadata["manual_reason"] = "人工核定"
        return estimate

    # ---- Model path ----
    if model_artifact is not None and _is_model_eligible(text, code, recognition_result):
        estimate.is_model_eligible = True
        try:
            fv = build_sportshare_features(
                business_text=text,
                industry_code=code,
                sport_score=sport_score,
            )
            feat_array = sportshare_features_to_array(fv)
            pred = predict_single(model_artifact, feat_array)
            estimate.model_share = round(pred, 4)
            estimate.share_source = "model"
            estimate.model_version = model_artifact.model_version
            estimate.residual_q90 = residual_q90

            if residual_q90 is not None:
                lower, upper = build_prediction_interval(pred, residual_q90)
                estimate.lower_bound = lower
                estimate.upper_bound = upper
            else:
                estimate.lower_bound = max(0.0, pred - 0.05)
                estimate.upper_bound = min(1.0, pred + 0.05)

            estimate.effective_share = estimate.model_share
            estimate.metadata["model_version"] = model_artifact.model_version
            return estimate
        except Exception:
            pass  # Fall through to fallback on model failure

    # ---- Fallback path ----
    from services.business_line_service import classify_business_line, parse_business_lines
    lines = parse_business_lines(text) if text else []
    classified = [classify_business_line(line) for line in lines]
    sport_lines = sum(1 for c in classified if c["is_sport"])

    fallback_val = _fallback_by_structure(
        code_type=code_type,
        sport_score=sport_score,
        sport_category=sport_category,
        total_lines=len(lines),
        sport_lines=sport_lines,
    )
    estimate.fallback_share = fallback_val
    estimate.share_source = "fallback"
    estimate.effective_share = fallback_val
    estimate.lower_bound = max(0.0, fallback_val - 0.10)
    estimate.upper_bound = min(1.0, fallback_val + 0.10)
    estimate.total_lines = len(lines)
    estimate.sport_lines = sport_lines
    estimate.metadata["fallback_rule"] = f"code_type={code_type}, sport_lines={sport_lines}"
    return estimate


def _is_model_eligible(
    text: str,
    code: Any,
    recognition_result: dict[str, Any] | None,
) -> bool:
    """检查企业是否满足模型特征完整性条件"""
    if not text or len(text.strip()) < 2:
        return False
    # 必须至少有基本识别结果
    if recognition_result is None:
        return False
    # 必须有有效 sport_score
    sport_score = recognition_result.get("sport_score", 0.0)
    if sport_score <= 0.0 and recognition_result.get("code_type") != "direct":
        return False
    return True


def batch_estimate(
    enterprises: list[dict[str, Any]],
    recognition_results: list[dict[str, Any]] | None = None,
    model_artifact: SportShareModelArtifact | None = None,
    residual_q90: float | None = None,
) -> list[SportShareEstimate]:
    """批量 SportShare 估计"""
    results = []
    for i, ent in enumerate(enterprises):
        rec = recognition_results[i] if recognition_results and i < len(recognition_results) else None
        est = estimate_sport_share(
            enterprise=ent,
            recognition_result=rec,
            model_artifact=model_artifact,
            residual_q90=residual_q90,
        )
        results.append(est)
    return results
