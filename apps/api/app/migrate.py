"""Apply Alembic migrations, adopting a complete pre-Alembic local schema safely."""

from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect

API_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = API_DIR.parents[1]
load_dotenv(REPO_ROOT / ".env")

BASELINE_COLUMNS = {
    "users": {"id", "email", "display_name", "password_hash", "role", "active", "created_at"},
    "sessions": {"token_hash", "user_id", "expires_at", "revoked_at"},
    "analyses": {
        "id",
        "owner_id",
        "status",
        "original_filename",
        "object_key",
        "preview_key",
        "detected_mime_type",
        "size_bytes",
        "width",
        "height",
        "sha256",
        "metadata_json",
        "detector_result_json",
        "created_at",
        "completed_at",
    },
}
LATEST_TABLES = {"inference_jobs", "rate_limit_buckets", "audit_events", "worker_heartbeats"}
AUTH_TABLES = {
    "guest_sessions",
    "ip_account_links",
    "ip_enforcement_guards",
    "ip_blocks",
    "ip_whitelist",
    "unblock_requests",
    "access_audit_events",
}


def _alembic_config(database_url: str) -> Config:
    config = Config(str(API_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(API_DIR / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


def _adopt_existing_schema(config: Config, database_url: str) -> None:
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False} if database_url.startswith("sqlite:") else {},
    )
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        if "alembic_version" in tables:
            # Respect the recorded revision and let `upgrade()` apply every
            # pending migration. Stamping a partially upgraded schema as head
            # hides missing columns and constraints until a request returns 500.
            return
        existing_core = set(BASELINE_COLUMNS).intersection(tables)
        if not existing_core:
            return
        if existing_core != set(BASELINE_COLUMNS):
            raise RuntimeError(
                "Found a partial application schema without migration history; refusing to "
                "guess a migration state."
            )
        for table, required in BASELINE_COLUMNS.items():
            actual = {column["name"] for column in inspector.get_columns(table)}
            if not required.issubset(actual):
                raise RuntimeError(
                    f"The existing {table} table does not match a supported schema; refusing to "
                    "modify it automatically."
                )
        if LATEST_TABLES.issubset(tables) and "provenance_json" in {
            c["name"] for c in inspector.get_columns("analyses")
        }:
            user_cols = {c["name"] for c in inspector.get_columns("users")}
            existing_auth_tables = AUTH_TABLES.intersection(tables)
            if existing_auth_tables and existing_auth_tables != AUTH_TABLES:
                raise RuntimeError(
                    "Found a partial authentication/security schema without migration history; "
                    "refusing to guess a migration state."
                )
            if existing_auth_tables == AUTH_TABLES:
                # This is the latest pre-Alembic local schema. Stamp only the
                # last known historical revision so the compatibility repair
                # migration can reconcile fields added after that schema.
                command.stamp(config, "0006_retire_credits")
            elif {"username", "phone_number"}.issubset(user_cols):
                command.stamp(config, "0004_user_contact_details")
            else:
                # Adopt the last schema version that predates PostgreSQL RLS so
                # the new policy migration is still applied to an existing DB.
                command.stamp(config, "0002_queue_security_admin")
        else:
            command.stamp(config, "0001_initial")
    finally:
        engine.dispose()


def main() -> None:
    database_url = os.getenv(
        "MIGRATION_DATABASE_URL",
        os.getenv("DATABASE_URL", "sqlite:///./data/cgs_deepfake_shield.db"),
    )
    if database_url.startswith("sqlite:///"):
        db_file = database_url.removeprefix("sqlite:///")
        if db_file != ":memory:":
            Path(db_file).parent.mkdir(parents=True, exist_ok=True)
    config = _alembic_config(database_url)
    _adopt_existing_schema(config, database_url)
    command.upgrade(config, "head")


if __name__ == "__main__":
    main()
