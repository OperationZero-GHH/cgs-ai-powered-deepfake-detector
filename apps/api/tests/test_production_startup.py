import os
import subprocess
import sys
from pathlib import Path


def test_production_import_succeeds_with_required_environment():
    api_root = Path(__file__).resolve().parents[1]
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHON_DOTENV_DISABLED": "true",
            "APP_ENV": "production",
            "APP_SECRET_KEY": "verification-only-secret-with-sufficient-length",
            "SESSION_COOKIE_SECURE": "true",
            "APP_ORIGINS": "https://shield.example.test",
            "SMTP_HOST": "smtp.example.test",
            "SMTP_FROM_EMAIL": "noreply@example.test",
            "SUPPORT_CONTACT_EMAIL": "support@example.test",
            "DATABASE_URL": "postgresql://localhost/test",
            "STORAGE_DIR": str(api_root / "storage"),
            "AI_DETECTOR_PROVIDER": "disabled",
        }
    )
    import_code = """
from types import SimpleNamespace
import sqlalchemy
import sqlalchemy.orm

class Result:
    def scalar_one(self):
        return False

class Connection:
    def __enter__(self):
        return self
    def __exit__(self, *_args):
        return False
    def execute(self, *_args):
        return Result()

class Engine:
    dialect = SimpleNamespace(name="postgresql")
    def connect(self):
        return Connection()

sqlalchemy.create_engine = lambda *_args, **_kwargs: Engine()
sqlalchemy.orm.sessionmaker = lambda **_kwargs: object()
import app.main
"""
    result = subprocess.run(
        [sys.executable, "-c", import_code],
        cwd=api_root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr
