"""SQLAlchemy metadata for migration-managed persistence tables.

The Phase 3 and Phase 4 repositories use SQL directly, but Alembic still
needs these tables represented in ``Base.metadata`` to detect real schema
drift. Keep this projection aligned with revisions 2d865fc0002 and
3d865fc0003.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Table,
    Text,
    func,
)

from .database import Base

sportshare_model_artifacts = Table(
    "sportshare_model_artifacts",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("model_version", String(50), nullable=False, unique=True),
    Column("artifact_path", String(500)),
    Column("feature_names", Text),
    Column("random_state", Integer),
    Column("n_estimators", Integer),
    Column("training_samples", Integer),
    Column("training_dataset_version", String(50)),
    Column("feature_schema_version", String(50)),
    Column("metadata_json", Text),
    Column("created_at", DateTime, server_default=func.now()),
)

sportshare_predictions = Table(
    "sportshare_predictions",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("enterprise_id", String(100)),
    Column("credit_code", String(50)),
    Column("model_share", Float),
    Column("fallback_share", Float),
    Column("manual_share", Float),
    Column("effective_share", Float),
    Column("share_source", String(20)),
    Column("lower_bound", Float),
    Column("upper_bound", Float),
    Column("model_version", String(50)),
    Column("residual_q90", Float),
    Column("sport_score", Float),
    Column("sport_category", String(50)),
    Column("metadata_json", Text),
    Column("created_at", DateTime, server_default=func.now()),
)

macro_calibrations = Table(
    "macro_calibrations",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("year", Integer, nullable=False),
    Column("region", String(50), nullable=False),
    Column("region_code", String(20)),
    Column("official_total_output", Float, nullable=False),
    Column("unit", String(10)),
    Column("source", String(200)),
    Column("source_version", String(50)),
    Column("metadata_json", Text),
    Column("created_at", DateTime, server_default=func.now()),
)

scenario_runs = Table(
    "scenario_runs",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("scenario_id", String(50), nullable=False),
    Column("evidence_calibration", String(20)),
    Column("alpha", Float),
    Column("total_allocated", Float),
    Column("category_outputs_json", Text),
    Column("region_outputs_json", Text),
    Column("boundary_outputs_json", Text),
    Column("status", String(20)),
    Column("provenance_json", Text),
    Column("created_at", DateTime, server_default=func.now()),
)

validation_runs = Table(
    "validation_runs",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("validation_type", String(30), nullable=False),
    Column("metrics_json", Text),
    Column("artifact_version", String(50)),
    Column("n_samples", Integer),
    Column("metadata_json", Text),
    Column("created_at", DateTime, server_default=func.now()),
)

benchmark_runs = Table(
    "benchmark_runs",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("dataset_rows", Integer),
    Column("wall_time_seconds", Float),
    Column("records_per_sec", Float),
    Column("n_warmups", Integer),
    Column("n_repeats", Integer),
    Column("hardware", String(100)),
    Column("python_version", String(20)),
    Column("commit_sha", String(40)),
    Column("model_version", String(50)),
    Column("created_at", DateTime, server_default=func.now()),
)

audit_log = Table(
    "audit_log",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("batch_id", String(50), nullable=False),
    Column("actor", String(50)),
    Column("action", String(50), nullable=False),
    Column("target", String(200)),
    Column("before_summary", Text),
    Column("after_summary", Text),
    Column("metadata_json", Text),
    Column("created_at", DateTime, server_default=func.now()),
)
Index("ix_audit_log_batch", audit_log.c.batch_id)

review_tasks_v2 = Table(
    "review_tasks_v2",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("task_id", String(50), nullable=False, unique=True),
    Column("batch_id", String(50), nullable=False),
    Column("enterprise_id", String(100)),
    Column("credit_code", String(50)),
    Column("enterprise_name", String(200)),
    Column("priority", String(4), nullable=False),
    Column("status", String(20)),
    Column("sport_score", Float),
    Column("sport_category", String(50)),
    Column("code_type", String(20)),
    Column("evidence_relation", String(50)),
    Column("confidence", Float),
    Column("effective_share", Float),
    Column("share_source", String(20)),
    Column("reviewer_a", String(50)),
    Column("reviewer_b", String(50)),
    Column("arbiter", String(50)),
    Column("a_result_json", Text),
    Column("b_result_json", Text),
    Column("arbiter_result_json", Text),
    Column("final_sport_attribute", String(20)),
    Column("final_sport_category", String(50)),
    Column("final_share", Float),
    Column("trigger_rules_json", Text),
    Column("risk_reasons_json", Text),
    Column("evidence_summary", Text),
    Column("created_at", DateTime, server_default=func.now()),
    Column("updated_at", DateTime),
)
Index("ix_review_batch", review_tasks_v2.c.batch_id)
Index("ix_review_priority", review_tasks_v2.c.priority)
Index("ix_review_status", review_tasks_v2.c.status)

directory_entries = Table(
    "directory_entries",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("enterprise_id", String(100)),
    Column("credit_code", String(50)),
    Column("enterprise_name", String(200)),
    Column("region", String(50)),
    Column("industry_code", String(20)),
    Column("sport_score", Float),
    Column("evidence_relation", String(50)),
    Column("model_share", Float),
    Column("manual_share", Float),
    Column("effective_share", Float),
    Column("share_source", String(20)),
    Column("sport_category", String(50)),
    Column("crossover_type", String(100)),
    Column("review_status", String(20)),
    Column("priority", String(4)),
    Column("batch_id", String(50), nullable=False),
    Column("is_finalized", Boolean, default=False),
    Column("provenance_json", Text),
    Column("created_at", DateTime, server_default=func.now()),
)
Index("ix_directory_batch", directory_entries.c.batch_id)
Index("ix_directory_finalized", directory_entries.c.is_finalized)


batches = Base.metadata.tables["batches"]
batches.append_column(Column("locked_at", DateTime))
batches.append_column(Column("locked_by", String(50)))
