"""Add signup attribution, administrator invitations, and separated activity logs."""

import sqlalchemy as sa
from alembic import op

revision = "0009_admin_workforce_and_logs"
down_revision = "0008_admin_console_management"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "signup_method", sa.String(length=32), nullable=False, server_default="email_password"
        ),
    )
    op.add_column("users", sa.Column("signup_ip", sa.String(length=45), nullable=True))

    op.create_table(
        "user_activity_events",
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
    for name, column in (
        ("actor_id", "actor_id"),
        ("action", "action"),
        ("subject_id", "subject_id"),
        ("created_at", "created_at"),
    ):
        op.create_index(f"ix_user_activity_events_{name}", "user_activity_events", [column])

    op.create_table(
        "admin_invitations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "invited_by",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_admin_invitations_email", "admin_invitations", ["email"])
    op.create_index(
        "ix_admin_invitations_token_hash", "admin_invitations", ["token_hash"], unique=True
    )
    op.create_index("ix_admin_invitations_expires_at", "admin_invitations", ["expires_at"])

    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE user_activity_events ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE user_activity_events FORCE ROW LEVEL SECURITY")
        op.execute(
            "CREATE POLICY user_activity_admin_read ON user_activity_events FOR SELECT USING "
            "(current_setting('cgs.actor', true) = 'admin')"
        )
        op.execute(
            "CREATE POLICY user_activity_application_insert ON user_activity_events FOR "
            "INSERT WITH CHECK (current_setting('cgs.actor', true) IN ('auth', 'admin') "
            "OR actor_id = NULLIF(current_setting('cgs.user_id', true), ''))"
        )
        op.execute(
            "CREATE POLICY user_activity_admin_delete ON user_activity_events FOR DELETE "
            "USING (current_setting('cgs.actor', true) = 'admin')"
        )

        op.execute("ALTER TABLE admin_invitations ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE admin_invitations FORCE ROW LEVEL SECURITY")
        op.execute(
            "CREATE POLICY admin_invitations_admin_all ON admin_invitations FOR ALL USING "
            "(current_setting('cgs.actor', true) = 'admin') WITH CHECK "
            "(current_setting('cgs.actor', true) = 'admin')"
        )
        op.execute("""
            CREATE POLICY admin_invitations_accept_read ON admin_invitations FOR SELECT
            USING (
                token_hash = NULLIF(current_setting('cgs.admin_invite_hash', true), '')
                AND accepted_at IS NULL AND canceled_at IS NULL AND expires_at > now()
            )
        """)
        op.execute("""
            CREATE POLICY admin_invitations_accept_update ON admin_invitations FOR UPDATE
            USING (
                token_hash = NULLIF(current_setting('cgs.admin_invite_hash', true), '')
                AND accepted_at IS NULL AND canceled_at IS NULL AND expires_at > now()
            )
            WITH CHECK (
                token_hash = NULLIF(current_setting('cgs.admin_invite_hash', true), '')
                AND accepted_at IS NOT NULL AND canceled_at IS NULL
            )
        """)


def downgrade() -> None:
    # Retain invitation and activity records during code rollback.
    pass
