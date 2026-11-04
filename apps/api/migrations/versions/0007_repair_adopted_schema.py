"""Repair legacy schemas that were incorrectly stamped as fully migrated."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007_repair_adopted_schema"
down_revision = "0006_retire_credits"
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


def _columns(table: str) -> dict[str, dict[str, object]]:
    return {column["name"]: column for column in sa.inspect(op.get_bind()).get_columns(table)}


def _ensure_index(table: str, name: str, columns: list[str], *, unique: bool = False) -> None:
    inspector = sa.inspect(op.get_bind())
    for index in inspector.get_indexes(table):
        if index["column_names"] == columns and bool(index["unique"]) == unique:
            return
    if unique:
        for constraint in inspector.get_unique_constraints(table):
            if constraint["column_names"] == columns:
                return
    if name in {index["name"] for index in inspector.get_indexes(table)}:
        raise RuntimeError(
            f"Cannot repair {table}: index {name} exists with a different definition."
        )
    op.create_index(name, table, columns, unique=unique)


def _ensure_user_auth_columns() -> None:
    existing = _columns("users")
    email_verified_was_added = "email_verified_at" not in existing
    additions = {
        "email_identity": sa.Column("email_identity", sa.String(length=320), nullable=True),
        "email_verified_at": sa.Column(
            "email_verified_at", sa.DateTime(timezone=True), nullable=True
        ),
        "email_verification_token_hash": sa.Column(
            "email_verification_token_hash", sa.String(length=64), nullable=True
        ),
        "email_verification_expires_at": sa.Column(
            "email_verification_expires_at", sa.DateTime(timezone=True), nullable=True
        ),
        "password_reset_token_hash": sa.Column(
            "password_reset_token_hash", sa.String(length=64), nullable=True
        ),
        "password_reset_expires_at": sa.Column(
            "password_reset_expires_at", sa.DateTime(timezone=True), nullable=True
        ),
    }
    missing = [column for name, column in additions.items() if name not in existing]
    if missing:
        with op.batch_alter_table("users") as batch:
            for column in missing:
                batch.add_column(column)

    bind = op.get_bind()
    seen: set[str] = set()
    rows = bind.execute(
        sa.text(
            "SELECT id, email, created_at, email_identity, email_verified_at "
            "FROM users ORDER BY created_at, id"
        )
    ).mappings()
    for row in rows:
        identity = (row["email_identity"] or "").strip()
        if not identity:
            identity = _email_identity(row["email"])
        if identity in seen:
            identity = f"{identity}#legacy-{row['id']}"
        seen.add(identity)

        updates: dict[str, object] = {}
        if row["email_identity"] != identity:
            updates["email_identity"] = identity
        if email_verified_was_added:
            updates["email_verified_at"] = row["created_at"]
        if updates:
            assignments = ", ".join(f"{name}=:{name}" for name in updates)
            bind.execute(
                sa.text(f"UPDATE users SET {assignments} WHERE id=:id"),
                {**updates, "id": row["id"]},
            )

    user_columns = _columns("users")
    if user_columns["email_identity"]["nullable"]:
        with op.batch_alter_table("users") as batch:
            batch.alter_column(
                "email_identity", existing_type=sa.String(length=320), nullable=False
            )

    _ensure_index("users", "ix_users_email_identity", ["email_identity"], unique=True)
    _ensure_index(
        "users", "ix_users_email_verification_token_hash", ["email_verification_token_hash"]
    )
    _ensure_index("users", "ix_users_password_reset_token_hash", ["password_reset_token_hash"])


def _ensure_analysis_guest_columns() -> None:
    existing = _columns("analyses")
    additions = {
        "guest_id": sa.Column("guest_id", sa.String(length=64), nullable=True),
        "idempotency_key": sa.Column("idempotency_key", sa.String(length=128), nullable=True),
    }
    missing = [column for name, column in additions.items() if name not in existing]
    inspector = sa.inspect(op.get_bind())
    foreign_keys = inspector.get_foreign_keys("analyses")
    guest_foreign_key_exists = any(
        key["constrained_columns"] == ["guest_id"] and key["referred_table"] == "guest_sessions"
        for key in foreign_keys
    )
    checks = inspector.get_check_constraints("analyses")
    owner_check_exists = any(
        check.get("name") == "ck_analysis_exactly_one_owner"
        or "owner_id IS NOT NULL" in (check.get("sqltext") or "")
        for check in checks
    )
    owner_nullable = bool(existing["owner_id"]["nullable"])
    if missing or not owner_nullable or not guest_foreign_key_exists or not owner_check_exists:
        with op.batch_alter_table("analyses") as batch:
            for column in missing:
                batch.add_column(column)
            if not owner_nullable:
                batch.alter_column("owner_id", existing_type=sa.String(length=36), nullable=True)
            if not guest_foreign_key_exists:
                batch.create_foreign_key(
                    "fk_analyses_guest_id",
                    "guest_sessions",
                    ["guest_id"],
                    ["guest_id"],
                    ondelete="CASCADE",
                )
            if not owner_check_exists:
                batch.create_check_constraint(
                    "ck_analysis_exactly_one_owner",
                    "(owner_id IS NOT NULL AND guest_id IS NULL) OR "
                    "(owner_id IS NULL AND guest_id IS NOT NULL)",
                )

    _ensure_index("analyses", "ix_analyses_guest_id", ["guest_id"])
    _ensure_index(
        "analyses", "uq_analyses_user_idempotency_key", ["owner_id", "idempotency_key"], unique=True
    )
    _ensure_index(
        "analyses",
        "uq_analyses_guest_idempotency_key",
        ["guest_id", "idempotency_key"],
        unique=True,
    )


def _retire_legacy_credit_tables() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    live_tables = {"credit_wallets", "credit_transactions"}.intersection(tables)
    retired_tables = {"retired_usage_wallets", "retired_usage_transactions"}.intersection(tables)
    if live_tables and retired_tables:
        raise RuntimeError(
            "Both live and retired credit ledger tables exist; refusing to overwrite "
            "historical data."
        )
    if live_tables and live_tables != {"credit_wallets", "credit_transactions"}:
        raise RuntimeError(
            "The live credit ledger is incomplete; refusing to rename only part of its history."
        )
    if retired_tables and retired_tables != {"retired_usage_wallets", "retired_usage_transactions"}:
        raise RuntimeError(
            "The retired credit ledger is incomplete; refusing to change its history."
        )

    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS credit_transactions_no_update")
        op.execute("DROP TRIGGER IF EXISTS credit_transactions_no_delete")
    elif bind.dialect.name == "postgresql":
        if "credit_transactions" in tables:
            op.execute("DROP POLICY IF EXISTS credit_transactions_access ON credit_transactions")
            op.execute(
                "DROP TRIGGER IF EXISTS credit_transactions_immutable ON credit_transactions"
            )
        if "credit_wallets" in tables:
            op.execute("DROP POLICY IF EXISTS credit_wallets_access ON credit_wallets")
        op.execute("DROP FUNCTION IF EXISTS reject_credit_ledger_mutation()")

    for live, retired in (
        ("credit_transactions", "retired_usage_transactions"),
        ("credit_wallets", "retired_usage_wallets"),
    ):
        if live in tables:
            op.rename_table(live, retired)

    if bind.dialect.name == "postgresql":
        current_tables = set(sa.inspect(bind).get_table_names())
        for retired in ("retired_usage_wallets", "retired_usage_transactions"):
            if retired in current_tables:
                op.execute(f"ALTER TABLE {retired} ENABLE ROW LEVEL SECURITY")
                op.execute(f"ALTER TABLE {retired} FORCE ROW LEVEL SECURITY")


def _remove_guest_quota_fields() -> None:
    if "guest_sessions" not in set(sa.inspect(op.get_bind()).get_table_names()):
        return
    existing = _columns("guest_sessions")
    retired = {"ip_hash", "ip_subnet_hash", "fingerprint_hash", "verifications_used"}.intersection(
        existing
    )
    if not retired:
        return
    for index in sa.inspect(op.get_bind()).get_indexes("guest_sessions"):
        if set(index["column_names"] or []).intersection(retired):
            op.drop_index(index["name"], table_name="guest_sessions")
    with op.batch_alter_table("guest_sessions") as batch:
        for column in sorted(retired):
            batch.drop_column(column)


def _repair_postgres_policies() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    policies = {
        "users": {
            "users_select_self_or_auth": (
                "FOR SELECT USING (current_setting('cgs.actor', "
                "true) IN ('admin','auth') OR id = NULLIF(current_setting('cgs.user_id', "
                "true), ''))"
            ),
            "users_insert_auth_or_admin": (
                "FOR INSERT WITH CHECK (current_setting('cgs.actor', true) IN ('admin','auth'))"
            ),
            "users_update_auth_or_admin": (
                "FOR UPDATE USING (current_setting('cgs.actor', "
                "true) IN ('admin','auth')) WITH CHECK (current_setting('cgs.actor', true) IN "
                "('admin','auth'))"
            ),
            "users_delete_self_or_admin": (
                "FOR DELETE USING (current_setting('cgs.actor', "
                "true) = 'admin' OR id = NULLIF(current_setting('cgs.user_id', true), ''))"
            ),
        },
        "sessions": {
            "sessions_select_self_or_admin": (
                "FOR SELECT USING "
                "(current_setting('cgs.actor', true) = 'admin' OR user_id = "
                "NULLIF(current_setting('cgs.user_id', true), '') OR token_hash = "
                "NULLIF(current_setting('cgs.session_hash', true), ''))"
            ),
            "sessions_insert_self_or_admin": (
                "FOR INSERT WITH CHECK "
                "(current_setting('cgs.actor', true) = 'admin' OR user_id = "
                "NULLIF(current_setting('cgs.user_id', true), ''))"
            ),
            "sessions_update_self_or_admin": (
                "FOR UPDATE USING "
                "(current_setting('cgs.actor', true) = 'admin' OR user_id = "
                "NULLIF(current_setting('cgs.user_id', true), '')) WITH CHECK "
                "(current_setting('cgs.actor', true) = 'admin' OR user_id = "
                "NULLIF(current_setting('cgs.user_id', true), ''))"
            ),
            "sessions_delete_self_or_admin": (
                "FOR DELETE USING "
                "(current_setting('cgs.actor', true) = 'admin' OR user_id = "
                "NULLIF(current_setting('cgs.user_id', true), ''))"
            ),
        },
        "analyses": {
            "analyses_owner_or_service": (
                "FOR ALL USING (current_setting('cgs.actor', true) "
                "IN ('admin','worker') OR owner_id = NULLIF(current_setting('cgs.user_id', "
                "true), '') OR guest_id = NULLIF(current_setting('cgs.guest_id', true), '')) "
                "WITH CHECK (current_setting('cgs.actor', true) IN ('admin','worker') OR "
                "owner_id = NULLIF(current_setting('cgs.user_id', true), '') OR guest_id = "
                "NULLIF(current_setting('cgs.guest_id', true), ''))"
            ),
        },
        "inference_jobs": {
            "inference_jobs_owner_or_service": (
                "FOR ALL USING (current_setting('cgs.actor', "
                "true) IN ('admin','worker') OR EXISTS (SELECT 1 FROM analyses a WHERE "
                "a.id=inference_jobs.analysis_id AND "
                "(a.owner_id=NULLIF(current_setting('cgs.user_id', true), '') OR "
                "a.guest_id=NULLIF(current_setting('cgs.guest_id', true), '')))) WITH CHECK "
                "(current_setting('cgs.actor', true) IN ('admin','worker') OR EXISTS (SELECT "
                "1 FROM analyses a WHERE a.id=inference_jobs.analysis_id AND "
                "(a.owner_id=NULLIF(current_setting('cgs.user_id', true), '') OR "
                "a.guest_id=NULLIF(current_setting('cgs.guest_id', true), ''))))"
            ),
        },
        "audit_events": {
            "audit_events_admin_only": (
                "FOR ALL USING (current_setting('cgs.actor', true) = "
                "'admin') WITH CHECK (current_setting('cgs.actor', true) = 'admin')"
            ),
        },
        "guest_sessions": {
            "guest_sessions_access": (
                "FOR ALL USING (current_setting('cgs.actor', true) IN "
                "('admin','auth','worker') OR guest_id = "
                "NULLIF(current_setting('cgs.guest_id', true), '')) WITH CHECK "
                "(current_setting('cgs.actor', true) IN ('admin','auth','worker') OR guest_id "
                "= NULLIF(current_setting('cgs.guest_id', true), ''))"
            ),
        },
        "ip_account_links": {
            "ip_account_links_admin_auth": (
                "FOR ALL USING (current_setting('cgs.actor', "
                "true) IN ('admin','auth')) WITH CHECK (current_setting('cgs.actor', true) IN "
                "('admin','auth'))"
            ),
        },
        "ip_blocks": {
            "ip_blocks_admin_auth": (
                "FOR ALL USING (current_setting('cgs.actor', true) IN "
                "('admin','auth')) WITH CHECK (current_setting('cgs.actor', true) IN "
                "('admin','auth'))"
            ),
        },
        "ip_whitelist": {
            "ip_whitelist_admin_auth": (
                "FOR ALL USING (current_setting('cgs.actor', true) "
                "IN ('admin','auth')) WITH CHECK (current_setting('cgs.actor', true) IN "
                "('admin','auth'))"
            ),
        },
        "unblock_requests": {
            "unblock_requests_admin_auth": (
                "FOR ALL USING (current_setting('cgs.actor', "
                "true) IN ('admin','auth')) WITH CHECK (current_setting('cgs.actor', true) IN "
                "('admin','auth'))"
            ),
        },
        "ip_enforcement_guards": {
            "ip_enforcement_guards_service": (
                "FOR ALL USING (current_setting('cgs.actor', "
                "true) IN ('admin','auth','guest')) WITH CHECK (current_setting('cgs.actor', "
                "true) IN ('admin','auth','guest'))"
            ),
        },
        "access_audit_events": {
            "access_audit_insert": (
                "FOR INSERT WITH CHECK (current_setting('cgs.actor', "
                "true) IN ('admin','auth','guest','worker'))"
            ),
            "access_audit_select": (
                "FOR SELECT USING (current_setting('cgs.actor', true) = 'admin')"
            ),
        },
    }

    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    for table, table_policies in policies.items():
        if table not in tables:
            continue
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        for policy_name, definition in table_policies.items():
            op.execute(f"DROP POLICY IF EXISTS {policy_name} ON {table}")
            op.execute(f"CREATE POLICY {policy_name} ON {table} {definition}")


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if not {"users", "analyses", "guest_sessions"}.issubset(tables):
        raise RuntimeError(
            "Cannot repair the adopted schema because a required authentication table is missing."
        )

    _ensure_user_auth_columns()
    _ensure_analysis_guest_columns()
    _retire_legacy_credit_tables()
    _remove_guest_quota_fields()
    _repair_postgres_policies()


def downgrade() -> None:
    # Keep repaired columns, backfilled identities, and preserved ledger tables
    # when rolling back later revisions; removing them could lock users out or
    # discard historical data.
    pass
