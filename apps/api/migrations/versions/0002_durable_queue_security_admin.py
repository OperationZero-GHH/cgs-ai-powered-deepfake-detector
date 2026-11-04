"""Add durable inference jobs, persisted rate limits, provenance, and admin audit."""

import sqlalchemy as sa
from alembic import op

revision = "0002_queue_security_admin"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("analyses") as batch:
        batch.alter_column("completed_at", existing_type=sa.DateTime(timezone=True), nullable=True)
        batch.add_column(
            sa.Column("provenance_json", sa.Text(), nullable=False, server_default="{}")
        )

    op.create_table(
        "inference_jobs",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column(
            "analysis_id",
            sa.String(length=32),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("worker_id", sa.String(length=80), nullable=True),
        sa.Column("last_error", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_inference_jobs_analysis_id", "inference_jobs", ["analysis_id"])
    op.create_index("ix_inference_jobs_status", "inference_jobs", ["status"])
    op.create_index("ix_inference_jobs_available_at", "inference_jobs", ["available_at"])

    op.create_table(
        "rate_limit_buckets",
        sa.Column("key_hash", sa.String(length=64), primary_key=True),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("resets_at", sa.Integer(), nullable=False),
    )
    op.create_index("ix_rate_limit_buckets_resets_at", "rate_limit_buckets", ["resets_at"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column(
            "actor_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("subject_id", sa.String(length=80), nullable=True),
        sa.Column("details_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_events_actor_id", "audit_events", ["actor_id"])
    op.create_index("ix_audit_events_action", "audit_events", ["action"])
    op.create_index("ix_audit_events_subject_id", "audit_events", ["subject_id"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])

    op.create_table(
        "worker_heartbeats",
        sa.Column("worker_id", sa.String(length=80), primary_key=True),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("process_id", sa.String(length=24), nullable=False),
    )
    op.create_index("ix_worker_heartbeats_last_seen", "worker_heartbeats", ["last_seen"])


def downgrade() -> None:
    op.drop_index("ix_worker_heartbeats_last_seen", table_name="worker_heartbeats")
    op.drop_table("worker_heartbeats")
    op.drop_index("ix_audit_events_created_at", table_name="audit_events")
    op.drop_index("ix_audit_events_subject_id", table_name="audit_events")
    op.drop_index("ix_audit_events_action", table_name="audit_events")
    op.drop_index("ix_audit_events_actor_id", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_rate_limit_buckets_resets_at", table_name="rate_limit_buckets")
    op.drop_table("rate_limit_buckets")
    op.drop_index("ix_inference_jobs_available_at", table_name="inference_jobs")
    op.drop_index("ix_inference_jobs_status", table_name="inference_jobs")
    op.drop_index("ix_inference_jobs_analysis_id", table_name="inference_jobs")
    op.drop_table("inference_jobs")
    with op.batch_alter_table("analyses") as batch:
        batch.drop_column("provenance_json")
        batch.alter_column("completed_at", existing_type=sa.DateTime(timezone=True), nullable=False)
