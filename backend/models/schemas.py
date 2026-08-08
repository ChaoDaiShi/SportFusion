"""Pydantic 入参出参实体定义"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


# ==================== 企业相关 ====================
class EnterpriseBase(BaseModel):
    name: str = Field(..., description="企业名称")
    credit_code: Optional[str] = Field(None, description="统一社会信用代码")
    region: Optional[str] = Field(None, description="所在区域")
    city: Optional[str] = Field(None, description="市州")
    district: Optional[str] = Field(None, description="区县")
    industry_code: Optional[str] = Field(None, description="行业代码")
    main_business: Optional[str] = Field(None, description="主营业务描述")
    total_revenue: Optional[float] = Field(0.0, description="总营收（万元）")
    employee_count: Optional[int] = Field(0, description="员工人数")
    total_assets: Optional[float] = Field(0.0, description="资产总额（万元）")
    registered_capital: Optional[float] = Field(0.0, description="注册资本（万元）")
    scale_level: Optional[str] = Field(None, description="企业规模等级")


class EnterpriseCreate(EnterpriseBase):
    pass


class EnterpriseOut(EnterpriseBase):
    id: int
    batch_id: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== 企业识别相关 ====================
class RecognitionRequest(BaseModel):
    enterprise_id: Optional[int] = Field(None, description="企业ID")
    business_text: str = Field(..., description="企业主营业务文本")
    industry_code: Optional[str] = Field(None, description="行业代码")
    enterprise_name: Optional[str] = Field(None, description="企业名称")
    uid: Optional[int] = Field(None, description="前端唯一标识")


class BatchRecognitionRequest(BaseModel):
    enterprises: List[RecognitionRequest] = Field(..., description="批量企业数据")


class RecognitionResult(BaseModel):
    enterprise_id: Optional[int] = None
    enterprise_name: Optional[str] = None
    credit_code: Optional[str] = None
    sport_category: str = Field(..., description="体育业态分类")
    is_sport: bool = False
    is_crossover: bool = False
    crossover_type: str = ""
    code_type: str = ""
    code_text_consistency: str = ""
    sport_score: float = 0.0
    sport_ratio: float = Field(0.0, description="体育营收占比(SportShare)")
    confidence: float = Field(0.0, description="置信度")
    w1_business_scope: float = 0.0
    w2_keyword_density: float = 0.0
    w3_code_weight: float = 0.0
    w4_category_coverage: float = 0.0
    total_business_lines: int = 0
    sport_business_lines: int = 0
    business_lines: List[str] = Field(default_factory=list, description="全部业务线")
    sport_lines: List[dict] = Field(default_factory=list, description="体育业务线详情")
    non_sport_lines: List[str] = Field(default_factory=list, description="非体育业务线")
    keywords: List[str] = Field(default_factory=list, description="匹配关键词")


class BatchRecognitionResult(BaseModel):
    results: List[RecognitionResult]
    total: int
    sport_count: int


# ==================== 产值测算相关（V1.0兼容） ====================
class MeasureRequest(BaseModel):
    enterprise_id: int
    enterprise_name: str
    region: Optional[str] = None
    total_revenue: float = 0.0
    sport_category: str
    sport_revenue_ratio: float = 0.0


class BatchMeasureRequest(BaseModel):
    items: List[MeasureRequest] = Field(..., description="测算数据列表")


class MeasureResult(BaseModel):
    enterprise_id: int
    enterprise_name: str
    region: Optional[str] = None
    sport_category: str
    total_revenue: float
    sport_revenue: float
    sport_ratio: float


class BatchMeasureResult(BaseModel):
    results: List[MeasureResult]
    total_sport_revenue: float = 0.0
    region_summary: List[dict] = Field(default_factory=list)


# ==================== 图表数据相关（V1.0兼容） ====================
class ChartDataRequest(BaseModel):
    chart_type: str = Field(..., description="图表类型: pie/bar/map/line")
    dimension: Optional[str] = Field(None, description="统计维度")
    filters: Optional[dict] = Field(default_factory=dict, description="过滤条件")


class ChartDataResponse(BaseModel):
    chart_type: str
    title: str
    labels: List[str] = Field(default_factory=list)
    series: List[dict] = Field(default_factory=list)
    raw_data: List[dict] = Field(default_factory=list)


# ==================== 模型校验相关（V1.0兼容） ====================
class ValidateRequest(BaseModel):
    model_type: str = Field("sport_recognition", description="模型类型")
    test_data: Optional[List[dict]] = Field(None, description="测试数据")


class ValidateResult(BaseModel):
    accuracy: float = Field(0.0, description="准确率")
    precision: float = Field(0.0, description="精确率")
    recall: float = Field(0.0, description="召回率")
    f1_score: float = Field(0.0, description="F1分数")
    mae: float = Field(0.0, description="MAE误差")
    comparison: List[dict] = Field(default_factory=list, description="对比数据")


# ==================== 数据预处理相关（V1.0兼容） ====================
class PreprocessRequest(BaseModel):
    file_id: Optional[int] = None
    clean_rules: Optional[dict] = Field(default_factory=dict, description="清洗规则配置")


# ============================================================
# V2.0 新增 Schema
# ============================================================
class SportShareEstimateRequest(BaseModel):
    enterprise_id: Optional[int] = None
    credit_code: Optional[str] = None
    recognition_result: Optional[dict] = Field(None, description="识别结果(如已缓存可直接传入)")
    force_recalculate: bool = Field(False, description="是否强制重新计算")


class SportShareResultOut(BaseModel):
    id: Optional[int] = None
    enterprise_id: Optional[int] = None
    credit_code: Optional[str] = None
    enterprise_name: Optional[str] = None
    model_share: float = Field(0.0, description="模型预测比重")
    share_band: str = Field("", description="比重档位")
    share_band_label: str = Field("", description="比重档位中文标签")
    lower_bound: Optional[float] = Field(None, description="预测区间下限")
    upper_bound: Optional[float] = Field(None, description="预测区间上限")
    model_confidence: float = Field(0.0, description="模型置信度")
    main_factors: List[str] = Field(default_factory=list, description="主要影响因素")
    manual_share: Optional[float] = Field(None, description="人工核定比重")
    is_manual_adjusted: bool = False
    sport_category: Optional[str] = None
    industry_code: Optional[str] = None

    class Config:
        from_attributes = True


class SportShareManualAdjustRequest(BaseModel):
    share_result_id: int = Field(..., description="比重结果ID")
    manual_share: float = Field(..., description="人工核定比重值(0-1)")
    adjusted_by: str = Field(..., description="校准人员")
    reason: str = Field("", description="校准理由")


class SportShareStatsOut(BaseModel):
    total_enterprises: int = 0
    estimated_count: int = 0
    avg_share: float = 0.0
    band_distribution: dict = Field(default_factory=dict, description="各档位分布")
    category_avg_share: dict = Field(default_factory=dict, description="分业态平均比重")


# ==================== 规模测算相关 ====================
class ScaleCalculateRequest(BaseModel):
    batch_id: int = Field(..., description="批次ID")
    scale_field: str = Field("auto", description="规模字段: auto/revenue/employee/asset/capital")


class EnterpriseScaleOut(BaseModel):
    id: Optional[int] = None
    enterprise_id: Optional[int] = None
    enterprise_name: Optional[str] = None
    credit_code: Optional[str] = None
    scale_field_type: str = ""
    scale_field_value: float = 0.0
    sport_scale: float = 0.0
    sport_share_used: float = 0.0
    measurement_type: str = ""
    measurement_label: str = ""

    class Config:
        from_attributes = True


class ScaleSummaryOut(BaseModel):
    measurement_type: str = Field("", description="测算口径类型")
    measurement_label: str = Field("", description="测算口径中文标签")
    coverage_rate: float = Field(0.0, description="数据覆盖率")
    total_enterprises: int = 0
    enterprises_with_scale: int = 0
    total_estimated_scale: float = 0.0
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    category_scales: List[dict] = Field(default_factory=list, description="分业态规模")
    method_comparison: Optional[dict] = Field(None, description="传统vs融合方法对比")


class RegionalScaleOut(BaseModel):
    region: str = ""
    region_type: str = ""
    total_enterprises: int = 0
    sport_enterprises: int = 0
    estimated_scale: float = 0.0
    dominant_category: str = ""
    crossover_rate: float = 0.0
    new_candidates: int = 0
    high_risk_review_count: int = 0


# ==================== 人工复核相关 ====================
class ReviewTaskGenerateRequest(BaseModel):
    batch_id: int = Field(..., description="批次ID")
    recognition_results: Optional[List[dict]] = Field(None, description="识别结果列表")


class ReviewTaskOut(BaseModel):
    id: Optional[int] = None
    enterprise_id: Optional[int] = None
    credit_code: Optional[str] = None
    enterprise_name: Optional[str] = None
    priority: str = ""
    status: str = "pending"
    status_label: str = ""
    sport_category: Optional[str] = None
    sport_share: Optional[float] = None
    industry_code: Optional[str] = None
    assigned_to_a: Optional[str] = None
    assigned_to_b: Optional[str] = None
    arbiter: Optional[str] = None
    batch_id: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReviewTaskAssignRequest(BaseModel):
    task_ids: List[int] = Field(..., description="任务ID列表")
    reviewer_a: str = Field(..., description="复核员A")
    reviewer_b: str = Field(..., description="复核员B")


class ReviewRecordSubmitRequest(BaseModel):
    review_task_id: int = Field(..., description="复核任务ID")
    reviewer_name: str = Field(..., description="复核人员")
    reviewer_role: str = Field("A", description="角色: A/B")
    sport_attribute: str = Field(..., description="体育属性: yes/no/uncertain")
    sport_category_override: Optional[str] = Field(None, description="修正业态")
    sport_share_override: Optional[float] = Field(None, description="修正比重")
    reason: str = Field("", description="判断理由")
    evidence_attachment: Optional[str] = Field(None, description="证据附件路径")
    need_further_investigation: bool = False


class ReviewRecordOut(BaseModel):
    id: Optional[int] = None
    review_task_id: Optional[int] = None
    reviewer_name: str = ""
    reviewer_role: str = ""
    sport_attribute: str = ""
    sport_category_override: Optional[str] = None
    sport_share_override: Optional[float] = None
    reason: str = ""
    need_further_investigation: bool = False
    reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ArbitrationRequest(BaseModel):
    review_task_id: int = Field(..., description="复核任务ID")
    arbiter_name: str = Field(..., description="仲裁员")
    final_sport_attribute: str = Field(..., description="最终体育属性: yes/no/uncertain")
    final_sport_category: Optional[str] = Field(None, description="最终体育业态")
    final_sport_share: Optional[float] = Field(None, description="最终SportShare")
    decision_reason: str = Field("", description="裁决理由")


class ArbitrationRecordOut(BaseModel):
    id: Optional[int] = None
    review_task_id: Optional[int] = None
    arbiter_name: str = ""
    reviewer_a_opinion: str = ""
    reviewer_b_opinion: str = ""
    final_sport_attribute: str = ""
    final_sport_category: Optional[str] = None
    final_sport_share: Optional[float] = None
    decision_reason: str = ""
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReviewStatsOut(BaseModel):
    total_tasks: int = 0
    pending: int = 0
    assigned: int = 0
    reviewing: int = 0
    disputed: int = 0
    confirmed: int = 0
    locked: int = 0
    p1_count: int = 0
    p2_count: int = 0
    p3_count: int = 0
    p4_count: int = 0
    consensus_rate: float = 0.0
    arbitration_rate: float = 0.0


# ==================== 批次管理相关 ====================
class BatchCreateRequest(BaseModel):
    data_mode: str = Field("formal", description="数据模式: formal/demo")
    file_name: Optional[str] = Field(None, description="原始文件名")
    file_hash: Optional[str] = Field(None, description="文件SHA256")
    total_rows: int = Field(0, description="总行数")
    operator_name: Optional[str] = Field(None, description="操作人员")


class BatchOut(BaseModel):
    id: Optional[int] = None
    batch_number: str = ""
    data_mode: str = "formal"
    data_mode_label: str = ""
    data_version: Optional[str] = None
    model_version: Optional[str] = None
    dictionary_version: Optional[str] = None
    file_hash: Optional[str] = None
    file_name: Optional[str] = None
    total_rows: int = 0
    sport_count: int = 0
    operator_name: Optional[str] = None
    status: str = "processing"
    status_label: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BatchCompareOut(BaseModel):
    batch_a: Optional[BatchOut] = None
    batch_b: Optional[BatchOut] = None
    new_enterprises: int = 0
    removed_enterprises: int = 0
    category_changes: int = 0
    share_changes: int = 0
    scale_change: float = 0.0
