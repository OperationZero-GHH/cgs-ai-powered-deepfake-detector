"""Retire point balances and remove the associated guest quota signals."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006_retire_credits"
down_revision = "0005_guest_credits_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP POLICY IF EXISTS credit_transactions_access ON credit_transactions")
        op.execute("DROP POLICY IF EXISTS credit_wallets_access ON credit_wallets")
        op.execute("DROP TRIGGER IF EXISTS credit_transactions_immutable ON credit_transactions")
        op.execute("DROP FUNCTION IF EXISTS reject_credit_ledger_mutation()")
        op.execute("DROP POLICY IF EXISTS guest_sessions_access ON guest_sessions")
        op.execute(
            """CREATE POLICY guest_sessions_access ON guest_sessions FOR ALL
            USING (
                current_setting('cgs.actor', true) IN ('admin','auth','worker')
                OR guest_id = NULLIF(current_setting('cgs.guest_id', true), '')
            )
            WITH CHECK (
                current_setting('cgs.actor', true) IN ('admin','auth','worker')
                OR guest_id = NULLIF(current_setting('cgs.guest_id', true), '')
            )"""
        )
        op.execute("DROP POLICY IF EXISTS ip_enforcement_guards_service ON ip_enforcement_guards")
        op.execute(
            """CREATE POLICY ip_enforcement_guards_service ON ip_enforcement_guards FOR ALL
            USING (current_setting('cgs.actor', true) IN ('admin','auth','guest'))
            WITH CHECK (
                current_setting('cgs.actor', true) IN ('admin','auth','guest')
            )"""
        )
        op.execute("DROP POLICY IF EXISTS access_audit_insert ON access_audit_events")
        op.execute(
            """CREATE POLICY access_audit_insert ON access_audit_events FOR INSERT
            WITH CHECK (
                current_setting('cgs.actor', true) IN ('admin','auth','guest','worker')
            )"""
        )
    elif bind.dialect.name == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS credit_transactions_no_update")
        op.execute("DROP TRIGGER IF EXISTS credit_transactions_no_delete")

    # Keep the old ledger records for audit recovery, but move them outside the
    # live schema and deny application access through forced RLS on PostgreSQL.
    op.rename_table("credit_transactions", "retired_usage_transactions")
    op.rename_table("credit_wallets", "retired_usage_wallets")
    if bind.dialect.name == "postgresql":
        for table in ("retired_usage_wallets", "retired_usage_transactions"):
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
            op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    for name in (
        "ix_guest_sessions_fingerprint_hash",
        "ix_guest_sessions_ip_subnet_hash",
        "ix_guest_sessions_ip_hash",
    ):
        op.drop_index(name, table_name="guest_sessions")
    with op.batch_alter_table("guest_sessions") as batch:
        batch.drop_column("fingerprint_hash")
        batch.drop_column("ip_subnet_hash")
        batch.drop_column("ip_hash")
        batch.drop_column("verifications_used")

    op.create_index(
        "uq_analyses_user_idempotency_key",
        "analyses",
        ["owner_id", "idempotency_key"],
        unique=True,
    )
    op.create_index(
        "uq_analyses_guest_idempotency_key",
        "analyses",
        ["guest_id", "idempotency_key"],
        unique=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    op.drop_index("uq_analyses_guest_idempotency_key", table_name="analyses")
    op.drop_index("uq_analyses_user_idempotency_key", table_name="analyses")

    with op.batch_alter_table("guest_sessions") as batch:
        batch.add_column(sa.Column("ip_hash", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("ip_subnet_hash", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("fingerprint_hash", sa.String(length=64), nullable=True))
        batch.add_column(
            sa.Column("verifications_used", sa.Integer(), nullable=False, server_default="0")
        )
    for name, column in (
        ("ix_guest_sessions_ip_hash", "ip_hash"),
        ("ix_guest_sessions_ip_subnet_hash", "ip_subnet_hash"),
        ("ix_guest_sessions_fingerprint_hash", "fingerprint_hash"),
    ):
        op.create_index(name, "guest_sessions", [column])

    op.rename_table("retired_usage_wallets", "credit_wallets")
    op.rename_table("retired_usage_transactions", "credit_transactions")
    if bind.dialect.name == "postgresql":
        op.execute(
            """CREATE POLICY credit_wallets_access ON credit_wallets FOR ALL
            USING (
                current_setting('cgs.actor', true) IN ('admin','credits')
                OR (owner_type='user' AND
                    owner_id=NULLIF(current_setting('cgs.user_id', true), ''))
                OR (owner_type='guest' AND
                    owner_id=NULLIF(current_setting('cgs.guest_id', true), ''))
            )
            WITH CHECK (
                current_setting('cgs.actor', true) IN ('admin','credits')
                OR (owner_type='user' AND
                    owner_id=NULLIF(current_setting('cgs.user_id', true), ''))
                OR (owner_type='guest' AND
                    owner_id=NULLIF(current_setting('cgs.guest_id', true), ''))
            )"""
        )
        op.execute(
            """CREATE POLICY credit_transactions_access ON credit_transactions FOR ALL
            USING (
                current_setting('cgs.actor', true) IN ('admin','credits')
                OR EXISTS (
                    SELECT 1
                    FROM credit_wallets w
                    WHERE w.id=credit_transactions.wallet_id
                        AND (
                            (w.owner_type='user' AND
                                w.owner_id=NULLIF(current_setting('cgs.user_id', true), ''))
                            OR (w.owner_type='guest' AND
                                w.owner_id=NULLIF(current_setting('cgs.guest_id', true), ''))
                        )
                )
            )
            WITH CHECK (current_setting('cgs.actor', true) IN ('admin','credits'))"""
        )
        op.execute("DROP POLICY IF EXISTS guest_sessions_access ON guest_sessions")
        op.execute(
            """CREATE POLICY guest_sessions_access ON guest_sessions FOR ALL
            USING (
                current_setting('cgs.actor', true) IN ('admin','auth','worker','credits')
                OR guest_id = NULLIF(current_setting('cgs.guest_id', true), '')
            )
            WITH CHECK (
                current_setting('cgs.actor', true) IN ('admin','auth','worker','credits')
                OR guest_id = NULLIF(current_setting('cgs.guest_id', true), '')
            )"""
        )
        op.execute("DROP POLICY IF EXISTS ip_enforcement_guards_service ON ip_enforcement_guards")
        op.execute(
            """CREATE POLICY ip_enforcement_guards_service ON ip_enforcement_guards FOR ALL
            USING (current_setting('cgs.actor', true) IN ('admin','auth','credits','guest'))
            WITH CHECK (
                current_setting('cgs.actor', true) IN ('admin','auth','credits','guest')
            )"""
        )
        op.execute("DROP POLICY IF EXISTS access_audit_insert ON access_audit_events")
        op.execute(
            """CREATE POLICY access_audit_insert ON access_audit_events FOR INSERT
            WITH CHECK (
                current_setting('cgs.actor', true) IN ('admin','auth','guest','credits','worker')
            )"""
        )
        op.execute(
            "CREATE FUNCTION reject_credit_ledger_mutation() RETURNS trigger LANGUAGE "
            "plpgsql AS $$ BEGIN RAISE EXCEPTION 'credit ledger is append-only'; END $$"
        )
        op.execute(
            "CREATE TRIGGER credit_transactions_immutable BEFORE UPDATE OR DELETE ON "
            "credit_transactions FOR EACH ROW EXECUTE FUNCTION "
            "reject_credit_ledger_mutation()"
        )
        for table in ("credit_wallets", "credit_transactions"):
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
            op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    elif bind.dialect.name == "sqlite":
        op.execute(
            "CREATE TRIGGER credit_transactions_no_update BEFORE UPDATE ON "
            "credit_transactions BEGIN SELECT RAISE(ABORT, 'credit ledger is "
            "append-only'); END"
        )
        op.execute(
            "CREATE TRIGGER credit_transactions_no_delete BEFORE DELETE ON "
            "credit_transactions BEGIN SELECT RAISE(ABORT, 'credit ledger is "
            "append-only'); END"
        )
