"""Phase 4 workflow and persistence tables

Revision ID: 3d865fc0003
Revises: 2d865fc0002
Create Date: 2026-08-09

Adds:
    - audit_log
    - review_tasks (expanded)
    - directory_entries
    - batch_locks
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "3d865fc0003"
down_revision: str | Sequence[str] | None = "2d865fc0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ---- Audit log ----
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("batch_id", sa.String(50), nullable=False),
        sa.Column("actor", sa.String(50), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("target", sa.String(200), nullable=True),
        sa.Column("before_summary", sa.Text(), nullable=True),
        sa.Column("after_summary", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_log_batch", "audit_log", ["batch_id"])

    # ---- Review tasks (expanded with Phase 3 evidence) ----
    op.create_table(
        "review_tasks_v2",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.String(50), nullable=False, unique=True),
        sa.Column("batch_id", sa.String(50), nullable=False),
        sa.Column("enterprise_id", sa.String(100), nullable=True),
        sa.Column("credit_code", sa.String(50), nullable=True),
        sa.Column("enterprise_name", sa.String(200), nullable=True),
        sa.Column("priority", sa.String(4), nullable=False, comment="P1/P2/P3/P4"),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("sport_score", sa.Float(), nullable=True),
        sa.Column("sport_category", sa.String(50), nullable=True),
        sa.Column("code_type", sa.String(20), nullable=True),
        sa.Column("evidence_relation", sa.String(50), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("effective_share", sa.Float(), nullable=True),
        sa.Column("share_source", sa.String(20), nullable=True),
        sa.Column("reviewer_a", sa.String(50), nullable=True),
        sa.Column("reviewer_b", sa.String(50), nullable=True),
        sa.Column("arbiter", sa.String(50), nullable=True),
        sa.Column("a_result_json", sa.Text(), nullable=True),
        sa.Column("b_result_json", sa.Text(), nullable=True),
        sa.Column("arbiter_result_json", sa.Text(), nullable=True),
        sa.Column("final_sport_attribute", sa.String(20), nullable=True),
        sa.Column("final_sport_category", sa.String(50), nullable=True),
        sa.Column("final_share", sa.Float(), nullable=True),
        sa.Column("trigger_rules_json", sa.Text(), nullable=True),
        sa.Column("risk_reasons_json", sa.Text(), nullable=True),
        sa.Column("evidence_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_review_batch", "review_tasks_v2", ["batch_id"])
    op.create_index("ix_review_priority", "review_tasks_v2", ["priority"])
    op.create_index("ix_review_status", "review_tasks_v2", ["status"])

    # ---- Directory entries (finalized enterprises only) ----
    op.create_table(
        "directory_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("enterprise_id", sa.String(100), nullable=True),
        sa.Column("credit_code", sa.String(50), nullable=True),
        sa.Column("enterprise_name", sa.String(200), nullable=True),
        sa.Column("region", sa.String(50), nullable=True),
        sa.Column("industry_code", sa.String(20), nullable=True),
        sa.Column("sport_score", sa.Float(), nullable=True),
        sa.Column("evidence_relation", sa.String(50), nullable=True),
        sa.Column("model_share", sa.Float(), nullable=True),
        sa.Column("manual_share", sa.Float(), nullable=True),
        sa.Column("effective_share", sa.Float(), nullable=True),
        sa.Column("share_source", sa.String(20), nullable=True),
        sa.Column("sport_category", sa.String(50), nullable=True),
        sa.Column("crossover_type", sa.String(100), nullable=True),
        sa.Column("review_status", sa.String(20), nullable=True),
        sa.Column("priority", sa.String(4), nullable=True),
        sa.Column("batch_id", sa.String(50), nullable=False),
        sa.Column("is_finalized", sa.Boolean(), default=False),
        sa.Column("provenance_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_directory_batch", "directory_entries", ["batch_id"])
    op.create_index("ix_directory_finalized", "directory_entries", ["is_finalized"])

    # ---- Batch lock metadata ----
    op.add_column("batches", sa.Column("locked_at", sa.DateTime(), nullable=True))
    op.add_column("batches", sa.Column("locked_by", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("batches", "locked_by")
    op.drop_column("batches", "locked_at")
    op.drop_index("ix_directory_finalized")
    op.drop_index("ix_directory_batch")
    op.drop_table("directory_entries")
    op.drop_index("ix_review_status")
    op.drop_index("ix_review_priority")
    op.drop_index("ix_review_batch")
    op.drop_table("review_tasks_v2")
    op.drop_index("ix_audit_log_batch")
    op.drop_table("audit_log")
