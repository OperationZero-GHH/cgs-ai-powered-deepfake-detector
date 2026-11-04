"""Add signed guest ownership, wallet ledger, verified email, and IP controls."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005_guest_credits_auth"
down_revision = "0004_user_contact_details"
branch_labels = None
depends_on = None


def _email_identity(value: str) -> str:
    email = value.strip().casefold()
    local, separator, domain = email.rpartition("@")
    if not separator:
        return email
    if domain in {"gmail.com", "googlemail.com"}:
        local = local.split("+", 1)[0].replace(".", "")
        domain = "gmail.com"
    return f"{local}@{domain}"


def upgrade() -> None:
    bind = op.get_bind()
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("email_identity", sa.String(length=320), nullable=True))
        batch.add_column(sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(
            sa.Column("email_verification_token_hash", sa.String(length=64), nullable=True)
        )
        batch.add_column(
            sa.Column("email_verification_expires_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch.add_column(
            sa.Column("password_reset_token_hash", sa.String(length=64), nullable=True)
        )
        batch.add_column(
            sa.Column("password_reset_expires_at", sa.DateTime(timezone=True), nullable=True)
        )

    seen: set[str] = set()
    users = bind.execute(
        sa.text("SELECT id, email, created_at FROM users ORDER BY created_at, id")
    ).mappings()
    for row in users:
        identity = _email_identity(row["email"])
        if identity in seen:
            # Preserve legacy rows if aliases already exist; exact-address login still works.
            identity = f"{identity}#legacy-{row['id']}"
        seen.add(identity)
        bind.execute(
            sa.text(
                "UPDATE users SET email_identity=:identity, email_verified_at=:verified "
                "WHERE id=:id"
            ),
            {"identity": identity, "verified": row["created_at"], "id": row["id"]},
        )
    with op.batch_alter_table("users") as batch:
        batch.alter_column("email_identity", existing_type=sa.String(length=320), nullable=False)
    op.create_index("ix_users_email_identity", "users", ["email_identity"], unique=True)
    op.create_index(
        "ix_users_email_verification_token_hash", "users", ["email_verification_token_hash"]
    )
    op.create_index("ix_users_password_reset_token_hash", "users", ["password_reset_token_hash"])

    op.create_table(
        "guest_sessions",
        sa.Column("guest_id", sa.String(length=64), primary_key=True),
        sa.Column("ip_hash", sa.String(length=64), nullable=False),
        sa.Column("ip_subnet_hash", sa.String(length=64), nullable=False),
        sa.Column("fingerprint_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "linked_user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("verifications_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
    )
    for name, column in (
        ("ip_hash", "ip_hash"),
        ("ip_subnet_hash", "ip_subnet_hash"),
        ("fingerprint_hash", "fingerprint_hash"),
        ("linked_user_id", "linked_user_id"),
        ("last_seen_at", "last_seen_at"),
    ):
        op.create_index(f"ix_guest_sessions_{name}", "guest_sessions", [column])

    op.create_table(
        "credit_wallets",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("owner_type", sa.String(length=12), nullable=False),
        sa.Column("owner_id", sa.String(length=64), nullable=False),
        sa.Column("balance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("owner_type", "owner_id", name="uq_credit_wallet_owner"),
        sa.CheckConstraint("balance >= 0", name="ck_credit_wallet_nonnegative"),
    )
    op.create_index("ix_credit_wallets_owner_type", "credit_wallets", ["owner_type"])
    op.create_index("ix_credit_wallets_owner_id", "credit_wallets", ["owner_id"])
    op.create_table(
        "credit_transactions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "wallet_id",
            sa.String(length=36),
            sa.ForeignKey("credit_wallets.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("reference_id", sa.String(length=80), nullable=True),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for name, column in (
        ("wallet_id", "wallet_id"),
        ("type", "type"),
        ("reference_id", "reference_id"),
        ("idempotency_key", "idempotency_key"),
        ("created_at", "created_at"),
    ):
        op.create_index(
            f"ix_credit_transactions_{name}",
            "credit_transactions",
            [column],
            unique=column == "idempotency_key",
        )
    if bind.dialect.name == "sqlite":
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

    op.create_table(
        "ip_account_links",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("ip_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("ip_hash", "user_id", name="uq_ip_account_link"),
    )
    op.create_index("ix_ip_account_links_ip_hash", "ip_account_links", ["ip_hash"])
    op.create_index("ix_ip_account_links_user_id", "ip_account_links", ["user_id"])
    op.create_index("ix_ip_account_links_last_seen_at", "ip_account_links", ["last_seen_at"])
    op.create_table(
        "ip_enforcement_guards",
        sa.Column("ip_hash", sa.String(length=64), primary_key=True),
        sa.Column("touch_count", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "ip_blocks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("ip_hash", sa.String(length=64), nullable=False),
        sa.Column("reference_id", sa.String(length=32), nullable=False, unique=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="blocked"),
        sa.Column(
            "reason", sa.String(length=80), nullable=False, server_default="ACCOUNT_LIMIT_EXCEEDED"
        ),
        sa.Column("linked_account_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("raised_limit", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "resolved_by",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_ip_blocks_ip_hash", "ip_blocks", ["ip_hash"])
    op.create_index("ix_ip_blocks_reference_id", "ip_blocks", ["reference_id"], unique=True)
    op.create_index("ix_ip_blocks_status", "ip_blocks", ["status"])
    op.create_index("ix_ip_blocks_created_at", "ip_blocks", ["created_at"])

    op.create_table(
        "ip_whitelist",
        sa.Column("ip_hash", sa.String(length=64), primary_key=True),
        sa.Column(
            "added_by",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(length=240), nullable=False, server_default=""),
    )
    op.create_table(
        "unblock_requests",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("reference_id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column(
            "resolved_by",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("resolution_note", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_unblock_requests_reference_id", "unblock_requests", ["reference_id"])
    op.create_index("ix_unblock_requests_status", "unblock_requests", ["status"])
    op.create_index("ix_unblock_requests_created_at", "unblock_requests", ["created_at"])
    op.create_table(
        "access_audit_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("reason", sa.String(length=80), nullable=True),
        sa.Column("ip_hash", sa.String(length=64), nullable=True),
        sa.Column("reference_id", sa.String(length=32), nullable=True),
        sa.Column("actor_id", sa.String(length=36), nullable=True),
        sa.Column("details_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for name, column in (
        ("action", "action"),
        ("ip_hash", "ip_hash"),
        ("reference_id", "reference_id"),
        ("created_at", "created_at"),
    ):
        op.create_index(f"ix_access_audit_events_{name}", "access_audit_events", [column])

    with op.batch_alter_table("analyses") as batch:
        batch.alter_column("owner_id", existing_type=sa.String(length=36), nullable=True)
        batch.add_column(sa.Column("guest_id", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("idempotency_key", sa.String(length=128), nullable=True))
        batch.create_foreign_key(
            "fk_analyses_guest_id", "guest_sessions", ["guest_id"], ["guest_id"], ondelete="CASCADE"
        )
        batch.create_check_constraint(
            "ck_analysis_exactly_one_owner",
            (
                "(owner_id IS NOT NULL AND guest_id IS NULL) OR (owner_id IS NULL AND guest_id "
                "IS NOT NULL)"
            ),
        )
    op.create_index("ix_analyses_guest_id", "analyses", ["guest_id"])

    if bind.dialect.name == "postgresql":
        op.execute(
            "CREATE FUNCTION reject_credit_ledger_mutation() RETURNS trigger LANGUAGE "
            "plpgsql AS $$ BEGIN RAISE EXCEPTION 'credit ledger is append-only'; END $$"
        )
        op.execute(
            "CREATE TRIGGER credit_transactions_immutable BEFORE UPDATE OR DELETE ON "
            "credit_transactions FOR EACH ROW EXECUTE FUNCTION "
            "reject_credit_ledger_mutation()"
        )
        op.execute("DROP POLICY IF EXISTS analyses_owner_or_service ON analyses")
        op.execute(
            """CREATE POLICY analyses_owner_or_service ON analyses FOR ALL
            USING (current_setting('cgs.actor', true) IN ('admin','worker')
                OR owner_id = NULLIF(current_setting('cgs.user_id', true), '')
                OR guest_id = NULLIF(current_setting('cgs.guest_id', true), ''))
            WITH CHECK (current_setting('cgs.actor', true) IN ('admin','worker')
                OR owner_id = NULLIF(current_setting('cgs.user_id', true), '')
                OR guest_id = NULLIF(current_setting('cgs.guest_id', true), ''))"""
        )
        op.execute("DROP POLICY IF EXISTS inference_jobs_owner_or_service ON inference_jobs")
        op.execute(
            """CREATE POLICY inference_jobs_owner_or_service ON inference_jobs FOR ALL
            USING (current_setting('cgs.actor', true) IN ('admin','worker') OR EXISTS (
                SELECT 1 FROM analyses a WHERE a.id = inference_jobs.analysis_id AND (
                    a.owner_id = NULLIF(current_setting('cgs.user_id', true), '') OR
                    a.guest_id = NULLIF(current_setting('cgs.guest_id', true), ''))))
            WITH CHECK (current_setting('cgs.actor', true) IN ('admin','worker') OR EXISTS (
                SELECT 1 FROM analyses a WHERE a.id = inference_jobs.analysis_id AND (
                    a.owner_id = NULLIF(current_setting('cgs.user_id', true), '') OR
                    a.guest_id = NULLIF(current_setting('cgs.guest_id', true), ''))))"""
        )

        for table in (
            "guest_sessions",
            "credit_wallets",
            "credit_transactions",
            "ip_account_links",
            "ip_enforcement_guards",
            "ip_blocks",
            "ip_whitelist",
            "unblock_requests",
            "access_audit_events",
        ):
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
            op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
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
        for table in ("ip_account_links", "ip_blocks", "ip_whitelist", "unblock_requests"):
            op.execute(
                f"CREATE POLICY {table}_admin_auth ON {table} FOR ALL "
                "USING (current_setting('cgs.actor', true) IN ('admin','auth')) "
                "WITH CHECK (current_setting('cgs.actor', true) IN ('admin','auth'))"
            )
        op.execute(
            "CREATE POLICY ip_enforcement_guards_service ON ip_enforcement_guards FOR ALL "
            "USING (current_setting('cgs.actor', true) IN "
            "('admin','auth','credits','guest')) WITH CHECK (current_setting('cgs.actor', "
            "true) IN ('admin','auth','credits','guest'))"
        )
        op.execute(
            """CREATE POLICY access_audit_insert ON access_audit_events FOR INSERT
            WITH CHECK (
                current_setting('cgs.actor', true)
                IN ('admin','auth','guest','credits','worker')
            )"""
        )
        op.execute("""CREATE POLICY access_audit_select ON access_audit_events FOR SELECT
            USING (current_setting('cgs.actor', true)='admin')""")


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS credit_transactions_immutable ON credit_transactions")
        op.execute("DROP FUNCTION IF EXISTS reject_credit_ledger_mutation()")
        for policy, table in (
            ("access_audit_select", "access_audit_events"),
            ("access_audit_insert", "access_audit_events"),
            ("unblock_requests_admin_auth", "unblock_requests"),
            ("ip_whitelist_admin_auth", "ip_whitelist"),
            ("ip_blocks_admin_auth", "ip_blocks"),
            ("ip_account_links_admin_auth", "ip_account_links"),
            ("credit_transactions_access", "credit_transactions"),
            ("credit_wallets_access", "credit_wallets"),
            ("guest_sessions_access", "guest_sessions"),
        ):
            op.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")
        op.execute("DROP POLICY IF EXISTS ip_enforcement_guards_service ON ip_enforcement_guards")
        for table in (
            "guest_sessions",
            "credit_wallets",
            "credit_transactions",
            "ip_account_links",
            "ip_enforcement_guards",
            "ip_blocks",
            "ip_whitelist",
            "unblock_requests",
            "access_audit_events",
        ):
            op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
            op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        op.execute("DROP POLICY IF EXISTS analyses_owner_or_service ON analyses")
        op.execute("DROP POLICY IF EXISTS inference_jobs_owner_or_service ON inference_jobs")
        op.execute(
            """CREATE POLICY analyses_owner_or_service ON analyses FOR ALL
            USING (
                current_setting('cgs.actor', true) IN ('admin','worker')
                OR owner_id = NULLIF(current_setting('cgs.user_id', true), '')
            )
            WITH CHECK (
                current_setting('cgs.actor', true) IN ('admin','worker')
                OR owner_id = NULLIF(current_setting('cgs.user_id', true), '')
            )"""
        )
        op.execute(
            """CREATE POLICY inference_jobs_owner_or_service ON inference_jobs FOR ALL
            USING (
                current_setting('cgs.actor', true) IN ('admin','worker')
                OR EXISTS (
                    SELECT 1 FROM analyses a
                    WHERE a.id = inference_jobs.analysis_id
                        AND a.owner_id = NULLIF(current_setting('cgs.user_id', true), '')
                )
            )
            WITH CHECK (
                current_setting('cgs.actor', true) IN ('admin','worker')
                OR EXISTS (
                    SELECT 1 FROM analyses a
                    WHERE a.id = inference_jobs.analysis_id
                        AND a.owner_id = NULLIF(current_setting('cgs.user_id', true), '')
                )
            )"""
        )
    op.drop_index("ix_analyses_guest_id", table_name="analyses")
    with op.batch_alter_table("analyses") as batch:
        batch.drop_constraint("ck_analysis_exactly_one_owner", type_="check")
        batch.drop_constraint("fk_analyses_guest_id", type_="foreignkey")
        batch.drop_column("idempotency_key")
        batch.drop_column("guest_id")
        batch.alter_column("owner_id", existing_type=sa.String(length=36), nullable=False)
    for name in ("action", "ip_hash", "reference_id", "created_at"):
        op.drop_index(f"ix_access_audit_events_{name}", table_name="access_audit_events")
    op.drop_table("access_audit_events")
    for name in ("reference_id", "status", "created_at", "ip_hash"):
        op.drop_index(f"ix_ip_blocks_{name}", table_name="ip_blocks")
    op.drop_table("ip_blocks")
    for name in ("reference_id", "status", "created_at"):
        op.drop_index(f"ix_unblock_requests_{name}", table_name="unblock_requests")
    op.drop_table("unblock_requests")
    op.drop_table("ip_whitelist")
    for name in ("ip_hash", "user_id", "last_seen_at"):
        op.drop_index(f"ix_ip_account_links_{name}", table_name="ip_account_links")
    op.drop_table("ip_account_links")
    op.drop_table("ip_enforcement_guards")
    if op.get_bind().dialect.name == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS credit_transactions_no_update")
        op.execute("DROP TRIGGER IF EXISTS credit_transactions_no_delete")
    for name in ("wallet_id", "type", "reference_id", "idempotency_key", "created_at"):
        op.drop_index(f"ix_credit_transactions_{name}", table_name="credit_transactions")
    op.drop_table("credit_transactions")
    for name in ("owner_type", "owner_id"):
        op.drop_index(f"ix_credit_wallets_{name}", table_name="credit_wallets")
    op.drop_table("credit_wallets")
    for name in ("ip_hash", "ip_subnet_hash", "fingerprint_hash", "linked_user_id", "last_seen_at"):
        op.drop_index(f"ix_guest_sessions_{name}", table_name="guest_sessions")
    op.drop_table("guest_sessions")
    op.drop_index("ix_users_password_reset_token_hash", table_name="users")
    op.drop_index("ix_users_email_verification_token_hash", table_name="users")
    op.drop_index("ix_users_email_identity", table_name="users")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("password_reset_expires_at")
        batch.drop_column("password_reset_token_hash")
        batch.drop_column("email_verification_expires_at")
        batch.drop_column("email_verification_token_hash")
        batch.drop_column("email_verified_at")
        batch.drop_column("email_identity")
