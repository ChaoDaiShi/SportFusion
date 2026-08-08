"""Phase 3 model and scale tables

Revision ID: 2d865fc0002
Revises: 1d865fc0001
Create Date: 2026-08-09

Adds:
    - sportshare_model_artifacts
    - sportshare_predictions
    - macro_calibrations
    - scenario_runs
    - validation_runs
    - benchmark_runs
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "2d865fc0002"
down_revision: str | Sequence[str] | None = "1d865fc0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ---- SportShare model artifacts ----
    op.create_table(
        "sportshare_model_artifacts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("model_version", sa.String(50), nullable=False, comment="模型版本"),
        sa.Column("artifact_path", sa.String(500), nullable=True, comment="序列化模型路径"),
        sa.Column("feature_names", sa.Text(), nullable=True, comment="特征名JSON"),
        sa.Column("random_state", sa.Integer(), nullable=True),
        sa.Column("n_estimators", sa.Integer(), nullable=True),
        sa.Column("training_samples", sa.Integer(), nullable=True),
        sa.Column("training_dataset_version", sa.String(50), nullable=True),
        sa.Column("feature_schema_version", sa.String(50), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True, comment="完整元数据JSON"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_version"),
    )

    # ---- SportShare predictions ----
    op.create_table(
        "sportshare_predictions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("enterprise_id", sa.String(100), nullable=True),
        sa.Column("credit_code", sa.String(50), nullable=True),
        sa.Column("model_share", sa.Float(), nullable=True, comment="模型估计比重"),
        sa.Column("fallback_share", sa.Float(), nullable=True, comment="回退估计比重"),
        sa.Column("manual_share", sa.Float(), nullable=True, comment="人工核定比重"),
        sa.Column("effective_share", sa.Float(), nullable=True, comment="最终有效比重"),
        sa.Column("share_source", sa.String(20), nullable=True, comment="model/fallback/manual"),
        sa.Column("lower_bound", sa.Float(), nullable=True),
        sa.Column("upper_bound", sa.Float(), nullable=True),
        sa.Column("model_version", sa.String(50), nullable=True),
        sa.Column("residual_q90", sa.Float(), nullable=True),
        sa.Column("sport_score", sa.Float(), nullable=True),
        sa.Column("sport_category", sa.String(50), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # ---- Macro calibration runs ----
    op.create_table(
        "macro_calibrations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("region", sa.String(50), nullable=False),
        sa.Column("region_code", sa.String(20), nullable=True),
        sa.Column("official_total_output", sa.Float(), nullable=False, comment="官方总量(亿元)"),
        sa.Column("unit", sa.String(10), nullable=True),
        sa.Column("source", sa.String(200), nullable=True),
        sa.Column("source_version", sa.String(50), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # ---- Scenario runs ----
    op.create_table(
        "scenario_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("scenario_id", sa.String(50), nullable=False),
        sa.Column("evidence_calibration", sa.String(20), nullable=True),
        sa.Column("alpha", sa.Float(), nullable=True),
        sa.Column("total_allocated", sa.Float(), nullable=True),
        sa.Column("category_outputs_json", sa.Text(), nullable=True),
        sa.Column("region_outputs_json", sa.Text(), nullable=True),
        sa.Column("boundary_outputs_json", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("provenance_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # ---- Validation runs ----
    op.create_table(
        "validation_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("validation_type", sa.String(30), nullable=False, comment="binary/category/ablation/threshold"),
        sa.Column("metrics_json", sa.Text(), nullable=True, comment="评估指标JSON"),
        sa.Column("artifact_version", sa.String(50), nullable=True),
        sa.Column("n_samples", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # ---- Benchmark runs ----
    op.create_table(
        "benchmark_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("dataset_rows", sa.Integer(), nullable=True),
        sa.Column("wall_time_seconds", sa.Float(), nullable=True),
        sa.Column("records_per_sec", sa.Float(), nullable=True),
        sa.Column("n_warmups", sa.Integer(), nullable=True),
        sa.Column("n_repeats", sa.Integer(), nullable=True),
        sa.Column("hardware", sa.String(100), nullable=True),
        sa.Column("python_version", sa.String(20), nullable=True),
        sa.Column("commit_sha", sa.String(40), nullable=True),
        sa.Column("model_version", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("benchmark_runs")
    op.drop_table("validation_runs")
    op.drop_table("scenario_runs")
    op.drop_table("macro_calibrations")
    op.drop_table("sportshare_predictions")
    op.drop_table("sportshare_model_artifacts")
