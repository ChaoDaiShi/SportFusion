"""数据库表结构定义（SQLAlchemy ORM）"""
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class Enterprise(Base):
    """企业基本信息表"""
    __tablename__ = "enterprises"

    id = Column(Integer, primary_key=True, autoincrement=True)
    credit_code = Column(String(50), comment="统一社会信用代码")
    name = Column(String(200), nullable=False, comment="企业名称")
    region = Column(String(100), comment="所在区域")
    city = Column(String(50), comment="市州")
    district = Column(String(50), comment="区县")
    industry_code = Column(String(20), comment="行业代码")
    main_business = Column(Text, comment="主营业务描述")
    total_revenue = Column(Float, default=0.0, comment="总营收（万元）")
    employee_count = Column(Integer, default=0, comment="员工人数")
    total_assets = Column(Float, default=0.0, comment="资产总额（万元）")
    registered_capital = Column(Float, default=0.0, comment="注册资本（万元）")
    scale_level = Column(String(20), comment="企业规模等级")
    longitude = Column(Float, comment="经度")
    latitude = Column(Float, comment="纬度")
    batch_id = Column(Integer, ForeignKey("batches.id"), comment="所属批次ID")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    batch = relationship("Batch", back_populates="enterprises")
    businesses = relationship("EnterpriseBusiness", back_populates="enterprise")
    measurements = relationship("Measurement", back_populates="enterprise")


class EnterpriseBusiness(Base):
    """企业体育业务识别结果表"""
    __tablename__ = "enterprise_businesses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    enterprise_id = Column(Integer, ForeignKey("enterprises.id"), nullable=False)
    sport_category = Column(String(50), comment="体育业态分类：赛事/健身/培训/用品")
    business_text = Column(Text, comment="识别的体育业务描述")
    is_crossover = Column(Integer, default=0, comment="是否跨界经营：0=否 1=是")
    sport_revenue_ratio = Column(Float, default=0.0, comment="体育营收占比")
    confidence = Column(Float, default=0.0, comment="识别置信度")
    keywords = Column(Text, comment="匹配关键词")
    created_at = Column(DateTime, default=datetime.now)

    enterprise = relationship("Enterprise", back_populates="businesses")


class Measurement(Base):
    """产值测算结果表"""
    __tablename__ = "measurements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    enterprise_id = Column(Integer, ForeignKey("enterprises.id"), nullable=False)
    enterprise_name = Column(String(200), comment="企业名称")
    region = Column(String(100), comment="区域")
    sport_category = Column(String(50), comment="业态分类")
    total_revenue = Column(Float, default=0.0, comment="总营收")
    sport_revenue = Column(Float, default=0.0, comment="测算体育产值")
    sport_ratio = Column(Float, default=0.0, comment="体育产值占比")
    created_at = Column(DateTime, default=datetime.now)

    enterprise = relationship("Enterprise", back_populates="measurements")


class DataSource(Base):
    """原始数据源记录表"""
    __tablename__ = "data_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(200), comment="文件名")
    file_type = Column(String(20), comment="文件类型")
    row_count = Column(Integer, default=0, comment="数据行数")
    status = Column(String(20), default="pending", comment="处理状态")
    uploaded_at = Column(DateTime, default=datetime.now)


class ModelMetric(Base):
    """模型校验指标表"""
    __tablename__ = "model_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    metric_name = Column(String(50), comment="指标名称")
    metric_value = Column(Float, comment="指标值")
    description = Column(String(200), comment="指标说明")
    created_at = Column(DateTime, default=datetime.now)


# ============================================================
# V2.0 新增表 — 批次管理 / 比重测算 / 规模测算 / 人工复核 / 审计
# ============================================================

class Batch(Base):
    """数据批次表 — 每次数据导入/处理创建一个批次"""
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_number = Column(String(50), unique=True, nullable=False, comment="批次号 BATCH-YYYYMMDD-NNN")
    data_mode = Column(String(10), default="formal", comment="数据模式: formal/demo")
    data_version = Column(String(20), comment="数据版本")
    model_version = Column(String(20), comment="模型版本")
    dictionary_version = Column(String(20), comment="词典版本")
    code_map_version = Column(String(20), comment="代码映射版本")
    share_model_version = Column(String(20), comment="比重模型版本")
    param_version = Column(String(50), comment="参数版本")
    runtime_env = Column(Text, comment="运行环境信息")
    file_hash = Column(String(64), comment="上传文件SHA256哈希")
    file_name = Column(String(300), comment="原始文件名")
    total_rows = Column(Integer, default=0, comment="数据总行数")
    sport_count = Column(Integer, default=0, comment="识别为体育企业的数量")
    operator_name = Column(String(100), comment="操作人员")
    status = Column(String(20), default="processing", comment="状态: importing/processing/completed/locked/archived")
    start_time = Column(DateTime, default=datetime.now, comment="开始处理时间")
    end_time = Column(DateTime, comment="结束时间")
    created_at = Column(DateTime, default=datetime.now)

    # 关联
    enterprises = relationship("Enterprise", back_populates="batch")
    recognition_results = relationship("RecognitionResultV2", back_populates="batch")
    share_results = relationship("SportShareResult", back_populates="batch")
    scale_results = relationship("EnterpriseScale", back_populates="batch")
    review_tasks = relationship("ReviewTask", back_populates="batch")


class RecognitionResultV2(Base):
    """边界识别结果表（V2.0 — 完整字段持久化）"""
    __tablename__ = "recognition_results_v2"

    id = Column(Integer, primary_key=True, autoincrement=True)
    enterprise_id = Column(Integer, ForeignKey("enterprises.id"), comment="关联企业ID")
    credit_code = Column(String(50), comment="统一社会信用代码")
    sport_category = Column(String(50), comment="体育业态分类")
    is_sport = Column(Integer, default=0, comment="是否体育企业: 0=否 1=是")
    is_crossover = Column(Integer, default=0, comment="是否跨界: 0=否 1=是")
    crossover_type = Column(String(100), comment="跨界类型描述")
    code_type = Column(String(20), comment="行业代码类型: direct/indirect/none")
    code_text_consistency = Column(String(30), comment="代码-文本一致性: consistent/partial/conflict/unknown")
    sport_score = Column(Float, default=0.0, comment="SportScore综合得分")
    w1_business_scope = Column(Float, default=0.0, comment="W1业务范围占比")
    w2_keyword_density = Column(Float, default=0.0, comment="W2关键词密度")
    w3_code_weight = Column(Float, default=0.0, comment="W3行业代码权重")
    w4_category_coverage = Column(Float, default=0.0, comment="W4业态覆盖度")
    confidence = Column(Float, default=0.0, comment="识别置信度")
    total_business_lines = Column(Integer, default=0, comment="总业务线数")
    sport_business_lines = Column(Integer, default=0, comment="体育业务线数")
    keywords = Column(Text, comment="匹配关键词(JSON数组)")
    sport_lines_detail = Column(Text, comment="体育业务线详情(JSON)")
    non_sport_lines = Column(Text, comment="非体育业务线(JSON)")
    model_version = Column(String(20), comment="模型版本")
    batch_id = Column(Integer, ForeignKey("batches.id"), comment="批次ID")
    created_at = Column(DateTime, default=datetime.now)

    enterprise = relationship("Enterprise")
    batch = relationship("Batch", back_populates="recognition_results")


class SportShareResult(Base):
    """体育经营活动比重测算结果表"""
    __tablename__ = "sport_share_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    enterprise_id = Column(Integer, ForeignKey("enterprises.id"), comment="关联企业ID")
    credit_code = Column(String(50), comment="统一社会信用代码")
    model_share = Column(Float, default=0.0, comment="模型预测比重(0-1)")
    share_band = Column(String(20), comment="比重档位: very_low/low/medium/medium_high/high")
    lower_bound = Column(Float, comment="预测区间下限")
    upper_bound = Column(Float, comment="预测区间上限")
    model_confidence = Column(Float, default=0.0, comment="模型置信度(0-1)")
    main_factors = Column(Text, comment="主要影响因素(JSON数组)")
    manual_share = Column(Float, comment="人工核定比重")
    is_manual_adjusted = Column(Integer, default=0, comment="是否经过人工校准: 0=否 1=是")
    adjusted_by = Column(String(100), comment="校准人员")
    adjusted_reason = Column(Text, comment="校准理由")
    share_model_version = Column(String(20), comment="比重模型版本")
    batch_id = Column(Integer, ForeignKey("batches.id"), comment="批次ID")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    enterprise = relationship("Enterprise")
    batch = relationship("Batch", back_populates="share_results")


class EnterpriseScale(Base):
    """企业体育业务规模测算表"""
    __tablename__ = "enterprise_scales"

    id = Column(Integer, primary_key=True, autoincrement=True)
    enterprise_id = Column(Integer, ForeignKey("enterprises.id"), comment="关联企业ID")
    credit_code = Column(String(50), comment="统一社会信用代码")
    scale_field_type = Column(String(30), comment="使用的规模字段: revenue/employee/asset/capital")
    scale_field_value = Column(Float, default=0.0, comment="规模字段原始值")
    sport_scale = Column(Float, default=0.0, comment="体育业务规模（规模字段值×SportShare）")
    sport_share_used = Column(Float, default=0.0, comment="使用的SportShare值")
    measurement_type = Column(String(30), comment="测算口径: formal/proxy/relative_index")
    batch_id = Column(Integer, ForeignKey("batches.id"), comment="批次ID")
    created_at = Column(DateTime, default=datetime.now)

    enterprise = relationship("Enterprise")
    batch = relationship("Batch", back_populates="scale_results")


class RegionalScaleResult(Base):
    """区域体育产业规模汇总表"""
    __tablename__ = "regional_scale_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    region = Column(String(100), comment="区域名称（市州/区县）")
    region_type = Column(String(20), comment="区域类型: city/district")
    total_enterprises = Column(Integer, default=0, comment="区域内候选企业总数")
    sport_enterprises = Column(Integer, default=0, comment="区域内体育企业数")
    estimated_scale = Column(Float, default=0.0, comment="体育产业估算规模")
    dominant_category = Column(String(50), comment="主导体育业态")
    crossover_rate = Column(Float, default=0.0, comment="跨界率")
    new_candidates = Column(Integer, default=0, comment="相较传统方法新增候选数")
    high_risk_review_count = Column(Integer, default=0, comment="高风险复核企业数(P1)")
    batch_id = Column(Integer, ForeignKey("batches.id"), comment="批次ID")
    created_at = Column(DateTime, default=datetime.now)


class ReviewTask(Base):
    """人工复核任务表"""
    __tablename__ = "review_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    enterprise_id = Column(Integer, ForeignKey("enterprises.id"), comment="关联企业ID")
    credit_code = Column(String(50), comment="统一社会信用代码")
    priority = Column(String(5), comment="复核优先级: P1/P2/P3/P4")
    status = Column(String(20), default="pending", comment="状态: pending/assigned/reviewing/disputed/confirmed/info_insufficient/locked")
    assigned_to_a = Column(String(100), comment="复核员A")
    assigned_to_b = Column(String(100), comment="复核员B")
    arbiter = Column(String(100), comment="仲裁员")
    batch_id = Column(Integer, ForeignKey("batches.id"), comment="批次ID")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    enterprise = relationship("Enterprise")
    batch = relationship("Batch", back_populates="review_tasks")
    records = relationship("ReviewRecord", back_populates="review_task")


class ReviewRecord(Base):
    """复核意见记录表"""
    __tablename__ = "review_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    review_task_id = Column(Integer, ForeignKey("review_tasks.id"), comment="关联复核任务ID")
    reviewer_name = Column(String(100), comment="复核人员")
    reviewer_role = Column(String(10), comment="角色: A/B")
    sport_attribute = Column(String(20), comment="体育属性判定: yes/no/uncertain")
    sport_category_override = Column(String(50), comment="修正后的体育业态")
    sport_share_override = Column(Float, comment="修正后的SportShare值")
    reason = Column(Text, comment="判断理由")
    evidence_attachment = Column(Text, comment="证据附件路径")
    need_further_investigation = Column(Integer, default=0, comment="是否需要补充调查: 0=否 1=是")
    reviewed_at = Column(DateTime, default=datetime.now)

    review_task = relationship("ReviewTask", back_populates="records")


class ArbitrationRecord(Base):
    """分歧仲裁记录表"""
    __tablename__ = "arbitration_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    review_task_id = Column(Integer, ForeignKey("review_tasks.id"), comment="关联复核任务ID")
    arbiter_name = Column(String(100), comment="仲裁员")
    reviewer_a_opinion = Column(Text, comment="复核员A意见摘要")
    reviewer_b_opinion = Column(Text, comment="复核员B意见摘要")
    final_sport_attribute = Column(String(20), comment="最终体育属性判定")
    final_sport_category = Column(String(50), comment="最终体育业态")
    final_sport_share = Column(Float, comment="最终SportShare值")
    decision_reason = Column(Text, comment="裁决理由")
    created_at = Column(DateTime, default=datetime.now)


class OperationLog(Base):
    """操作审计日志表"""
    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_name = Column(String(100), comment="操作人员")
    action = Column(String(50), comment="操作类型: CREATE/UPDATE/DELETE/EXPORT/REVIEW/ARBITRATE")
    target_type = Column(String(50), comment="操作目标类型")
    target_id = Column(Integer, comment="操作目标ID")
    detail = Column(Text, comment="操作详情(JSON)")
    ip_address = Column(String(50), comment="IP地址")
    created_at = Column(DateTime, default=datetime.now)
