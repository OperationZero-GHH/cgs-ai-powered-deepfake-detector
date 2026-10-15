import os
import uuid
from pathlib import Path
import tempfile
_pytest_run_id = uuid.uuid4().hex
os.environ["APP_ENV"] = "test"
os.environ["AI_DETECTOR_PROVIDER"] = "disabled"
_pytest_tmp = Path(tempfile.gettempdir()) / f"cgs-deepfake-shield-pytest-{_pytest_run_id}"
_pytest_tmp.mkdir(parents=True, exist_ok=True)
os.environ["DATABASE_URL"] = f"sqlite:///{(_pytest_tmp / 'test.db').as_posix()}"
os.environ["STORAGE_DIR"] = str(_pytest_tmp / "storage")
os.environ["SESSION_COOKIE_SECURE"] = "false"

import pytest
from fastapi.testclient import TestClient

from app import main


@pytest.fixture
def client(monkeypatch):
    with main.engine.begin() as conn:
        conn.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
    main.Base.metadata.drop_all(main.engine)
    main.Base.metadata.create_all(main.engine)
    main.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    for item in main.STORAGE_DIR.iterdir():
        if item.is_file():
            item.unlink()
    outbox = []
    monkeypatch.setattr(main, "_send_account_email", lambda address, subject, body: outbox.append((address, subject, body)))
    with TestClient(main.app) as test_client:
        test_client.account_email_outbox = outbox
        yield test_client


@pytest.fixture
def image_bytes():
    from io import BytesIO
    from PIL import Image

    output = BytesIO()
    Image.new("RGB", (24, 16), color=(80, 140, 190)).save(output, "PNG")
    return output.getvalue()
