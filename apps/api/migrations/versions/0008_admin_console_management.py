"""Persist contact inquiries and typed platform controls for administrators."""

from alembic import op
import sqlalchemy as sa


revision = "0008_admin_console_management"
down_revision = "0007_repair_adopted_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contact_inquiries",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("topic", sa.String(length=100), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="new"),
        sa.Column("admin_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_contact_inquiries_email", "contact_inquiries", ["email"])
    op.create_index("ix_contact_inquiries_status", "contact_inquiries", ["status"])
    op.create_index("ix_contact_inquiries_created_at", "contact_inquiries", ["created_at"])

    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(length=64), primary_key=True),
        sa.Column("value_json", sa.Text(), nullable=False),
        sa.Column("updated_by", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE contact_inquiries ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE contact_inquiries FORCE ROW LEVEL SECURITY")
        op.execute("CREATE POLICY contact_inquiries_public_submit ON contact_inquiries FOR INSERT WITH CHECK (true)")
        op.execute("CREATE POLICY contact_inquiries_admin_read ON contact_inquiries FOR SELECT USING (current_setting('cgs.actor', true) = 'admin')")
        op.execute("CREATE POLICY contact_inquiries_admin_update ON contact_inquiries FOR UPDATE USING (current_setting('cgs.actor', true) = 'admin') WITH CHECK (current_setting('cgs.actor', true) = 'admin')")

        op.execute("ALTER TABLE system_settings ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE system_settings FORCE ROW LEVEL SECURITY")
        op.execute("CREATE POLICY system_settings_runtime_read ON system_settings FOR SELECT USING (true)")
        op.execute("CREATE POLICY system_settings_admin_insert ON system_settings FOR INSERT WITH CHECK (current_setting('cgs.actor', true) = 'admin')")
        op.execute("CREATE POLICY system_settings_admin_update ON system_settings FOR UPDATE USING (current_setting('cgs.actor', true) = 'admin') WITH CHECK (current_setting('cgs.actor', true) = 'admin')")
        op.execute("CREATE POLICY system_settings_admin_delete ON system_settings FOR DELETE USING (current_setting('cgs.actor', true) = 'admin')")


def downgrade() -> None:
    # Keep submitted inquiries and the applied controls when rolling back code.
    pass
