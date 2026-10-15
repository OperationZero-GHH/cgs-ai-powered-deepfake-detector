"""Add unique usernames and optional phone details to users."""

from alembic import op
import sqlalchemy as sa


revision = "0004_user_contact_details"
down_revision = "0003_postgres_rls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(length=32), nullable=True))
    op.add_column("users", sa.Column("phone_number", sa.String(length=16), nullable=True))
    op.create_index("ix_users_username", "users", ["username"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_username", table_name="users")
    op.drop_column("users", "phone_number")
    op.drop_column("users", "username")
