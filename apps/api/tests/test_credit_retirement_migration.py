from datetime import datetime, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session


def test_credit_retirement_preserves_archive_and_removes_live_tables(tmp_path, monkeypatch):
    database_path = tmp_path / "credit-retirement.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("MIGRATION_DATABASE_URL", database_url)
    api_root = Path(__file__).resolve().parents[1]
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option("script_location", str(api_root / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)

    command.upgrade(config, "0005_guest_credits_auth")
    engine = create_engine(database_url)
    now = datetime.now(timezone.utc).isoformat()
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO guest_sessions "
            "(guest_id, ip_hash, ip_subnet_hash, fingerprint_hash, linked_user_id, verifications_used, created_at, last_seen_at) "
            "VALUES ('guest-1', 'ip-hash', 'subnet-hash', 'fingerprint', NULL, 1, :now, :now)"
        ), {"now": now})
        connection.execute(text(
            "INSERT INTO credit_wallets (id, owner_type, owner_id, balance, updated_at) "
            "VALUES ('wallet-1', 'guest', 'guest-1', 50, :now)"
        ), {"now": now})
        connection.execute(text(
            "INSERT INTO credit_transactions "
            "(id, wallet_id, type, amount, balance_after, reference_id, idempotency_key, created_at) "
            "VALUES ('transaction-1', 'wallet-1', 'guest_grant', 50, 50, NULL, 'grant-1', :now)"
        ), {"now": now})

    command.upgrade(config, "head")
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert "credit_wallets" not in tables
    assert "credit_transactions" not in tables
    assert "retired_usage_wallets" in tables
    assert "retired_usage_transactions" in tables
    assert {"ip_hash", "ip_subnet_hash", "fingerprint_hash", "verifications_used"}.isdisjoint(
        {column["name"] for column in inspector.get_columns("guest_sessions")}
    )
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT balance FROM retired_usage_wallets WHERE id='wallet-1'")) == 50
        assert connection.scalar(text("SELECT COUNT(*) FROM retired_usage_transactions")) == 1

    from app.main import GuestSession

    with Session(engine) as session:
        session.add(GuestSession(guest_id="guest-runtime"))
        session.commit()
        assert session.get(GuestSession, "guest-runtime").last_seen_at is not None

    command.downgrade(config, "0005_guest_credits_auth")
    restored = inspect(engine)
    assert "credit_wallets" in set(restored.get_table_names())
    assert "credit_transactions" in set(restored.get_table_names())
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT COUNT(*) FROM credit_transactions")) == 1
    engine.dispose()
