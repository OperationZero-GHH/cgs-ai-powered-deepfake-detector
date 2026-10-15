import hashlib
import re
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from fastapi.testclient import TestClient

from app import main
from app import worker


def finish_analysis(client, analysis_id):
    assert worker.process_one("test-worker") is True
    return client.get(f"/api/v1/analyses/{analysis_id}").json()


def registration_payload(email, display_name="Reviewer"):
    username = email.split("@", 1)[0].casefold().replace("-", "_").replace(".", "_")[:32]
    return {
        "email": email,
        "password": "correct horse battery staple",
        "display_name": display_name,
        "username": username,
        "phone_number": "+12025550123",
    }


def sign_in(client, email):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": "correct horse battery staple"})
    assert response.status_code == 200
    return response.json()


def create_user(client, email="reviewer@example.com"):
    response = client.post(
        "/api/v1/auth/signup",
        json=registration_payload(email),
    )
    assert response.status_code == 201
    assert client.get("/api/v1/auth/me").status_code == 200
    token_body = client.account_email_outbox[-1][2]
    token = re.search(r"token=([A-Za-z0-9_-]+)", token_body).group(1)
    verified = client.post("/api/v1/auth/verify-email", json={"token": token})
    assert verified.status_code == 200
    return response.json()


def upload(client, image_bytes, filename="photo.png", media_type="image/png"):
    return client.post("/api/v1/analyses", files={"file": (filename, image_bytes, media_type)})


def test_upload_report_history_and_delete(client, image_bytes):
    create_user(client)
    response = upload(client, image_bytes)
    assert response.status_code == 201
    assert response.json()["status"] == "queued"
    report = finish_analysis(client, response.json()["analysis_id"])
    assert report["status"] == "completed"
    assert report["summary"]["classification"] == "inconclusive"
    assert report["summary"]["confidence_value"] is None
    assert report["detectors"][0]["status"] == "not_configured"
    assert report["file"]["sha256"] == hashlib.sha256(image_bytes).hexdigest()
    assert report["file"]["width"] == 24
    assert report["technical_integrity"]["format"] == "PNG"

    history = client.get("/api/v1/analyses")
    assert history.status_code == 200
    assert history.json()["total"] == 1
    detail = client.get(f"/api/v1/analyses/{report['analysis_id']}")
    assert detail.status_code == 200
    preview = client.get(f"/api/v1/analyses/{report['analysis_id']}/image")
    assert preview.status_code == 200
    assert preview.headers["content-type"] == "image/jpeg"

    keys = [main.STORAGE_DIR / f"{report['analysis_id']}.original", main.STORAGE_DIR / f"{report['analysis_id']}.jpg"]
    assert all(path.exists() for path in keys)
    deleted = client.delete(f"/api/v1/analyses/{report['analysis_id']}")
    assert deleted.status_code == 204
    assert all(not path.exists() for path in keys)
    assert client.get(f"/api/v1/analyses/{report['analysis_id']}").status_code == 404


def test_history_pagination_search_status_and_date_filters(client, image_bytes):
    create_user(client)
    first = upload(client, image_bytes).json()
    second = upload(client, image_bytes, filename="another.png").json()
    worker.process_one("test-worker")
    worker.process_one("test-worker")
    page_one = client.get("/api/v1/analyses?page=1&page_size=1&created_from=2000-01-01&created_to=2099-01-01")
    page_two = client.get("/api/v1/analyses?page=2&page_size=1&status_filter=completed")
    assert page_one.status_code == 200 and page_one.json()["total"] == 2
    assert len(page_one.json()["items"]) == 1
    assert page_two.status_code == 200 and page_two.json()["total"] == 2
    assert page_one.json()["items"][0]["analysis_id"] != page_two.json()["items"][0]["analysis_id"]
    by_id = client.get(f"/api/v1/analyses?q={first['analysis_id'][:10]}")
    assert by_id.json()["total"] == 1
    assert by_id.json()["items"][0]["analysis_id"] == first["analysis_id"]


def test_guest_uploads_are_owned_and_spoofed_uploads_are_rejected(client, image_bytes):
    guest_report = upload(client, image_bytes)
    assert guest_report.status_code == 201
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/analyses").json()["total"] == 1

    # Signup transfers the current signed guest's report into the new account.
    create_user(client)
    assert client.get("/api/v1/analyses").json()["total"] == 1
    mismatch = upload(client, image_bytes, filename="photo.jpg", media_type="image/jpeg")
    assert mismatch.status_code == 400
    assert mismatch.json()["code"] == "INVALID_FILE"
    corrupt = upload(client, b"not an image", filename="bad.png")
    assert corrupt.status_code == 400
    assert corrupt.json()["code"] == "INVALID_FILE"
    assert upload(client, image_bytes).status_code == 201
    second = upload(client, image_bytes, filename="second.png")
    assert second.status_code == 201
    assert client.get("/api/v1/analyses").json()["total"] == 3


def test_signup_rejects_backslash_return_path(client):
    payload = registration_payload("return-path@example.com")
    payload["return_to"] = "/" + chr(92) + "attacker.example/landing"
    response = client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == 422


def test_chunked_upload_body_limit_applies_without_content_length(client, monkeypatch):
    monkeypatch.setattr(main, "MAX_UPLOAD_BYTES", 128)
    monkeypatch.setattr(main, "MAX_VIDEO_BYTES", 128)
    boundary = "cgs-upload-boundary"
    payload = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="large.png"\r\n'
        "Content-Type: image/png\r\n\r\n"
    ).encode() + b"x" * (1024 * 1024 + 128) + f"\r\n--{boundary}--\r\n".encode()

    def chunks():
        for offset in range(0, len(payload), 64 * 1024):
            yield payload[offset:offset + 64 * 1024]

    response = client.post(
        "/api/v1/analyses",
        content=chunks(),
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Transfer-Encoding": "chunked",
            "Origin": "http://localhost:3000",
        },
    )

    assert response.status_code == 413, response.text


def test_upload_rejects_video_declared_mime_for_image(client, image_bytes):
    response = upload(client, image_bytes, media_type="video/mp4")

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_FILE"


def test_mkv_upload_keeps_its_video_mime(client, image_bytes, monkeypatch):
    from app import video

    monkeypatch.setattr(
        video,
        "validate_video",
        lambda *_args: ("MKV", 64, 64, {"is_video": True, "format": "MKV"}, image_bytes),
    )

    response = upload(client, image_bytes, filename="clip.mkv", media_type="video/x-matroska")

    assert response.status_code == 201
    assert response.json()["file"]["detected_mime_type"] == "video/x-matroska"
    assert "video/x-matroska" in client.get("/api/v1/config").json()["supported_mime_types"]


def test_login_and_logout(client):
    create_user(client)
    client.post("/api/v1/auth/logout")
    assert client.get("/api/v1/auth/me").status_code == 401
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "REVIEWER@example.com", "password": "correct horse battery staple"},
    )
    assert response.status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 200


def test_login_password_length_is_not_registration_validation(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "unknown@example.com", "password": "short"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Email or password is incorrect."


def test_expired_session_is_rejected(client):
    create_user(client)
    token = client.cookies.get(main.COOKIE_NAME)
    with main.SessionLocal() as db:
        session_row = db.get(main.UserSession, main.token_digest(token))
        session_row.expires_at = main.utcnow() - timedelta(minutes=1)
        db.commit()
    assert client.get("/api/v1/auth/me").status_code == 401


def test_upload_limit_and_traversal_like_filename(client, image_bytes, monkeypatch):
    create_user(client)
    monkeypatch.setattr(main, "MAX_UPLOAD_BYTES", 64)
    too_large = upload(client, image_bytes)
    assert too_large.status_code == 400
    assert too_large.json()["code"] == "INVALID_FILE"
    monkeypatch.setattr(main, "MAX_UPLOAD_BYTES", 10 * 1024 * 1024)
    result = upload(client, image_bytes, filename="../../travel\nreport.png")
    assert result.status_code == 201
    safe_name = result.json()["file"]["original_filename"]
    assert safe_name == "travelreport.png"
    assert "/" not in safe_name and "\\" not in safe_name and "\n" not in safe_name


def test_dimension_cap_returns_clear_error(client, image_bytes, monkeypatch):
    create_user(client)
    monkeypatch.setattr(main, "MAX_IMAGE_PIXELS", 100)
    response = upload(client, image_bytes)
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_FILE"
    assert "dimensions" in response.json()["message"]


def test_analysis_is_owner_scoped_and_admin_requires_role(client, image_bytes):
    create_user(client, "owner@example.com")
    report = upload(client, image_bytes).json()
    finish_analysis(client, report["analysis_id"])
    owner_client = client
    other = TestClient(main.app)
    try:
        response = other.post(
            "/api/v1/auth/signup",
            json=registration_payload("other@example.com", "Other"),
        )
        assert response.status_code == 201
        sign_in(other, "other@example.com")
        assert other.get(f"/api/v1/analyses/{report['analysis_id']}").status_code == 404
        assert other.get(f"/api/v1/analyses/{report['analysis_id']}/image").status_code == 404
        assert other.delete(f"/api/v1/analyses/{report['analysis_id']}").status_code == 404
        assert other.get("/api/v1/admin/overview").status_code == 403
        assert owner_client.get(f"/api/v1/analyses/{report['analysis_id']}").status_code == 200
    finally:
        other.close()


def test_logout_and_account_deletion_revoke_access(client, image_bytes):
    create_user(client)
    report = upload(client, image_bytes).json()
    assert client.delete("/api/v1/auth/account").status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401
    assert not (main.STORAGE_DIR / f"{report['analysis_id']}.original").exists()


def test_health_checks(client):
    assert client.get("/health/live").json() == {"status": "ok", "database": None, "storage": None}
    assert client.get("/health/ready").json() == {"status": "ready", "database": "ready", "storage": "ready"}
    config = client.get("/api/v1/config")
    assert config.status_code == 200
    assert config.json()["max_upload_bytes"] == main.MAX_UPLOAD_BYTES


def test_allowlisted_address_cannot_claim_admin_through_public_signup(client, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "operator@example.com")
    response = client.post(
        "/api/v1/auth/signup",
        json=registration_payload("operator@example.com", "Operator"),
    )
    assert response.status_code == 201
    assert response.json()["role"] == "user"
    sign_in(client, "operator@example.com")
    assert client.get("/api/v1/admin/overview").status_code == 403
    from app.bootstrap_admin import bootstrap

    bootstrap("operator@example.com", "correct horse battery staple", "Operator")
    assert client.get("/api/v1/admin/overview").status_code == 200
    blocked = client.post("/api/v1/auth/logout", headers={"Origin": "https://attacker.example"})
    assert blocked.status_code == 403


def test_persistent_rate_limit_blocks_excess_signups(client, monkeypatch):
    monkeypatch.setattr(main, "RATE_LIMIT_AUTH_LIMIT", 1)
    first = client.post(
        "/api/v1/auth/signup",
        json=registration_payload("first@example.com", "First"),
    )
    second = client.post(
        "/api/v1/auth/signup",
        json=registration_payload("second@example.com", "Second"),
    )
    assert first.status_code == 201
    assert second.status_code == 429
    assert int(second.headers["retry-after"]) > 0


def test_durable_worker_recovers_expired_lease_and_persists_detector_result(client, image_bytes, monkeypatch):
    from app.detectors import TestOnlyDetector

    create_user(client)
    created = upload(client, image_bytes).json()
    with main.SessionLocal() as db:
        job = db.scalar(main.select(main.InferenceJob).where(main.InferenceJob.analysis_id == created["analysis_id"]))
        job.status = "processing"
        job.attempts = 1
        job.locked_until = main.utcnow() - timedelta(seconds=1)
        job.worker_id = "crashed-worker"
        db.commit()
    monkeypatch.setattr(main, "synthetic_detector", TestOnlyDetector())

    report = finish_analysis(client, created["analysis_id"])
    assert report["status"] == "completed"
    assert report["detectors"][0]["provider"] == "test_only"
    assert report["detectors"][0]["score"] == 0.31
    assert "never a production" in report["detectors"][0]["score_semantics"]
    with main.SessionLocal() as db:
        job = db.scalar(main.select(main.InferenceJob).where(main.InferenceJob.analysis_id == created["analysis_id"]))
        assert job.status == "completed"
        assert job.attempts == 2


def test_trusted_non_hardware_provenance_does_not_skip_ai_detector(client, image_bytes, monkeypatch):
    from app.detectors import TestOnlyDetector

    create_user(client)
    created = upload(client, image_bytes).json()
    monkeypatch.setattr(main, "synthetic_detector", TestOnlyDetector())
    monkeypatch.setattr(
        worker,
        "scan_content_credentials",
        lambda _path: {
            "status": "trusted",
            "is_hardware_authenticated": False,
            "details": ["Trusted software signer."],
        },
    )

    report = finish_analysis(client, created["analysis_id"])

    assert report["detectors"][0]["provider"] == "test_only"
    assert report["provenance"]["status"] == "trusted"
    assert report["summary"]["classification"] != "authentic_hardware_provenance"


def test_legacy_hardware_provenance_cache_is_recomputed(client, image_bytes, monkeypatch):
    from app.detectors import TestOnlyDetector

    create_user(client)
    first = upload(client, image_bytes).json()
    finish_analysis(client, first["analysis_id"])

    with main.SessionLocal() as db:
        previous = db.get(main.Analysis, first["analysis_id"])
        previous.detector_result_json = json.dumps({
            "status": "completed",
            "provider": "c2pa_hardware_cryptographic_trust",
            "label": "authentic_hardware_provenance",
            "score": 0.01,
        })
        previous.provenance_json = json.dumps({
            "status": "trusted",
            "is_hardware_authenticated": True,
            "hardware_signer": "Sony Hardware Root (user assertion)",
        })
        db.commit()

    legacy_report = client.get(f"/api/v1/analyses/{first['analysis_id']}").json()
    assert legacy_report["summary"]["classification"] == "inconclusive"
    assert legacy_report["provenance"]["is_hardware_authenticated"] is False
    assert "Reanalyze" in legacy_report["detectors"][0]["limitations"][0]

    monkeypatch.setattr(main, "synthetic_detector", TestOnlyDetector())
    second = upload(client, image_bytes).json()
    report = finish_analysis(client, second["analysis_id"])

    assert report["detectors"][0]["provider"] == "test_only"
    assert report["summary"]["classification"] != "authentic_hardware_provenance"


def test_admin_can_suspend_accounts_and_actions_are_audited(client, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "operator@example.com")
    operator = create_user(client, "operator@example.com")
    from app.bootstrap_admin import bootstrap

    bootstrap("operator@example.com", "correct horse battery staple", "Operator")
    other = TestClient(main.app)
    try:
        created = other.post(
            "/api/v1/auth/signup",
            json=registration_payload("target@example.com", "Target"),
        ).json()
        sign_in(other, "target@example.com")
        assert created["role"] == "user"
        updated = client.patch(f"/api/v1/admin/users/{created['id']}", json={"active": False})
        assert updated.status_code == 200
        assert updated.json()["active"] is False
        assert other.get("/api/v1/auth/me").status_code == 401
        events = client.get("/api/v1/admin/audit")
        assert events.status_code == 200
        assert events.json()["items"][0]["action"] == "admin.user.updated"
        self_change = client.patch(f"/api/v1/admin/users/{operator['id']}", json={"active": False})
        assert self_change.status_code == 409
    finally:
        other.close()


def test_admin_workforce_user_logs_and_admin_logs(client, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "operator@example.com")
    create_user(client, "operator@example.com")
    from app.bootstrap_admin import bootstrap

    bootstrap("operator@example.com", "correct horse battery staple", "Operator")
    target = TestClient(main.app)
    target.account_email_outbox = client.account_email_outbox
    try:
        target_user = create_user(target, "target@example.com")
        users = client.get("/api/v1/admin/users?q=Target")
        assert users.status_code == 200
        item = users.json()["items"][0]
        assert item["id"] == target_user["id"]
        assert item["signup_method"] == "email_password"
        assert item["signup_ip"]
        assert item["phone_number"] == "+12025550123"

        invite = client.post("/api/v1/admin/admins", json={"email": "newadmin@example.com"})
        assert invite.status_code == 201
        invitation_body = client.account_email_outbox[-1][2]
        token = re.search(r"token=([A-Za-z0-9_-]+)", invitation_body).group(1)
        accepted = target.post("/api/v1/auth/admin-invite", json={
            "token": token,
            "display_name": "New Administrator",
            "username": "new_administrator",
            "phone_number": "+12025550124",
            "password": "a strong administrator password",
        })
        assert accepted.status_code == 201
        assert accepted.json()["role"] == "admin"
        assert target.get("/api/v1/auth/me").json()["role"] == "admin"
        reused = target.post("/api/v1/auth/admin-invite", json={
            "token": token,
            "display_name": "Another Administrator",
            "username": "another_administrator",
            "phone_number": "+12025550125",
            "password": "another strong administrator password",
        })
        assert reused.status_code == 400

        logs = client.get("/api/v1/admin/user-logs?q=account.created")
        assert logs.status_code == 200
        assert logs.json()["total"] >= 2
        cleared_users = client.request("DELETE", "/api/v1/admin/user-logs", json={"confirmation": "DELETE ALL USER LOGS"})
        assert cleared_users.status_code == 200
        assert client.get("/api/v1/admin/user-logs").json()["total"] == 0

        cleared_admins = client.request("DELETE", "/api/v1/admin/audit", json={"confirmation": "DELETE ALL ADMIN LOGS"})
        assert cleared_admins.status_code == 200
        assert cleared_admins.json()["retained_purge_record"] is True
        retained = client.get("/api/v1/admin/audit")
        assert retained.json()["total"] == 1
        assert retained.json()["items"][0]["action"] == "admin.audit_log.cleared"
    finally:
        target.close()


def test_test_detector_is_rejected_outside_test_environment(tmp_path):
    from app.detectors import create_detector

    try:
        create_detector("test", tmp_path / "missing.onnx", "production")
    except ValueError as error:
        assert "restricted" in str(error)
    else:
        raise AssertionError("The test-only detector must not be available in production.")


def _email_token(client):
    body = client.account_email_outbox[-1][2]
    return re.search(r"token=([A-Za-z0-9_-]+)", body).group(1)


def test_guest_and_authenticated_user_run_without_balance_or_guest_quota(client, image_bytes):
    initial = client.get("/api/v1/account/status").json()
    assert initial["is_authenticated"] is False
    assert initial["can_analyze"] is True
    assert "credits_remaining" not in initial
    assert client.get("/api/v1/credits/status").status_code == 404

    # Signed guest ownership allows repeat scans without creating an account.
    guest_headers = {"Idempotency-Key": "guest-submit-key-00001"}
    guest_first = client.post("/api/v1/analyses", files={"file": ("photo.png", image_bytes, "image/png")}, headers=guest_headers)
    guest_replay = client.post("/api/v1/analyses", files={"file": ("photo.png", image_bytes, "image/png")}, headers=guest_headers)
    assert guest_first.status_code == 201
    assert guest_replay.status_code == 200
    assert guest_replay.json()["analysis_id"] == guest_first.json()["analysis_id"]
    for index in range(5):
        assert upload(client, image_bytes, filename=f"guest-{index}.png").status_code == 201
    assert client.get("/api/v1/analyses").json()["total"] == 6

    # Registration links the guest's reports to the newly verified account.
    create_user(client, "free_access@example.com")
    auth_status = client.get("/api/v1/account/status").json()
    assert auth_status["is_authenticated"] is True
    assert auth_status["can_analyze"] is True
    assert client.get("/api/v1/analyses").json()["total"] == 6

    headers = {"Idempotency-Key": "user-submit-key-00001"}
    first = client.post("/api/v1/analyses", files={"file": ("photo.png", image_bytes, "image/png")}, headers=headers)
    replay = client.post("/api/v1/analyses", files={"file": ("photo.png", image_bytes, "image/png")}, headers=headers)
    assert first.status_code == 201
    assert replay.status_code == 200
    assert replay.json()["analysis_id"] == first.json()["analysis_id"]

    second = upload(client, image_bytes, filename="second.png")
    third = upload(client, image_bytes, filename="third.png")
    assert second.status_code == third.status_code == 201
    assert client.get("/api/v1/verifications").json()["total"] == 9
    assert client.get("/api/v1/account/status").json()["can_analyze"] is True
    assert client.get("/api/v1/admin/credits/adjust").status_code == 404


def test_signup_email_verification_gates_account_analysis_without_run_limits(client, image_bytes):
    signup = client.post("/api/v1/auth/signup", json=registration_payload("verified@example.com"))
    assert signup.status_code == 201
    before = client.get("/api/v1/account/status").json()
    assert before["requires_email_verification"] is True
    assert before["can_analyze"] is False
    blocked = upload(client, image_bytes)
    assert blocked.status_code == 403
    assert blocked.json()["code"] == "EMAIL_NOT_VERIFIED"

    token = _email_token(client)
    verified = client.post("/api/v1/auth/verify-email", json={"token": token})
    assert verified.status_code == 200
    assert client.get("/api/v1/account/status").json()["can_analyze"] is True

    for index in range(5):
        result = upload(client, image_bytes, filename=f"run-{index}.png")
        assert result.status_code == 201


def test_terminal_worker_failure_does_not_block_future_analysis(client, image_bytes, monkeypatch):
    monkeypatch.setattr(worker, "MAX_ATTEMPTS", 1)
    monkeypatch.setattr(worker, "scan_content_credentials", lambda _path: {"status": "not_present", "details": []})

    class BrokenDetector:
        def analyze(self, _data):
            raise RuntimeError("detector failure")

    monkeypatch.setattr(main, "synthetic_detector", BrokenDetector())
    create_user(client, "failure_recovery@example.com")
    created = upload(client, image_bytes)
    assert created.status_code == 201
    assert worker.process_one("refund-test") is True

    report = client.get(f"/api/v1/analyses/{created.json()['analysis_id']}").json()
    assert report["status"] == "failed"
    assert upload(client, image_bytes, filename="retry.png").status_code == 201


def test_concurrent_distinct_analyses_are_not_limited_by_balance(client, image_bytes):
    create_user(client, "race@example.com")
    cookie = client.cookies.get(main.COOKIE_NAME)

    def submit(key):
        with TestClient(main.app) as concurrent_client:
            concurrent_client.cookies.set(main.COOKIE_NAME, cookie)
            return concurrent_client.post(
                "/api/v1/analyses",
                files={"file": ("race.png", image_bytes, "image/png")},
                headers={"Idempotency-Key": key},
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(submit, ("race-submit-key-0001", "race-submit-key-0002")))
    assert all(response.status_code == 201 for response in responses)
    assert client.get("/api/v1/analyses").json()["total"] == 2


def test_concurrent_replay_of_same_idempotency_key_creates_one_analysis(client, image_bytes):
    create_user(client, "duplicate@example.com")
    cookie = client.cookies.get(main.COOKIE_NAME)
    key = "same-concurrent-submit-0001"

    def submit():
        with TestClient(main.app) as concurrent_client:
            concurrent_client.cookies.set(main.COOKIE_NAME, cookie)
            return concurrent_client.post(
                "/api/v1/analyses",
                files={"file": ("duplicate.png", image_bytes, "image/png")},
                headers={"Idempotency-Key": key},
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _index: submit(), range(2)))
    assert sorted(response.status_code for response in responses) == [200, 201]
    assert responses[0].json()["analysis_id"] == responses[1].json()["analysis_id"]
    assert client.get("/api/v1/analyses").json()["total"] == 1
    with main.SessionLocal() as db:
        user = db.scalar(main.select(main.User).where(main.User.email == "duplicate@example.com"))
        assert db.scalar(main.select(main.func.count()).select_from(main.Analysis).where(main.Analysis.owner_id == user.id)) == 1


def test_tampered_guest_cookie_and_cookie_rotation_do_not_create_usage_caps(client, image_bytes):
    client.cookies.set(main.GUEST_COOKIE_NAME, "not-a-valid-guest-cookie", domain="testserver.local", path="/")
    assert client.get("/api/v1/account/status").status_code == 200
    signed_cookie = client.cookies.get(main.GUEST_COOKIE_NAME)
    assert main._verify_guest_cookie(signed_cookie) is not None
    # A valid guest cookie can scan and retains access to its own report.
    guest_result = upload(client, image_bytes)
    assert guest_result.status_code == 201
    assert client.get("/api/v1/analyses").json()["total"] == 1

    first_guest_id = main._verify_guest_cookie(signed_cookie)
    client.cookies.delete(main.GUEST_COOKIE_NAME)
    assert client.get("/api/v1/account/status").status_code == 200
    second_guest_id = main._verify_guest_cookie(client.cookies.get(main.GUEST_COOKIE_NAME))
    assert second_guest_id and second_guest_id != first_guest_id
    assert client.get("/api/v1/analyses").json()["total"] == 0

    # Create account and upload
    create_user(client, "guest_converted@example.com")
    assert upload(client, image_bytes, filename="rotated.png").status_code == 201

    with main.SessionLocal() as db:
        rejected = db.scalar(main.select(main.AccessAuditEvent).where(main.AccessAuditEvent.action == "guest.cookie_rejected"))
        assert rejected is not None


def test_ip_account_cap_error_and_support_request_include_reference(client, monkeypatch):
    monkeypatch.setattr(main, "SUPPORT_CONTACT_EMAIL", "owner@example.com")
    accounts = [TestClient(main.app) for _ in range(4)]
    try:
        for index, account_client in enumerate(accounts[:3]):
            response = account_client.post(
                "/api/v1/auth/signup",
                json=registration_payload(f"network{index}@example.com"),
            )
            assert response.status_code == 201
        assert accounts[0].post("/api/v1/auth/login", json={"email": "network0@example.com", "password": "correct horse battery staple"}).status_code == 200

        fourth = accounts[3].post(
            "/api/v1/auth/signup",
            json=registration_payload("network4@example.com"),
        )
        assert fourth.status_code == 403
        assert fourth.json()["code"] == "IP_ACCOUNT_LIMIT"
        reference = fourth.json()["reference_id"]
        assert reference.startswith("CGS-BLK-")
        assert fourth.json()["contact_email"] == "owner@example.com"

        status = accounts[3].get("/api/v1/account/status").json()
        assert status["access_restricted"] is True
        assert status["reference_id"] == reference
        request = accounts[3].post(
            "/api/v1/support/unblock-request",
            json={"reference_id": reference, "name": "Network user", "email": "network4@example.com", "reason": "This is a shared office network."},
        )
        assert request.status_code == 201
        with main.SessionLocal() as db:
            row = db.scalar(main.select(main.UnblockRequest).where(main.UnblockRequest.reference_id == reference))
            assert row and row.status == "pending"
            assert len(main._linked_account_ids(db, main._ip_hash("127.0.0.1"))) == 3
    finally:
        for account_client in accounts:
            account_client.close()


def test_untrusted_forwarded_address_is_ignored(monkeypatch):
    from starlette.requests import Request

    monkeypatch.setattr(main, "TRUSTED_PROXY_CIDRS", ())
    request = Request({
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"x-forwarded-for", b"203.0.113.19")],
        "client": ("198.51.100.9", 51234),
        "server": ("testserver", 80),
        "scheme": "http",
        "query_string": b"",
    })
    assert main._client_ip(request) == "198.51.100.9"


def test_admin_unblock_raise_limit_and_whitelist_are_audited(client, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "operator@example.com")
    admin = create_user(client, "operator@example.com")
    from app.bootstrap_admin import bootstrap

    bootstrap("operator@example.com", "correct horse battery staple", "Operator")
    admin_client = TestClient(main.app)
    admin_client.cookies.set(main.COOKIE_NAME, client.cookies.get(main.COOKIE_NAME))
    blocked_client = TestClient(main.app)
    ip_value = "127.0.0.1"
    hashed_ip = main._ip_hash(ip_value)
    now = main.utcnow()
    with main.SessionLocal() as db:
        main.set_auth_rls_principal(db)
        extras = []
        for index in range(2):
            user = main.User(
                id=str(uuid.uuid4()),
                email=f"seed{index}@example.com",
                email_identity=f"seed{index}@example.com",
                display_name=f"Seed {index}",
                username=f"seed{index}",
                password_hash=main.PASSWORDS.hash("correct horse battery staple"),
                role="user",
                active=True,
                email_verified_at=now,
            )
            db.add(user)
            db.flush()
            db.add(main.IpAccountLink(ip_hash=hashed_ip, user_id=user.id))
            extras.append(user.id)
        block_id = str(uuid.uuid4())
        block = main.IpBlock(
            id=block_id,
            ip_hash=hashed_ip,
            reference_id="CGS-BLK-ADM001",
            reason="ACCOUNT_LIMIT_EXCEEDED",
            linked_account_ids_json=json.dumps([admin["id"], *extras]),
            status="blocked",
        )
        db.add(block)
        db.commit()

    limit_denied = blocked_client.post("/api/v1/auth/signup", json=registration_payload("next@example.com"))
    assert limit_denied.status_code == 403
    assert limit_denied.json()["code"] == "IP_ACCOUNT_LIMIT"
    raised = admin_client.post(f"/api/v1/admin/ip-blocks/{block_id}/raise-limit", json={"limit": 4})
    assert raised.status_code == 200
    allowed = blocked_client.post("/api/v1/auth/signup", json=registration_payload("next@example.com"))
    assert allowed.status_code == 201

    unblocked = admin_client.post(f"/api/v1/admin/ip-blocks/{block_id}/unblock")
    assert unblocked.status_code == 200
    fifth = blocked_client.post("/api/v1/auth/signup", json=registration_payload("fifth@example.com"))
    assert fifth.status_code == 201

    with main.SessionLocal() as db:
        main.set_auth_rls_principal(db)
        block_row = db.get(main.IpBlock, block_id)
        block_row.status = "blocked"
        block_row.updated_at = main.utcnow()
        db.commit()
    whitelisted = admin_client.post("/api/v1/admin/ip-whitelist", json={"ip_address": ip_value, "reason": "approved shared workplace"})
    assert whitelisted.status_code == 200
    sixth = blocked_client.post("/api/v1/auth/signup", json=registration_payload("sixth@example.com"))
    assert sixth.status_code == 201
    events = admin_client.get("/api/v1/admin/audit").json()["items"]
    actions = {item["action"] for item in events}
    assert {"admin.ip_block.limit_raised", "admin.ip_block.unblocked", "admin.ip_whitelisted"}.issubset(actions)
    admin_client.close()
    blocked_client.close()


def test_contact_inquiry_submission_and_validation(client, monkeypatch):
    monkeypatch.setattr(main, "SUPPORT_CONTACT_EMAIL", "support@example.com")

    # 1. Valid inquiry
    payload = {
        "name": "Alex Mercer",
        "email": "alex@mercer-security.com",
        "topic": "technical",
        "message": "We would like to test the dual-layer forensic pipeline for our research lab.",
    }
    response = client.post("/api/v1/support/contact", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["submitted"] is True
    assert "successfully submitted" in data["message"].lower()

    # 2. Honeypot check (silently absorbed without sending email or failing)
    spam_payload = {
        **payload,
        "website": "http://spamsite.xyz",
    }
    spam_resp = client.post("/api/v1/support/contact", json=spam_payload)
    assert spam_resp.status_code == 201
    assert spam_resp.json()["submitted"] is True

    # 3. Missing/invalid fields
    bad_payload = {
        "name": "",
        "email": "not-an-email",
        "topic": "product",
        "message": "short",
    }
    bad_resp = client.post("/api/v1/support/contact", json=bad_payload)
    assert bad_resp.status_code == 422


def test_admin_contact_inbox_and_settings_are_persistent_and_typed(client, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "operator@example.com")
    payload = {
        "name": "Jordan Lee",
        "email": "jordan@example.com",
        "topic": "Account help",
        "message": "Please help us review our account access settings.",
    }
    created = client.post("/api/v1/support/contact", json=payload)
    assert created.status_code == 201
    assert created.json()["inquiry_id"]
    assert client.get("/api/v1/admin/contact-inquiries").status_code == 401

    admin = create_user(client, "operator@example.com")
    from app.bootstrap_admin import bootstrap

    bootstrap("operator@example.com", "correct horse battery staple", "Operator")
    inbox = client.get("/api/v1/admin/contact-inquiries?q=jordan")
    assert inbox.status_code == 200
    assert len(inbox.json()["items"]) == 1
    inquiry = inbox.json()["items"][0]
    assert inquiry["email"] == payload["email"]
    assert inquiry["message"] == payload["message"]

    updated = client.patch(
        f"/api/v1/admin/contact-inquiries/{inquiry['id']}",
        json={"status": "in_progress", "admin_note": "Contacted the user."},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "in_progress"
    assert updated.json()["admin_note"] == "Contacted the user."

    wrong_confirmation = client.patch(
        "/api/v1/admin/settings",
        json={"registration_enabled": False, "confirmation": "save"},
    )
    wrong_type = client.patch(
        "/api/v1/admin/settings",
        json={"registration_enabled": "false", "confirmation": "APPLY PLATFORM SETTINGS"},
    )
    assert wrong_confirmation.status_code == 422
    assert wrong_type.status_code == 422

    changed = client.patch(
        "/api/v1/admin/settings",
        json={"registration_enabled": False, "confirmation": "APPLY PLATFORM SETTINGS"},
    )
    assert changed.status_code == 200
    assert changed.json()["settings"]["registration_enabled"] is False
    blocked_signup = client.post("/api/v1/auth/signup", json=registration_payload("new-user@example.com"))
    assert blocked_signup.status_code == 403
    assert blocked_signup.json()["code"] == "REGISTRATION_PAUSED"

    secondary_session = TestClient(main.app)
    try:
        sign_in(secondary_session, admin["email"])
        bad_danger_confirmation = client.post(
            "/api/v1/admin/security/revoke-other-sessions",
            json={"confirmation": "revoke"},
        )
        assert bad_danger_confirmation.status_code == 422
        revoked = client.post(
            "/api/v1/admin/security/revoke-other-sessions",
            json={"confirmation": "REVOKE OTHER SESSIONS"},
        )
        assert revoked.status_code == 200
        assert revoked.json()["revoked_sessions"] == 1
        assert client.get("/api/v1/auth/me").status_code == 200
        assert secondary_session.get("/api/v1/auth/me").status_code == 401
    finally:
        secondary_session.close()


def test_admin_inspection_ledger_search_returns_minimal_account_details(client, image_bytes, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "operator@example.com")
    user = create_user(client, "operator@example.com")
    from app.bootstrap_admin import bootstrap

    bootstrap("operator@example.com", "correct horse battery staple", "Operator")
    created = upload(client, image_bytes, filename="ledger sample.png").json()
    assert worker.process_one("test-worker") is True

    response = client.get("/api/v1/admin/analyses?q=ledger%20sample")
    assert response.status_code == 200
    assert response.json()["total"] == 1
    record = response.json()["items"][0]
    assert record["analysis_id"] == created["analysis_id"]
    assert record["owner_email"] == user["email"]
    assert record["file"]["original_filename"] == "ledger sample.png"
    assert "image_url" not in record["file"] or record["file"]["image_url"] is None

