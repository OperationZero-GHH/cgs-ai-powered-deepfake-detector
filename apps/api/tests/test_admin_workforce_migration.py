from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_admin_workforce_migration_adds_signup_attribution_and_logs(tmp_path, monkeypatch):
    database_url = f"sqlite:///{(tmp_path / 'admin-workforce.db').as_posix()}"
    monkeypatch.setenv("MIGRATION_DATABASE_URL", database_url)
    api_root = Path(__file__).resolve().parents[1]
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option("script_location", str(api_root / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)

    command.upgrade(config, "0008_admin_console_management")
    command.upgrade(config, "head")
    engine = create_engine(database_url)
    inspector = inspect(engine)
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    assert {"signup_method", "signup_ip"} <= user_columns
    tables = set(inspector.get_table_names())
    assert {"user_activity_events", "admin_invitations"} <= tables
    assert {"ix_user_activity_events_actor_id", "ix_user_activity_events_created_at"} <= {
        index["name"] for index in inspector.get_indexes("user_activity_events")
    }
    engine.dispose()
