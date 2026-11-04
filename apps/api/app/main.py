from __future__ import annotations

import hashlib
import hmac
import io
import ipaddress
import json
import logging
import os
import re
import secrets
import smtplib
import unicodedata
import uuid
import warnings
from contextlib import asynccontextmanager
from datetime import date, datetime, time, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Annotated
from urllib.parse import quote, unquote, urlsplit

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from dotenv import load_dotenv
from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    File,
    Header,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.routing import APIRoute
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, EmailStr, Field, StrictBool, field_validator
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    case,
    create_engine,
    delete,
    event,
    func,
    or_,
    select,
    text,
    update,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    sessionmaker,
)

from app.detectors import create_detector

load_dotenv(Path(__file__).resolve().parents[3] / ".env")


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


APP_ENV = _env("APP_ENV", "development").strip().lower()
DATABASE_URL = _env("DATABASE_URL", "sqlite:///./data/cgs_deepfake_shield.db")
STORAGE_DIR = Path(_env("STORAGE_DIR", "./storage")).resolve()
MODEL_PATH = Path(
    _env("AI_MODEL_PATH", "./models/community_forensics_low_quality_fp16.onnx")
).resolve()
SESSION_TTL_HOURS = max(1, int(_env("SESSION_TTL_HOURS", "168")))
MAX_UPLOAD_BYTES = max(1, int(_env("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024))))
MAX_VIDEO_BYTES = max(MAX_UPLOAD_BYTES, int(_env("MAX_VIDEO_BYTES", str(50 * 1024 * 1024))))
MAX_VIDEO_SECONDS = max(1, int(_env("MAX_VIDEO_SECONDS", "300")))
MAX_IMAGE_PIXELS = max(1, int(_env("MAX_IMAGE_PIXELS", "40000000")))
COOKIE_SECURE = _env("SESSION_COOKIE_SECURE", "false").strip().lower() == "true"
COOKIE_NAME = "cgs_session"
_default_origins = "" if APP_ENV == "production" else "http://127.0.0.1:3000,http://localhost:3000"
ALLOWED_ORIGINS = {
    origin.strip().rstrip("/")
    for origin in _env("APP_ORIGINS", _default_origins).split(",")
    if origin.strip()
}
ALLOWED_EXTENSIONS = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".webp": "WEBP",
    ".mp4": "MP4",
    ".webm": "WEBM",
    ".mov": "MOV",
    ".avi": "AVI",
    ".mkv": "MKV",
    ".wav": "WAV",
    ".mp3": "MP3",
    ".flac": "FLAC",
    ".ogg": "OGG",
    ".m4a": "M4A",
    ".aac": "AAC",
}
MEDIA_TYPES = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
    "MP4": "video/mp4",
    "WEBM": "video/webm",
    "MOV": "video/quicktime",
    "AVI": "video/x-msvideo",
    "MKV": "video/x-matroska",
    "WAV": "audio/wav",
    "MP3": "audio/mpeg",
    "FLAC": "audio/flac",
    "OGG": "audio/ogg",
    "M4A": "audio/mp4",
    "AAC": "audio/aac",
}
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
PASSWORDS = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
DUMMY_PASSWORD_HASH = PASSWORDS.hash(secrets.token_urlsafe(32))
APP_SECRET_KEY = _env("APP_SECRET_KEY", "development-only-rate-limit-pepper")
if APP_ENV == "production" and (
    len(APP_SECRET_KEY) < 32
    or "replace-with" in APP_SECRET_KEY
    or "development-only" in APP_SECRET_KEY
):
    raise RuntimeError(
        "Set APP_SECRET_KEY to a random secret of at least 32 characters before starting in "
        "production."
    )
if APP_ENV == "production" and not COOKIE_SECURE:
    raise RuntimeError("Set SESSION_COOKIE_SECURE=true before starting in production.")
if APP_ENV == "production" and not ALLOWED_ORIGINS:
    raise RuntimeError(
        "Set APP_ORIGINS to the exact browser origins before starting in production."
    )
if "*" in ALLOWED_ORIGINS:
    raise RuntimeError("APP_ORIGINS must contain exact origins; wildcard CORS is not supported.")
for configured_origin in ALLOWED_ORIGINS:
    parsed_origin = urlsplit(configured_origin)
    if (
        parsed_origin.scheme not in {"http", "https"}
        or not parsed_origin.netloc
        or parsed_origin.path
        or parsed_origin.query
        or parsed_origin.fragment
        or parsed_origin.username
        or parsed_origin.password
    ):
        raise RuntimeError(f"Invalid APP_ORIGINS entry: {configured_origin!r}")
RATE_LIMIT_SECRET = APP_SECRET_KEY.encode("utf-8")
RATE_LIMIT_AUTH_LIMIT = max(1, int(_env("RATE_LIMIT_AUTH_LIMIT", "12")))
RATE_LIMIT_AUTH_WINDOW_SECONDS = max(60, int(_env("RATE_LIMIT_AUTH_WINDOW_SECONDS", "900")))
RATE_LIMIT_AUTH_IDENTITY_LIMIT = max(
    1,
    int(_env("RATE_LIMIT_AUTH_IDENTITY_LIMIT", _env("RATE_LIMIT_AUTH_EMAIL_LIMIT", "12"))),
)
RATE_LIMIT_UPLOAD_LIMIT = max(1, int(_env("RATE_LIMIT_UPLOAD_LIMIT", "30")))
RATE_LIMIT_UPLOAD_WINDOW_SECONDS = max(60, int(_env("RATE_LIMIT_UPLOAD_WINDOW_SECONDS", "3600")))
GUEST_COOKIE_NAME = _env("GUEST_COOKIE_NAME", "cgs_guest")
GUEST_COOKIE_TTL_DAYS = max(1, int(_env("GUEST_COOKIE_TTL_DAYS", "365")))
MAX_ACCOUNTS_PER_IP = max(1, int(_env("MAX_ACCOUNTS_PER_IP", "3")))
IP_ACCOUNT_WINDOW_DAYS = max(0, int(_env("IP_ACCOUNT_WINDOW_DAYS", "0")))
IP_BLOCK_MODE = _env("IP_BLOCK_MODE", "soft").strip().lower()
if IP_BLOCK_MODE not in {"soft", "hard"}:
    raise RuntimeError("IP_BLOCK_MODE must be 'soft' or 'hard'.")
SUPPORT_CONTACT_EMAIL = _env("SUPPORT_CONTACT_EMAIL", "").strip()
TRUSTED_PROXY_CIDRS = tuple(
    ipaddress.ip_network(value.strip(), strict=False)
    for value in _env("TRUSTED_PROXY_CIDRS", "").split(",")
    if value.strip()
)
EMAIL_VERIFICATION_TTL_HOURS = max(1, int(_env("EMAIL_VERIFICATION_TTL_HOURS", "24")))
PASSWORD_RESET_TTL_HOURS = max(1, int(_env("PASSWORD_RESET_TTL_HOURS", "1")))
UPLOAD_RETENTION_DAYS = max(0, int(_env("UPLOAD_RETENTION_DAYS", "0")))
DISPOSABLE_EMAIL_DOMAINS = {
    value.strip().casefold()
    for value in _env(
        "DISPOSABLE_EMAIL_DOMAINS", "mailinator.com,tempmail.com,10minutemail.com"
    ).split(",")
    if value.strip()
}
SMTP_HOST = _env("SMTP_HOST", "").strip()
SMTP_PORT = max(1, int(_env("SMTP_PORT", "587")))
SMTP_USERNAME = _env("SMTP_USERNAME", "").strip()
SMTP_PASSWORD = _env("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = _env("SMTP_FROM_EMAIL", "").strip()
SMTP_STARTTLS = _env("SMTP_STARTTLS", "true").strip().lower() == "true"
if APP_ENV == "production" and (not SMTP_HOST or not SMTP_FROM_EMAIL):
    raise RuntimeError(
        "Set SMTP_HOST and SMTP_FROM_EMAIL before enabling production email verification and "
        "password recovery."
    )
if APP_ENV == "production" and not SUPPORT_CONTACT_EMAIL:
    raise RuntimeError("Set SUPPORT_CONTACT_EMAIL before starting in production.")
PUBLIC_APP_ORIGIN = _env("PUBLIC_APP_ORIGIN", "http://127.0.0.1:3000").strip().rstrip("/")
RATE_LIMIT_ANALYSIS_OWNER_LIMIT = max(
    1, int(_env("RATE_LIMIT_ANALYSIS_OWNER_LIMIT", _env("RATE_LIMIT_VERIFY_OWNER_LIMIT", "12")))
)
RATE_LIMIT_ANALYSIS_IP_LIMIT = max(
    1,
    int(
        _env(
            "RATE_LIMIT_ANALYSIS_IP_LIMIT",
            _env("RATE_LIMIT_VERIFY_IP_LIMIT", str(RATE_LIMIT_UPLOAD_LIMIT)),
        )
    ),
)
RATE_LIMIT_ANALYSIS_WINDOW_SECONDS = max(
    60,
    int(
        _env(
            "RATE_LIMIT_ANALYSIS_WINDOW_SECONDS",
            _env("RATE_LIMIT_VERIFY_WINDOW_SECONDS", str(RATE_LIMIT_UPLOAD_WINDOW_SECONDS)),
        )
    ),
)
RATE_LIMIT_SUPPORT_LIMIT = max(1, int(_env("RATE_LIMIT_SUPPORT_LIMIT", "3")))
logger = logging.getLogger("cgs.api")
synthetic_detector = create_detector(_env("AI_DETECTOR_PROVIDER", "local"), MODEL_PATH, APP_ENV)

if DATABASE_URL.startswith("sqlite:"):
    db_file = DATABASE_URL.removeprefix("sqlite:///")
    if db_file != ":memory:":
        Path(db_file).parent.mkdir(parents=True, exist_ok=True)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite:") else {},
)
if APP_ENV == "production":
    if engine.dialect.name != "postgresql":
        raise RuntimeError(
            "Production requires PostgreSQL so database row-level security can be enforced."
        )
    with engine.connect() as connection:
        can_bypass_rls = connection.execute(
            text("SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname = current_user")
        ).scalar_one()
    if can_bypass_rls:
        raise RuntimeError(
            "The production DATABASE_URL role must not be a PostgreSQL superuser or BYPASSRLS role."
        )
if DATABASE_URL.startswith("sqlite:"):
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@event.listens_for(Session, "after_begin")
def _apply_postgres_rls_context(session: Session, _transaction, connection) -> None:
    if connection.dialect.name != "postgresql":
        return
    actor, user_id, session_hash = session.info.get("rls_principal", ("anonymous", "", ""))
    connection.execute(
        text(
            "SELECT set_config('cgs.actor', :actor, true), "
            "set_config('cgs.user_id', :user_id, true), "
            "set_config('cgs.session_hash', :session_hash, true)"
        ),
        {"actor": actor, "user_id": user_id, "session_hash": session_hash},
    ).close()


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(80))
    username: Mapped[str | None] = mapped_column(String(32), unique=True, index=True, nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(16), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    email_identity: Mapped[str] = mapped_column(String(320), unique=True, index=True, default="")
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    email_verification_token_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    email_verification_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    password_reset_token_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    password_reset_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    role: Mapped[str] = mapped_column(String(16), default="user")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    signup_method: Mapped[str] = mapped_column(
        String(32), default="email_password", server_default="email_password"
    )
    signup_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: utcnow())


class UserSession(Base):
    __tablename__ = "sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Analysis(Base):
    __tablename__ = "analyses"
    __table_args__ = (
        CheckConstraint(
            (
                "(owner_id IS NOT NULL AND guest_id IS NULL) OR (owner_id IS NULL AND guest_id "
                "IS NOT NULL)"
            ),
            name="ck_analysis_exactly_one_owner",
        ),
        UniqueConstraint("owner_id", "idempotency_key", name="uq_analyses_user_idempotency_key"),
        UniqueConstraint("guest_id", "idempotency_key", name="uq_analyses_guest_idempotency_key"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    owner_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True
    )
    guest_id: Mapped[str | None] = mapped_column(
        ForeignKey("guest_sessions.guest_id", ondelete="CASCADE"), index=True, nullable=True
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="completed", index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    object_key: Mapped[str] = mapped_column(String(80))
    preview_key: Mapped[str] = mapped_column(String(80))
    detected_mime_type: Mapped[str] = mapped_column(String(40))
    size_bytes: Mapped[int] = mapped_column(Integer)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    metadata_json: Mapped[str] = mapped_column(Text)
    detector_result_json: Mapped[str] = mapped_column(Text)
    provenance_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: utcnow(), index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class InferenceJob(Base):
    __tablename__ = "inference_jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    analysis_id: Mapped[str] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"), unique=True, index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: utcnow(), index=True
    )
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    worker_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: utcnow())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: utcnow(), onupdate=lambda: utcnow()
    )





class RateLimitBucket(Base):
    __tablename__ = "rate_limit_buckets"

    key_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, nullable=False)
    resets_at: Mapped[int] = mapped_column(Integer, nullable=False, index=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    actor_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(80), index=True)
    subject_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    details_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: utcnow(), index=True
    )


class GuestSession(Base):
    __tablename__ = "guest_sessions"

    guest_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    linked_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: utcnow())
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: utcnow(), index=True
    )


class UserActivityEvent(Base):
    __tablename__ = "user_activity_events"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    actor_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(80), index=True)
    subject_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    details_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: utcnow(), index=True
    )


class AdminInvitation(Base):
    __tablename__ = "admin_invitations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(320), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    invited_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: utcnow())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class IpAccountLink(Base):
    __tablename__ = "ip_account_links"
    __table_args__ = (UniqueConstraint("ip_hash", "user_id", name="uq_ip_account_link"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ip_hash: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: utcnow()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: utcnow(), index=True
    )


class IpEnforcementGuard(Base):
    """Per-hash write lock so simultaneous account/guest checks see committed usage."""

    __tablename__ = "ip_enforcement_guards"

    ip_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    touch_count: Mapped[int] = mapped_column(Integer, default=0)


class IpBlock(Base):
    __tablename__ = "ip_blocks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ip_hash: Mapped[str] = mapped_column(String(64), index=True)
    reference_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="blocked", index=True)
    reason: Mapped[str] = mapped_column(String(80), default="ACCOUNT_LIMIT_EXCEEDED")
    linked_account_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    raised_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: utcnow(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: utcnow(), onupdate=lambda: utcnow()
    )
    resolved_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class IpWhitelist(Base):
    __tablename__ = "ip_whitelist"

    ip_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    added_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: utcnow())
    reason: Mapped[str] = mapped_column(String(240), default="")


class UnblockRequest(Base):
    __tablename__ = "unblock_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    reference_id: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(320))
    reason: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    resolved_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolution_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: utcnow(), index=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AccessAuditEvent(Base):
    __tablename__ = "access_audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    action: Mapped[str] = mapped_column(String(80), index=True)
    reason: Mapped[str | None] = mapped_column(String(80), nullable=True)
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    reference_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    details_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: utcnow(), index=True
    )


class WorkerHeartbeat(Base):
    __tablename__ = "worker_heartbeats"

    worker_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    process_id: Mapped[str] = mapped_column(String(24))


class ContactInquiry(Base):
    __tablename__ = "contact_inquiries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(320), index=True)
    topic: Mapped[str] = mapped_column(String(100))
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="new", index=True)
    admin_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: utcnow(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: utcnow(), onupdate=lambda: utcnow()
    )


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value_json: Mapped[str] = mapped_column(Text)
    updated_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: utcnow(), onupdate=lambda: utcnow()
    )


def _set_rls_context_on_connection(connection, actor: str, user_id: str, session_hash: str) -> None:
    connection.execute(
        text(
            "SELECT set_config('cgs.actor', :actor, true), "
            "set_config('cgs.user_id', :user_id, true), "
            "set_config('cgs.session_hash', :session_hash, true)"
        ),
        {"actor": actor, "user_id": user_id, "session_hash": session_hash},
    ).close()


def _set_rls_principal(db: Session, actor: str, user_id: str = "") -> None:
    """Set transaction-local identity used by PostgreSQL row security policies."""
    _previous_actor, _previous_user_id, session_hash = db.info.get(
        "rls_principal", ("anonymous", "", "")
    )
    db.info["rls_principal"] = (actor, user_id, session_hash)
    if engine.dialect.name == "postgresql" and db.in_transaction():
        _set_rls_context_on_connection(db.connection(), actor, user_id, session_hash)


def set_auth_rls_principal(db: Session) -> None:
    _set_rls_principal(db, "auth")


def _set_rls_session_hash(db: Session, session_hash: str) -> None:
    actor, user_id, _previous_hash = db.info.get("rls_principal", ("anonymous", "", ""))
    db.info["rls_principal"] = (actor, user_id, session_hash)
    if engine.dialect.name == "postgresql" and db.in_transaction():
        _set_rls_context_on_connection(db.connection(), actor, user_id, session_hash)


def set_worker_rls_principal(db: Session) -> None:
    _set_rls_principal(db, "worker")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _runtime_setting(db: Session, key: str, default: bool) -> bool:
    row = db.get(SystemSetting, key)
    if not row:
        return default
    try:
        value = json.loads(row.value_json)
    except (TypeError, ValueError):
        logger.error("Ignoring malformed platform setting %s", key)
        return default
    return value if type(value) is bool else default


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return (
        value.replace(tzinfo=timezone.utc)
        if value.tzinfo is None
        else value.astimezone(timezone.utc)
    )


def _rate_limit_key(value: str) -> str:
    import hmac

    return hmac.new(RATE_LIMIT_SECRET, value.encode("utf-8"), hashlib.sha256).hexdigest()


def _consume_rate_limit(key: str, limit: int, window_seconds: int) -> tuple[int, int]:
    """Atomically increment a fixed-window counter in SQLite or PostgreSQL."""
    now = int(datetime.now(timezone.utc).timestamp())
    db = SessionLocal()
    try:
        dialect = engine.dialect.name
        if dialect == "sqlite":
            from sqlalchemy.dialects.sqlite import insert as dialect_insert
        elif dialect == "postgresql":
            from sqlalchemy.dialects.postgresql import insert as dialect_insert
        else:
            raise RuntimeError("Persistent rate limiting requires SQLite or PostgreSQL.")
        statement = dialect_insert(RateLimitBucket).values(
            key_hash=_rate_limit_key(key), count=1, resets_at=now + window_seconds
        )
        statement = statement.on_conflict_do_update(
            index_elements=[RateLimitBucket.key_hash],
            set_={
                "count": case(
                    (RateLimitBucket.resets_at <= now, 1), else_=RateLimitBucket.count + 1
                ),
                "resets_at": case(
                    (RateLimitBucket.resets_at <= now, now + window_seconds),
                    else_=RateLimitBucket.resets_at,
                ),
            },
        ).returning(RateLimitBucket.count, RateLimitBucket.resets_at)
        count, resets_at = db.execute(statement).one()
        db.commit()
        if now % 60 == 0:
            db.execute(
                RateLimitBucket.__table__.delete().where(RateLimitBucket.resets_at < now - 86_400)
            )
            db.commit()
        return int(count), int(resets_at)
    finally:
        db.close()


def _enforce_auth_identity_limit(action: str, identity: str) -> None:
    count, resets_at = _consume_rate_limit(
        f"auth-identity:{action}:{identity.strip().casefold()}",
        RATE_LIMIT_AUTH_IDENTITY_LIMIT,
        RATE_LIMIT_AUTH_WINDOW_SECONDS,
    )
    if count > RATE_LIMIT_AUTH_IDENTITY_LIMIT:
        retry_after = max(1, resets_at - int(datetime.now(timezone.utc).timestamp()))
        raise HTTPException(
            status_code=429,
            detail={
                "code": "RATE_LIMITED",
                "message": "Too many requests. Wait before trying again.",
            },
            headers={"Retry-After": str(retry_after), "Cache-Control": "no-store"},
        )


def _request_limits(request: Request) -> list[tuple[str, int, int]]:
    path = request.url.path
    if path in {
        "/api/v1/auth/login",
        "/api/v1/auth/signup",
        "/api/v1/auth/forgot-password",
        "/api/v1/auth/reset-password",
        "/api/v1/auth/verify-email",
        "/api/v1/auth/resend-verification",
        "/api/v1/auth/admin-invite",
    }:
        return [(path.rsplit("/", 1)[-1], RATE_LIMIT_AUTH_LIMIT, RATE_LIMIT_AUTH_WINDOW_SECONDS)]
    if path == "/api/v1/analyses" and request.method == "POST":
        return [
            ("analysis-ip", RATE_LIMIT_ANALYSIS_IP_LIMIT, RATE_LIMIT_ANALYSIS_WINDOW_SECONDS),
            ("analysis-owner", RATE_LIMIT_ANALYSIS_OWNER_LIMIT, RATE_LIMIT_ANALYSIS_WINDOW_SECONDS),
        ]
    if path == "/api/v1/support/unblock-request" and request.method == "POST":
        return [("unblock-request", RATE_LIMIT_SUPPORT_LIMIT, 86400)]
    if path.startswith("/api/v1/admin/"):
        limits = [("admin-request", 120, 60)]
        if request.method in {"POST", "PATCH", "PUT", "DELETE"}:
            limits.append(("admin-write", 40, 60))
        return limits
    return []


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _normalized_email(value: str) -> str:
    return value.strip().casefold()


def _email_identity(value: str) -> str:
    email = _normalized_email(value)
    local, separator, domain = email.rpartition("@")
    if not separator:
        return email
    if domain in {"gmail.com", "googlemail.com"}:
        local = local.split("+", 1)[0].replace(".", "")
        domain = "gmail.com"
    return f"{local}@{domain}"


def _email_domain(value: str) -> str:
    return _normalized_email(value).rsplit("@", 1)[-1]


def _client_ip(request: Request) -> str:
    """Only consume forwarded addresses when the immediate peer is configured as trusted."""
    peer = request.client.host if request.client else "127.0.0.1"
    try:
        peer_ip = ipaddress.ip_address(peer)
    except ValueError:
        return "127.0.0.1"
    if not any(peer_ip in proxy for proxy in TRUSTED_PROXY_CIDRS):
        return peer_ip.compressed
    forwarded = request.headers.get("x-forwarded-for", "")
    chain: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    for part in forwarded.split(","):
        try:
            chain.append(ipaddress.ip_address(part.strip()))
        except ValueError:
            continue
    # Walk from the trusted proxy inward; the first non-proxy address is the client.
    for candidate in reversed([*chain, peer_ip]):
        if not any(candidate in proxy for proxy in TRUSTED_PROXY_CIDRS):
            return candidate.compressed
    return peer_ip.compressed


def _ip_hash(ip_value: str) -> str:
    return hmac.new(APP_SECRET_KEY.encode(), f"ip:{ip_value}".encode(), hashlib.sha256).hexdigest()


def _guest_cookie_value(guest_id: str) -> str:
    signature = hmac.new(
        APP_SECRET_KEY.encode(), f"guest:{guest_id}".encode(), hashlib.sha256
    ).hexdigest()
    return f"{guest_id}.{signature}"


def _verify_guest_cookie(value: str | None) -> str | None:
    if not value or "." not in value:
        return None
    guest_id, signature = value.rsplit(".", 1)
    if not re.fullmatch(r"[A-Za-z0-9_-]{40,48}", guest_id) or not re.fullmatch(
        r"[a-f0-9]{64}", signature
    ):
        return None
    expected = _guest_cookie_value(guest_id).rsplit(".", 1)[1]
    return guest_id if hmac.compare_digest(signature, expected) else None


def _set_guest_rls_principal(db: Session, guest_id: str) -> None:
    _set_rls_principal(db, "guest")
    if engine.dialect.name == "postgresql" and db.in_transaction():
        db.connection().execute(
            text("SELECT set_config('cgs.guest_id', :guest_id, true)"),
            {"guest_id": guest_id},
        ).close()


class APIProblem(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        reference_id: str | None = None,
        contact_email: str | None = None,
    ):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.reference_id = reference_id
        self.contact_email = contact_email


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _admin_emails() -> set[str]:
    return {_normalized_email(e) for e in _env("ADMIN_EMAILS", "").split(",") if e.strip()}


def _is_protected_admin(email: str) -> bool:
    return _normalized_email(email) in _admin_emails()


class SignupPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=15, max_length=128)
    display_name: str = Field(min_length=1, max_length=80)
    username: str = Field(min_length=3, max_length=32)
    phone_number: str = Field(min_length=9, max_length=16)
    return_to: str | None = Field(default=None, max_length=512)

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        cleaned = value.strip()
        bidi_controls = {"LRE", "RLE", "LRO", "RLO", "PDF", "LRI", "RLI", "FSI", "PDI"}
        if not cleaned or any(
            unicodedata.category(char) in {"Cc", "Cs"}
            or unicodedata.bidirectional(char) in bidi_controls
            for char in cleaned
        ):
            raise ValueError("Enter a display name without control characters.")
        return cleaned

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        cleaned = value.strip().casefold()
        if not re.fullmatch(r"[a-z0-9_]{3,32}", cleaned):
            raise ValueError("Use 3–32 letters, numbers, or underscores for the username.")
        return cleaned

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value: str) -> str:
        if not re.fullmatch(r"\+[1-9][0-9]{7,14}", value):
            raise ValueError("Enter a valid international phone number.")
        return value

    @field_validator("return_to")
    @classmethod
    def validate_return_path(cls, value: str | None) -> str | None:
        if value is not None and (
            not value.startswith("/")
            or value.startswith("//")
            or "\\" in value
            or "\r" in value
            or "\n" in value
        ):
            raise ValueError("The return path must be a local application path.")
        return value


class AdminInviteAcceptPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=32, max_length=256)
    password: str = Field(min_length=15, max_length=128)
    display_name: str = Field(min_length=1, max_length=80)
    username: str = Field(min_length=3, max_length=32)
    phone_number: str = Field(min_length=9, max_length=16)

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        cleaned = value.strip()
        bidi_controls = {"LRE", "RLE", "LRO", "RLO", "PDF", "LRI", "RLI", "FSI", "PDI"}
        if not cleaned or any(
            unicodedata.category(char) in {"Cc", "Cs"}
            or unicodedata.bidirectional(char) in bidi_controls
            for char in cleaned
        ):
            raise ValueError("Enter a display name without control characters.")
        return cleaned

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        cleaned = value.strip().casefold()
        if not re.fullmatch(r"[a-z0-9_]{3,32}", cleaned):
            raise ValueError("Use 3–32 letters, numbers, or underscores for the username.")
        return cleaned

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value: str) -> str:
        if not re.fullmatch(r"\+[1-9][0-9]{7,14}", value):
            raise ValueError("Enter a valid international phone number.")
        return value


class ReturnToPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    return_to: str | None = Field(default=None, max_length=512)

    @field_validator("return_to")
    @classmethod
    def validate_return_path(cls, value: str | None) -> str | None:
        if value is not None and (
            not value.startswith("/")
            or value.startswith("//")
            or "\\" in value
            or "\r" in value
            or "\n" in value
        ):
            raise ValueError("The return path must be a local application path.")
        return value


class LoginPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=128)


class VerifyEmailPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=20, max_length=256)


class ForgotPasswordPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    return_to: str | None = Field(default=None, max_length=512)

    @field_validator("return_to")
    @classmethod
    def validate_return_path(cls, value: str | None) -> str | None:
        if value is not None and (
            not value.startswith("/")
            or value.startswith("//")
            or "\\" in value
            or "\r" in value
            or "\n" in value
        ):
            raise ValueError("The return path must be a local application path.")
        return value


class ResetPasswordPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=20, max_length=256)
    password: str = Field(min_length=15, max_length=128)


class UnblockRequestPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reference_id: str = Field(min_length=8, max_length=32)
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    reason: str = Field(min_length=10, max_length=1000)
    website: str = Field(default="", max_length=200)


class ContactInquiryPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    topic: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=10, max_length=3000)
    website: str = Field(default="", max_length=200)


class AdminContactInquiryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str | None = Field(default=None, pattern="^(new|in_progress|resolved)$")
    admin_note: str | None = Field(default=None, max_length=2000)

    @field_validator("admin_note")
    @classmethod
    def normalize_admin_note(cls, value: str | None) -> str | None:
        value = value.strip() if value is not None else None
        return value or None


class AdminSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    registration_enabled: StrictBool | None = None
    inspections_enabled: StrictBool | None = None
    confirmation: str = Field(min_length=1, max_length=40)

    @field_validator("confirmation")
    @classmethod
    def verify_settings_confirmation(cls, value: str) -> str:
        if value != "APPLY PLATFORM SETTINGS":
            raise ValueError("Type APPLY PLATFORM SETTINGS exactly to save platform settings.")
        return value


class AdminDangerActionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirmation: str = Field(min_length=1, max_length=40)

    @field_validator("confirmation")
    @classmethod
    def verify_danger_confirmation(cls, value: str) -> str:
        if value != "REVOKE OTHER SESSIONS":
            raise ValueError(
                "Type REVOKE OTHER SESSIONS exactly to revoke the other administrator sessions."
            )
        return value


class AdminLogPurgePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirmation: str = Field(min_length=1, max_length=40)


class AdminInvitationCreatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr


class AdminRoleActionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: str = Field(pattern="^(disable|restore|revoke)$")


class AdminBlockIpPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ip_address: str = Field(min_length=3, max_length=64)
    reason: str = Field(default="Administrator network restriction", max_length=240)


class AdminTrafficCleanupPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirmation: str = Field(min_length=1, max_length=48)


class RaiseIpLimitPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    limit: int = Field(ge=1, le=10000)


class WhitelistIpPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ip_address: str = Field(min_length=3, max_length=64)
    reason: str = Field(default="", max_length=240)


class ResolveUnblockPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str = Field(pattern="^(approved|rejected)$")
    note: str = Field(default="", max_length=500)


class AdminUserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active: StrictBool | None = None


class AdminUserDeletePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirmation: str = Field(min_length=1, max_length=400)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: str
    display_name: str
    username: str | None = None
    phone_number: str | None = None
    role: str
    created_at: datetime
    email_verified_at: datetime | None = None

    @field_validator("created_at", mode="before")
    @classmethod
    def normalize_created_at(cls, value):
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class HealthOut(BaseModel):
    status: str
    database: str | None = None
    storage: str | None = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    STORAGE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name != "nt":
        STORAGE_DIR.chmod(0o700)
    if APP_ENV != "production" and _env("AUTO_CREATE_SCHEMA", "true").lower() == "true":
        Base.metadata.create_all(engine)
    yield


app = FastAPI(
    title="CGS DeepFake Shield API",
    version="0.1.0",
    description="Image integrity and evidence reporting API",
    debug=APP_ENV != "production",
    docs_url=None if APP_ENV == "production" else "/docs",
    redoc_url=None if APP_ENV == "production" else "/redoc",
    openapi_url=None if APP_ENV == "production" else "/openapi.json",
    lifespan=lifespan,
)


@app.exception_handler(APIProblem)
async def _api_problem_response(request: Request, problem: APIProblem) -> JSONResponse:
    content: dict[str, object] = {"code": problem.code, "message": problem.message}
    if problem.reference_id:
        content["reference_id"] = problem.reference_id
        content["contact_email"] = problem.contact_email
    return _apply_security_headers(
        JSONResponse(status_code=problem.status_code, content=content), request.url.path
    )


def _apply_security_headers(response: Response, path: str) -> Response:
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
    response.headers.setdefault("X-DNS-Prefetch-Control", "off")
    response.headers.setdefault(
        "Content-Security-Policy",
        (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; media-src 'self' data: blob:; font-src 'self' data:; "
            "connect-src 'self'; frame-ancestors 'none'; form-action 'self';"
        ),
    )
    if APP_ENV == "production":
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=63072000; includeSubDomains"
        )
    if path.startswith("/api/v1/"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


class _RequestBodyTooLarge(Exception):
    pass


class RequestBodySizeLimitMiddleware:
    """Bound upload bodies even when a client omits Content-Length."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if (
            scope.get("type") != "http"
            or scope.get("method") != "POST"
            or scope.get("path") != "/api/v1/analyses"
        ):
            await self.app(scope, receive, send)
            return

        limit = max(MAX_UPLOAD_BYTES, MAX_VIDEO_BYTES) + 1024 * 1024
        headers = dict(scope.get("headers", []))
        content_length = headers.get(b"content-length", b"").decode("ascii", errors="ignore")
        if content_length.isdecimal() and int(content_length) > limit:
            response = _apply_security_headers(
                JSONResponse(
                    status_code=413, content={"detail": "The uploaded request is too large."}
                ),
                scope.get("path", ""),
            )
            await response(scope, receive, send)
            return

        received = 0
        response_started = False

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message.get("type") == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    scope["cgs_request_body_too_large"] = True
                    raise _RequestBodyTooLarge
            return message

        async def tracked_send(message):
            nonlocal response_started
            if scope.get("cgs_request_body_too_large"):
                return
            if message.get("type") == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracked_send)
        except _RequestBodyTooLarge:
            pass
        if scope.get("cgs_request_body_too_large"):
            if response_started:
                return
            response = _apply_security_headers(
                JSONResponse(
                    status_code=413, content={"detail": "The uploaded request is too large."}
                ),
                scope.get("path", ""),
            )
            await response(scope, receive, send)


if APP_ENV == "production":

    async def _production_internal_error(request: Request, _exception: Exception) -> JSONResponse:
        logger.error("Unhandled API exception (path=%s)", request.url.path)
        return _apply_security_headers(
            JSONResponse(
                status_code=500, content={"detail": "An internal service error occurred."}
            ),
            request.url.path,
        )

    app.add_exception_handler(Exception, _production_internal_error)


@app.middleware("http")
async def same_origin_mutations(request: Request, call_next):
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        origin = request.headers.get("origin")
        fetch_site = request.headers.get("sec-fetch-site", "").strip().lower()
        if origin and origin.strip().rstrip("/") not in ALLOWED_ORIGINS:
            return _apply_security_headers(
                JSONResponse(status_code=403, content={"detail": "Cross-origin request rejected."}),
                request.url.path,
            )
        if not origin and fetch_site in {"cross-site", "same-site"}:
            return _apply_security_headers(
                JSONResponse(status_code=403, content={"detail": "Cross-origin request rejected."}),
                request.url.path,
            )
    if request.url.path == "/api/v1/analyses" and request.method == "POST":
        content_length = request.headers.get("content-length")
        max_allowed_payload = max(MAX_UPLOAD_BYTES, MAX_VIDEO_BYTES) + 1024 * 1024
        if (
            content_length
            and content_length.isdecimal()
            and int(content_length) > max_allowed_payload
        ):
            return _apply_security_headers(
                JSONResponse(
                    status_code=413, content={"detail": "The uploaded request is too large."}
                ),
                request.url.path,
            )
    remote = _client_ip(request)
    for scope, limit, window_seconds in _request_limits(request):
        identity = remote
        if scope == "upload-session":
            session_cookie = request.cookies.get(COOKIE_NAME)
            if not session_cookie:
                continue
            identity = hashlib.sha256(session_cookie.encode("utf-8")).hexdigest()
        elif scope == "upload-owner":
            session_cookie = request.cookies.get(COOKIE_NAME)
            guest_cookie = request.cookies.get(GUEST_COOKIE_NAME)
            if session_cookie:
                identity = hashlib.sha256(session_cookie.encode("utf-8")).hexdigest()
            elif guest_cookie:
                identity = hashlib.sha256(guest_cookie.encode("utf-8")).hexdigest()
            else:
                identity = remote
        count, resets_at = _consume_rate_limit(f"{scope}:{identity}", limit, window_seconds)
        if count > limit:
            retry_after = max(1, resets_at - int(datetime.now(timezone.utc).timestamp()))
            return _apply_security_headers(
                JSONResponse(
                    status_code=429,
                    content={
                        "code": "RATE_LIMITED",
                        "message": "Too many requests. Wait before trying again.",
                    },
                    headers={"Retry-After": str(retry_after), "Cache-Control": "no-store"},
                ),
                request.url.path,
            )
    return _apply_security_headers(await call_next(request), request.url.path)


# Exact origins, credentialed cookies, and the minimum methods/headers used by this app.
# Keep CORS outermost so preflight requests are handled before authenticated routes.
app.add_middleware(RequestBodySizeLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(ALLOWED_ORIGINS),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Idempotency-Key"],
    max_age=600,
)


@app.get("/health/live", response_model=HealthOut)
def live():
    return {"status": "ok"}


@app.get("/healthz", response_model=HealthOut)
def healthz():
    return {"status": "ok"}


@app.get("/health/ready", response_model=HealthOut)
def ready(db: Session = Depends(get_db)):
    try:
        db.execute(select(1))
        if not STORAGE_DIR.is_dir() or not os.access(STORAGE_DIR, os.W_OK):
            raise OSError("Storage is not writable")
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Required service unavailable") from exc
    return {"status": "ready", "database": "ready", "storage": "ready"}


@app.get("/readyz")
def readyz(db: Session = Depends(get_db)):
    try:
        db.execute(select(1))
        if not STORAGE_DIR.is_dir() or not os.access(STORAGE_DIR, os.W_OK):
            raise OSError("Storage is not writable")
        from app.model_loader import registry

        model_status = registry.healthcheck()
        return {"status": "ready", "database": "ready", "storage": "ready", "models": model_status}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Required service unavailable") from exc


public_api = APIRouter(prefix="/api/v1")


@public_api.get("/config")
def public_config(db: Session = Depends(get_db)):
    detector_health = synthetic_detector.healthcheck()
    # Layer 2 temporal detector health
    temporal_status = {"status": "unavailable", "model_id": "Naman712/Deep-fake-detection"}
    try:
        from app.temporal_detector import create_temporal_detector

        temporal = create_temporal_detector()
        temporal_status = temporal.healthcheck()
    except Exception as exc:
        logger.debug("Temporal healthcheck ignored: %s", exc)
    return {
        "max_upload_bytes": MAX_UPLOAD_BYTES,
        "max_video_bytes": MAX_VIDEO_BYTES,
        "max_video_seconds": MAX_VIDEO_SECONDS,
        "max_image_pixels": MAX_IMAGE_PIXELS,
        "supported_mime_types": list(MEDIA_TYPES.values()),
        "detector": {"status": detector_health["status"], "model_id": detector_health["model_id"]},
        "temporal_detector": {
            "status": temporal_status.get("status", "unavailable"),
            "model_id": temporal_status.get("model_id", "N/A"),
        },
        "audio_detector": {
            "status": "ready",
            "model_id": "Vansh180/deepfake-audio-wav2vec2",
        },
        "analysis_processing": "queued",
        "registration_enabled": _runtime_setting(db, "registration_enabled", True),
        "inspections_enabled": _runtime_setting(db, "inspections_enabled", True),
    }


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    session_hash = token_digest(token)
    _set_rls_session_hash(db, session_hash)
    session_row = db.get(UserSession, session_hash)
    now = utcnow()
    if not session_row or session_row.revoked_at:
        raise HTTPException(status_code=401, detail="Your session has expired. Sign in again.")
    expires_at = session_row.expires_at
    expires_at = (
        expires_at.replace(tzinfo=timezone.utc)
        if expires_at.tzinfo is None
        else expires_at.astimezone(timezone.utc)
    )
    if expires_at <= now:
        raise HTTPException(status_code=401, detail="Your session has expired. Sign in again.")
    _set_rls_principal(db, "user", session_row.user_id)
    user = db.get(User, session_row.user_id)
    if not user or not user.active:
        raise HTTPException(status_code=401, detail="This account is not active.")
    if user.role == "admin":
        _set_rls_principal(db, "admin", user.id)
    return user


def _optional_user(request: Request, db: Session) -> User | None:
    if not request.cookies.get(COOKIE_NAME):
        return None
    try:
        return current_user(request, db)
    except HTTPException as exc:
        if exc.status_code != 401:
            raise
        db.rollback()
        return None


def _resolve_analysis_owner(request: Request, response: Response, db: Session):
    user = _optional_user(request, db)
    raw_ip = _client_ip(request)
    if user:
        return "user", user.id, user, None, _ip_hash(raw_ip), raw_ip
    guest, hashed_ip = _ensure_guest_context(request, response, db)
    return "guest", guest.guest_id, None, guest, hashed_ip, raw_ip


def _ip_restriction_for_owner(
    db: Session, raw_ip: str, user_id: str | None, is_guest: bool
) -> IpBlock | None:
    hashed_ip = _ip_hash(raw_ip)
    if _ip_whitelisted(db, hashed_ip):
        return None
    block = _ip_block_for_hash(db, hashed_ip)
    if not block:
        return None
    if IP_BLOCK_MODE == "hard" or is_guest:
        return block
    linked_ids = _linked_account_ids(db, hashed_ip)
    known = bool(user_id and user_id in linked_ids)
    limit = block.raised_limit if block.raised_limit else MAX_ACCOUNTS_PER_IP
    return None if known or len(linked_ids) < limit else block


@public_api.get("/account/status")
def account_status(request: Request, response: Response, db: Session = Depends(get_db)):
    owner_type, owner_id, user, _guest, _hashed_ip, raw_ip = _resolve_analysis_owner(
        request, response, db
    )
    if user:
        set_auth_rls_principal(db)
    restriction = _ip_restriction_for_owner(db, raw_ip, user.id if user else None, user is None)
    email_verified = True
    requires_email_verification = False
    can_analyze = bool(restriction is None)
    db.commit()
    return {
        "is_authenticated": user is not None,
        "email_verified": email_verified,
        "requires_email_verification": requires_email_verification,
        "can_analyze": can_analyze,
        "access_restricted": bool(restriction),
        "reference_id": restriction.reference_id if restriction else None,
        "contact_email": SUPPORT_CONTACT_EMAIL or None,
    }


private_api = APIRouter(prefix="/api/v1", dependencies=[Depends(current_user)])


def create_session(user: User, response: Response, db: Session) -> None:
    token = secrets.token_urlsafe(40)
    db.add(
        UserSession(
            token_hash=token_digest(token),
            user_id=user.id,
            expires_at=utcnow() + timedelta(hours=SESSION_TTL_HOURS),
        )
    )
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        max_age=SESSION_TTL_HOURS * 3600,
        path="/",
    )


def _append_access_audit(
    db: Session,
    action: str,
    *,
    reason: str | None = None,
    ip_hash: str | None = None,
    reference_id: str | None = None,
    actor_id: str | None = None,
    details: dict | None = None,
    commit: bool = False,
) -> None:
    db.add(
        AccessAuditEvent(
            action=action,
            reason=reason,
            ip_hash=ip_hash,
            reference_id=reference_id,
            actor_id=actor_id,
            details_json=json.dumps(details or {}, separators=(",", ":")),
        )
    )
    if commit:
        db.commit()


def _record_user_activity(
    db: Session,
    actor_id: str | None,
    action: str,
    *,
    subject_id: str | None = None,
    details: dict | None = None,
) -> None:
    db.add(
        UserActivityEvent(
            actor_id=actor_id,
            action=action,
            subject_id=subject_id,
            details_json=json.dumps(details or {}, separators=(",", ":")),
        )
    )


def _lock_ip_hash(db: Session, hashed_ip: str) -> None:
    """Serialize per-IP checks on PostgreSQL and force a SQLite write lock before counting."""
    set_auth_rls_principal(db)
    if engine.dialect.name == "sqlite":
        from sqlalchemy.dialects.sqlite import insert as dialect_insert
    elif engine.dialect.name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as dialect_insert
    else:
        raise RuntimeError("IP abuse controls require SQLite or PostgreSQL.")
    db.execute(
        dialect_insert(IpEnforcementGuard)
        .values(ip_hash=hashed_ip, touch_count=0)
        .on_conflict_do_nothing(index_elements=[IpEnforcementGuard.ip_hash])
    )
    db.execute(
        update(IpEnforcementGuard)
        .where(IpEnforcementGuard.ip_hash == hashed_ip)
        .values(touch_count=IpEnforcementGuard.touch_count + 1)
    )


def _ip_whitelisted(db: Session, hashed_ip: str) -> bool:
    set_auth_rls_principal(db)
    return db.get(IpWhitelist, hashed_ip) is not None


def _ip_block_for_hash(db: Session, hashed_ip: str) -> IpBlock | None:
    set_auth_rls_principal(db)
    return db.scalar(
        select(IpBlock)
        .where(IpBlock.ip_hash == hashed_ip, IpBlock.status == "blocked")
        .order_by(IpBlock.created_at.desc())
        .limit(1)
    )


def _linked_account_ids(db: Session, hashed_ip: str) -> list[str]:
    query = select(IpAccountLink.user_id).where(IpAccountLink.ip_hash == hashed_ip)
    if IP_ACCOUNT_WINDOW_DAYS > 0:
        cutoff = utcnow() - timedelta(days=IP_ACCOUNT_WINDOW_DAYS)
        query = query.where(IpAccountLink.last_seen_at >= cutoff)
    return sorted(set(db.scalars(query).all()))


def _effective_account_limit(
    db: Session, hashed_ip: str, active_block: IpBlock | None = None
) -> int:
    if active_block and active_block.raised_limit:
        return active_block.raised_limit
    if active_block is None:
        # An approved unblock grants one additional account slot. A later
        # over-limit attempt creates a fresh block and returns to the default.
        resolved = db.scalar(
            select(IpBlock)
            .where(
                IpBlock.ip_hash == hashed_ip,
                IpBlock.status == "unblocked",
                IpBlock.raised_limit.is_not(None),
            )
            .order_by(IpBlock.updated_at.desc())
            .limit(1)
        )
        if resolved and resolved.raised_limit:
            return resolved.raised_limit
    return MAX_ACCOUNTS_PER_IP


def _create_ip_block(db: Session, hashed_ip: str, linked_ids: list[str]) -> IpBlock:
    active = _ip_block_for_hash(db, hashed_ip)
    if active:
        return active
    block = IpBlock(
        ip_hash=hashed_ip,
        reference_id=f"CGS-BLK-{secrets.token_hex(3).upper()}",
        reason="ACCOUNT_LIMIT_EXCEEDED",
        linked_account_ids_json=json.dumps(linked_ids),
    )
    db.add(block)
    db.flush()
    _append_access_audit(
        db,
        "ip.account_limit_blocked",
        reason=block.reason,
        ip_hash=hashed_ip,
        reference_id=block.reference_id,
        details={"linked_account_count": len(linked_ids), "mode": IP_BLOCK_MODE},
    )
    return block


def _raise_ip_limit(block: IpBlock) -> None:
    raise APIProblem(
        403,
        "IP_ACCOUNT_LIMIT",
        "Too many accounts were used from this network.",
        reference_id=block.reference_id,
        contact_email=SUPPORT_CONTACT_EMAIL or None,
    )


def _check_ip_account_access(
    db: Session,
    ip_value: str,
    *,
    user_id: str | None = None,
    new_account: bool = False,
    guest: bool = False,
) -> str:
    hashed_ip = _ip_hash(ip_value)
    _lock_ip_hash(db, hashed_ip)
    if _ip_whitelisted(db, hashed_ip):
        return hashed_ip

    linked_ids = _linked_account_ids(db, hashed_ip)
    known_account = bool(user_id and user_id in linked_ids)
    active_block = _ip_block_for_hash(db, hashed_ip)
    limit = _effective_account_limit(db, hashed_ip, active_block)
    over_limit = len(linked_ids) >= limit
    denied = False
    if active_block and IP_BLOCK_MODE == "hard":
        denied = True
    elif active_block and IP_BLOCK_MODE == "soft":
        denied = guest or (not known_account and over_limit)
    elif new_account or (user_id and not known_account) or guest:
        denied = over_limit

    if denied:
        block = active_block or _create_ip_block(db, hashed_ip, linked_ids)
        _append_access_audit(
            db,
            "ip.access_denied",
            reason=block.reason,
            ip_hash=hashed_ip,
            reference_id=block.reference_id,
            actor_id=user_id,
            details={"mode": IP_BLOCK_MODE, "account_count": len(linked_ids)},
        )
        db.commit()
        _raise_ip_limit(block)

    if user_id:
        set_auth_rls_principal(db)
        link = db.scalar(
            select(IpAccountLink).where(
                IpAccountLink.ip_hash == hashed_ip, IpAccountLink.user_id == user_id
            )
        )
        if link:
            link.last_seen_at = utcnow()
        else:
            db.add(IpAccountLink(ip_hash=hashed_ip, user_id=user_id))
    return hashed_ip


def _ensure_guest_context(
    request: Request, response: Response, db: Session
) -> tuple[GuestSession, str]:
    raw_ip = _client_ip(request)
    hashed_ip = _ip_hash(raw_ip)
    signed_cookie = request.cookies.get(GUEST_COOKIE_NAME)
    guest_id = _verify_guest_cookie(signed_cookie)
    guest = None
    if guest_id:
        _set_guest_rls_principal(db, guest_id)
        guest = db.get(GuestSession, guest_id)
    if not guest:
        if signed_cookie and not guest_id:
            set_auth_rls_principal(db)
            _append_access_audit(
                db, "guest.cookie_rejected", reason="tampered_cookie", ip_hash=hashed_ip
            )
        guest_id = secrets.token_urlsafe(32)
        _set_guest_rls_principal(db, guest_id)
        guest = GuestSession(guest_id=guest_id)
        db.add(guest)
        db.flush()
        response.set_cookie(
            GUEST_COOKIE_NAME,
            _guest_cookie_value(guest_id),
            httponly=True,
            secure=COOKIE_SECURE,
            samesite="lax",
            max_age=GUEST_COOKIE_TTL_DAYS * 86400,
            path="/",
        )
    else:
        _set_guest_rls_principal(db, guest.guest_id)
        guest.last_seen_at = utcnow()
    return guest, hashed_ip


def _send_account_email(address: str, subject: str, body: str) -> bool:
    if not SMTP_HOST or not SMTP_FROM_EMAIL:
        if APP_ENV == "production":
            logger.error("Account email unavailable: SMTP is not configured.")
            return False
        # Local QA can copy the one-time URL from the private service log. The authenticated
        # admin invitation endpoint may also provide a one-time fallback link to its creator.
        logger.warning("Account email for %s: %s\n%s", address, subject, body)
        return False
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = SMTP_FROM_EMAIL
    message["To"] = address
    message.set_content(body)
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            if SMTP_STARTTLS:
                server.starttls()
            if SMTP_USERNAME:
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
            refused = server.send_message(message)
        return address.casefold() not in {recipient.casefold() for recipient in refused}
    except Exception:
        # The account/token is already committed. Keep signup/resend usable;
        # the user can retry delivery instead of seeing a false signup failure.
        logger.exception("Unable to deliver an account email to %s", address)
        return False


# ── Reserved admin identities that CANNOT be claimed through public signup ──
_RESERVED_ADMIN_USERNAMES: frozenset[str] = frozenset(
    {"master", "admin", "administrator", "root", "superadmin"}
)


@public_api.post("/auth/signup", response_model=UserOut, status_code=201)
def signup(
    payload: SignupPayload, request: Request, response: Response, db: Session = Depends(get_db)
):
    if not _runtime_setting(db, "registration_enabled", True):
        raise APIProblem(
            403, "REGISTRATION_PAUSED", "New account registration is temporarily paused."
        )
    email = _normalized_email(str(payload.email))
    identity = _email_identity(email)
    if _email_domain(email) in DISPOSABLE_EMAIL_DOMAINS:
        raise HTTPException(
            status_code=400, detail="Please register with a non-disposable email address."
        )
    # ── Block reserved usernames ──
    if payload.username.lower() in _RESERVED_ADMIN_USERNAMES:
        raise HTTPException(
            status_code=409,
            detail="That username is not available. Please choose another.",
        )
    _enforce_auth_identity_limit("signup", identity)
    _enforce_auth_identity_limit("signup-username", payload.username)
    set_auth_rls_principal(db)
    if db.scalar(
        select(User).where(
            (User.email_identity == identity)
            | (User.email == email)
            | (User.username == payload.username)
        )
    ):
        raise HTTPException(
            status_code=409,
            detail="That email or username may already be registered. Sign in or choose another.",
        )
    raw_ip = _client_ip(request)
    _check_ip_account_access(db, raw_ip, new_account=True)
    guest, _guest_ip = _ensure_guest_context(request, response, db)
    set_auth_rls_principal(db)
    user = User(
        email=email,
        email_identity=identity,
        display_name=payload.display_name,
        username=payload.username,
        phone_number=payload.phone_number,
        password_hash=PASSWORDS.hash(payload.password),
        signup_method="email_password",
        signup_ip=raw_ip,
        email_verified_at=utcnow(),
        email_verification_token_hash=None,
        email_verification_expires_at=None,
        role="user",
    )
    db.add(user)
    try:
        db.flush()
        set_auth_rls_principal(db)
        db.add(IpAccountLink(ip_hash=_ip_hash(raw_ip), user_id=user.id))
        guest.linked_user_id = user.id
        _set_rls_principal(db, "user", user.id)
        db.execute(
            update(Analysis)
            .where(Analysis.guest_id == guest.guest_id)
            .values(owner_id=user.id, guest_id=None)
        )
        _set_rls_principal(db, "user", user.id)
        _record_user_activity(
            db, user.id, "account.created", details={"signup_method": user.signup_method}
        )
        # User logs in themselves; no auto-session on signup
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="That email or username may already be registered. Sign in or choose another.",
        ) from exc
    return user


@public_api.post("/auth/admin-invite", response_model=UserOut, status_code=201)
def accept_admin_invitation(
    payload: AdminInviteAcceptPayload,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    token_hash = token_digest(payload.token)
    set_auth_rls_principal(db)
    if engine.dialect.name == "postgresql":
        db.connection().execute(
            text("SELECT set_config('cgs.admin_invite_hash', :token_hash, true)"),
            {"token_hash": token_hash},
        ).close()
    invitation = db.scalar(
        select(AdminInvitation)
        .where(
            AdminInvitation.token_hash == token_hash,
            AdminInvitation.expires_at > utcnow(),
            AdminInvitation.accepted_at.is_(None),
            AdminInvitation.canceled_at.is_(None),
        )
        .with_for_update()
    )
    if not invitation:
        raise HTTPException(
            status_code=400,
            detail="This administrator invitation is invalid, expired, or already used.",
        )
    email = _normalized_email(invitation.email)
    identity = _email_identity(email)
    if db.scalar(
        select(User.id).where(
            (User.email_identity == identity)
            | (User.email == email)
            | (User.username == payload.username)
        )
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "That email or username is already in use. Contact an administrator for "
                "a new invitation."
            ),
        )

    raw_ip = _client_ip(request)
    user = User(
        email=email,
        email_identity=identity,
        display_name=payload.display_name,
        username=payload.username,
        phone_number=payload.phone_number,
        password_hash=PASSWORDS.hash(payload.password),
        email_verified_at=utcnow(),
        role="admin",
        active=True,
        signup_method="admin_invite",
        signup_ip=raw_ip,
    )
    db.add(user)
    db.flush()
    invitation.accepted_at = utcnow()
    _set_rls_principal(db, "admin", user.id)
    _record_user_activity(
        db,
        user.id,
        "account.admin_invitation_accepted",
        details={"invited_by": invitation.invited_by},
    )
    db.add(
        AuditEvent(
            actor_id=user.id,
            action="admin.invitation.accepted",
            subject_id=user.id,
            details_json=json.dumps({"invited_by": invitation.invited_by}),
        )
    )
    create_session(user, response, db)
    db.commit()
    return user


@public_api.post("/auth/login", response_model=UserOut)
def login(
    payload: LoginPayload, request: Request, response: Response, db: Session = Depends(get_db)
):
    raw_ident = str(payload.email).strip()
    if "@" in raw_ident:
        ident = _normalized_email(raw_ident)
        identity = _email_identity(ident)
        _enforce_auth_identity_limit("login", identity)
        set_auth_rls_principal(db)
        user = db.scalar(
            select(User).where((User.email_identity == identity) | (User.email == ident))
        )
    else:
        ident = raw_ident.casefold()
        _enforce_auth_identity_limit("login-username", ident)
        set_auth_rls_principal(db)
        user = db.scalar(select(User).where(func.lower(User.username) == ident))
    try:
        valid = PASSWORDS.verify(
            user.password_hash if user else DUMMY_PASSWORD_HASH, payload.password
        )
    except VerificationError:
        valid = False
    if not valid or not user or not user.active:
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    if IP_BLOCK_MODE == "hard":
        hashed_ip = _ip_hash(_client_ip(request))
        block = _ip_block_for_hash(db, hashed_ip)
        if block:
            _append_access_audit(
                db,
                "ip.login_denied",
                reason=block.reason,
                ip_hash=hashed_ip,
                reference_id=block.reference_id,
                actor_id=user.id,
                commit=True,
            )
            _raise_ip_limit(block)
    _check_ip_account_access(db, _client_ip(request), user_id=user.id)
    if PASSWORDS.check_needs_rehash(user.password_hash):
        user.password_hash = PASSWORDS.hash(payload.password)
    _set_rls_principal(db, "admin" if user.role == "admin" else "user", user.id)
    create_session(user, response, db)
    _record_user_activity(db, user.id, "account.login", details={"method": "email_password"})
    if user.role == "admin":
        db.add(AuditEvent(actor_id=user.id, action="admin.login", subject_id=user.id))
    db.commit()
    return user


@private_api.post("/auth/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        session_row = db.get(UserSession, token_digest(token))
        if session_row and session_row.user_id == user.id:
            session_row.revoked_at = utcnow()
            _record_user_activity(db, user.id, "account.logout")
            if user.role == "admin":
                db.add(AuditEvent(actor_id=user.id, action="admin.logout", subject_id=user.id))
            db.commit()
    response.delete_cookie(
        COOKIE_NAME, path="/", httponly=True, secure=COOKIE_SECURE, samesite="lax"
    )
    response.status_code = 204
    return response


@private_api.get("/auth/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@public_api.post("/auth/verify-email")
def verify_email(payload: VerifyEmailPayload, db: Session = Depends(get_db)):
    set_auth_rls_principal(db)
    user = db.scalar(
        select(User).where(User.email_verification_token_hash == token_digest(payload.token))
    )
    now = utcnow()
    if (
        not user
        or not user.email_verification_expires_at
        or _as_utc(user.email_verification_expires_at) < now
    ):
        raise HTTPException(
            status_code=400, detail="This email verification link is invalid or expired."
        )
    if user.email_verified_at:
        return {"verified": True}
    user.email_verified_at = now
    user.email_verification_token_hash = None
    user.email_verification_expires_at = None
    _set_rls_principal(db, "admin" if user.role == "admin" else "user", user.id)
    _record_user_activity(db, user.id, "account.email_verified")
    db.commit()
    return {"verified": True}


@private_api.post("/auth/resend-verification", status_code=202)
def resend_verification(
    payload: ReturnToPayload | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if user.email_verified_at:
        return {"sent": True}
    token = secrets.token_urlsafe(36)
    user.email_verification_token_hash = token_digest(token)
    user.email_verification_expires_at = utcnow() + timedelta(hours=EMAIL_VERIFICATION_TTL_HOURS)
    db.commit()
    return_suffix = (
        f"&next={quote(payload.return_to, safe='')}" if payload and payload.return_to else ""
    )
    verify_url = f"{PUBLIC_APP_ORIGIN}/verify-email?token={token}{return_suffix}"
    _send_account_email(
        user.email,
        "Verify your CGS DeepFake Shield account",
        f"Open this one-time link to verify your email:\n\n{verify_url}\n\n"
        f"The link expires in {EMAIL_VERIFICATION_TTL_HOURS} hours.",
    )
    return {"sent": True}


@public_api.post("/auth/forgot-password", status_code=202)
def forgot_password(payload: ForgotPasswordPayload, db: Session = Depends(get_db)):
    set_auth_rls_principal(db)
    identity = _email_identity(str(payload.email))
    user = db.scalar(select(User).where(User.email_identity == identity))
    if user and user.active:
        token = secrets.token_urlsafe(36)
        user.password_reset_token_hash = token_digest(token)
        user.password_reset_expires_at = utcnow() + timedelta(hours=PASSWORD_RESET_TTL_HOURS)
        db.commit()
        return_suffix = f"&next={quote(payload.return_to, safe='')}" if payload.return_to else ""
        reset_url = f"{PUBLIC_APP_ORIGIN}/reset-password?token={token}{return_suffix}"
        _send_account_email(
            user.email,
            "Reset your CGS DeepFake Shield password",
            f"Open this one-time link to reset your password:\n\n{reset_url}\n\n"
            f"The link expires in {PASSWORD_RESET_TTL_HOURS} hour(s).",
        )
    return {
        "sent": True,
        "message": "If the account exists, password reset instructions have been sent.",
    }


@public_api.post("/auth/reset-password")
def reset_password(payload: ResetPasswordPayload, db: Session = Depends(get_db)):
    set_auth_rls_principal(db)
    user = db.scalar(
        select(User).where(User.password_reset_token_hash == token_digest(payload.token))
    )
    if (
        not user
        or not user.password_reset_expires_at
        or _as_utc(user.password_reset_expires_at) < utcnow()
    ):
        raise HTTPException(
            status_code=400, detail="This password reset link is invalid or expired."
        )
    user.password_hash = PASSWORDS.hash(payload.password)
    user.password_reset_token_hash = None
    user.password_reset_expires_at = None
    sessions = db.scalars(
        select(UserSession).where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
    ).all()
    for session_row in sessions:
        session_row.revoked_at = utcnow()
    _set_rls_principal(db, "admin" if user.role == "admin" else "user", user.id)
    _record_user_activity(
        db, user.id, "account.password_reset", details={"sessions_revoked": len(sessions)}
    )
    if user.role == "admin":
        db.add(
            AuditEvent(
                actor_id=user.id,
                action="admin.password_reset",
                subject_id=user.id,
                details_json=json.dumps({"sessions_revoked": len(sessions)}),
            )
        )
    db.commit()
    return {"reset": True}


def serialize_analysis(row: Analysis, *, include_image: bool = True) -> dict:
    created_at = (
        row.created_at if row.created_at.tzinfo else row.created_at.replace(tzinfo=timezone.utc)
    )
    completed_at = row.completed_at
    if completed_at and completed_at.tzinfo is None:
        completed_at = completed_at.replace(tzinfo=timezone.utc)
    synthetic_result = json.loads(row.detector_result_json)
    provenance = json.loads(row.provenance_json or "{}")
    is_video_asset = bool(row.detected_mime_type and row.detected_mime_type.startswith("video/"))
    is_audio_asset = bool(row.detected_mime_type and row.detected_mime_type.startswith("audio/"))
    legacy_provenance_only = (
        synthetic_result.get("provider") == "c2pa_hardware_cryptographic_trust"
        or synthetic_result.get("label") == "authentic_hardware_provenance"
    )
    if provenance.get("is_hardware_authenticated"):
        provenance["is_hardware_authenticated"] = False
        provenance["hardware_signer"] = None
    if legacy_provenance_only:
        synthetic_result = {
            "status": "not_configured",
            "limitations": [
                (
                    "This legacy report did not run the AI screening model. Reanalyze the asset "
                    "for an independent screening result."
                )
            ],
        }

    verdict = synthetic_result.get("verdict")
    score = synthetic_result.get("score")

    if row.status == "failed":
        classification = "inconclusive"
        summary_explanation = (
            "Something went wrong after the worker retries. Please try again later."
        )
    elif row.status in {"queued", "processing"}:
        classification = "inconclusive"
        summary_explanation = (
            "The report is queued for analysis. This page updates when the worker finishes."
        )
    elif verdict:
        if verdict == "likely_manipulated":
            classification = "likely_ai_generated"
            summary_explanation = (
                "Multi-model ensemble analysis detected synthetic manipulation patterns. "
                "This is automated probabilistic screening, not legal proof."
            )
        elif verdict == "likely_authentic":
            classification = "likely_authentic"
            summary_explanation = (
                "Multi-model ensemble analysis did not detect strong synthetic patterns. "
                "This does not establish that the media has never been edited or modified."
            )
        else:
            classification = "inconclusive"
            summary_explanation = (
                "Forensic analysis was inconclusive. Detectors produced divergent signals or "
                "fell within the ambiguity band."
            )
    elif synthetic_result.get("label") == "ai_generated_signal":
        classification = "likely_ai_generated"
        if is_video_asset:
            summary_explanation = (
                "The video forensic pipeline detected synthetic manipulation artifacts "
                "across keyframes."
            )
        else:
            summary_explanation = (
                "The configured image models crossed screening thresholds for an "
                "AI-generated signal. This is a probabilistic model finding, not proof."
            )
    elif synthetic_result.get("status") == "completed":
        classification = "inconclusive"
        if is_video_asset:
            summary_explanation = (
                "The video forensic pipeline did not detect significant synthetic "
                "manipulation signatures."
            )
        else:
            summary_explanation = (
                "The models did not cross AI-generated screening thresholds. "
                "This does not establish that the media is authentic or unedited."
            )
    else:
        classification = "inconclusive"
        summary_explanation = (
            "The model did not produce a usable finding. "
            "File integrity and provenance checks are reported separately."
        )
    if synthetic_result.get("cached_from_digest"):
        summary_explanation += " (Instantly verified via cryptographic SHA-256 ledger match)."
    if synthetic_result.get("status") == "not_configured":
        summary_explanation = (
            "The local AI detector is not available. File integrity and "
            "provenance facts do not establish whether media is AI-generated or authentic."
        )
    warnings = [
        (
            "This report provides technical indicators, not proof of who created the media or "
            "whether depicted events are true."
        )
    ]
    warnings.extend(synthetic_result.get("limitations", []))
    warnings.extend(synthetic_result.get("warnings", []))
    detector_task = (
        "video_deepfake_temporal_detection"
        if is_video_asset
        else ("audio_deepfake_detection" if is_audio_asset else "synthetic_image_detection")
    )
    return {
        "analysis_id": row.id,
        "job_id": row.id,
        "media_type": "video" if is_video_asset else ("audio" if is_audio_asset else "image"),
        "verdict": verdict
        or ("likely_manipulated" if classification == "likely_ai_generated" else classification),
        "confidence_band": synthetic_result.get("confidence_band", "medium"),
        "score": score if score is not None else 0.5,
        "models": synthetic_result.get("models", []),
        "audio": synthetic_result.get("audio"),
        "frames_analyzed": synthetic_result.get("frames_analyzed", 0),
        "status": row.status,
        "created_at": created_at,
        "completed_at": completed_at,
        "file": {
            "original_filename": row.original_filename,
            "detected_mime_type": row.detected_mime_type,
            "size_bytes": row.size_bytes,
            "width": row.width,
            "height": row.height,
            "sha256": row.sha256,
            "image_url": f"/api/v1/analyses/{row.id}/image" if include_image else None,
            "media_url": f"/api/v1/analyses/{row.id}/original" if include_image else None,
            "is_video": is_video_asset,
            "is_audio": is_audio_asset,
        },
        "summary": {
            "classification": classification,
            "confidence_kind": "ensemble_calibrated"
            if verdict
            else (
                "calibrated_screening_score"
                if synthetic_result.get("status") == "completed"
                else "none"
            ),
            "confidence_value": score if score is not None else synthetic_result.get("score"),
            "explanation": summary_explanation,
        },
        "detectors": [
            {"task": detector_task, **synthetic_result},
            {
                "task": "manipulation_detection",
                "status": "not_configured",
                "provider": None,
                "limitations": [
                    "No separate, validated manipulation-localization detector is configured."
                ],
            },
            {
                "task": "face_manipulation_detection",
                "status": "not_configured",
                "provider": None,
                "limitations": [
                    (
                        "No face-manipulation detector is configured; face presence is not "
                        "evidence of face swapping."
                    )
                ],
            },
        ],
        "provenance": provenance
        or {
            "status": "queued",
            "details": ["Content Credentials verification runs with the analysis worker."],
        },
        "technical_integrity": json.loads(row.metadata_json),
        "warnings": warnings,
        "disclaimer": "Automated analysis. Not proof. Results can be wrong.",
        "report": {"available": True, "format": "print"},
    }


def _safe_filename(name: str) -> str:
    normalized = unicodedata.normalize("NFKC", unquote(name)).replace("\\", "/").split("/")[-1]
    bidi_controls = {"LRE", "RLE", "LRO", "RLO", "PDF", "LRI", "RLI", "FSI", "PDI"}
    cleaned = "".join(
        ch
        for ch in normalized
        if ch.isprintable()
        and unicodedata.category(ch) not in {"Cc", "Cs"}
        and unicodedata.bidirectional(ch) not in bidi_controls
    )
    return cleaned[:255] or "uploaded-image"


_STORAGE_KEY_PATTERN = re.compile(r"^[a-f0-9]{32}\.(?:original|jpg)$")


def private_storage_path(key: str) -> Path:
    if not _STORAGE_KEY_PATTERN.fullmatch(key):
        raise ValueError("Invalid private storage key.")
    root = STORAGE_DIR.resolve()
    path = (root / key).resolve()
    if path.parent != root:
        raise ValueError("Storage key escaped the private storage directory.")
    return path


def _write_private_storage(key: str, data: bytes) -> Path:
    path = private_storage_path(key)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stored_file:
            stored_file.write(data)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return path


def _validate_audio(data: bytes, filename: str) -> tuple[str, int, int, dict, bytes]:
    import tempfile

    from app.media_safety import check_audio_magic_bytes, convert_audio_to_pcm_wav

    suffix = Path(filename).suffix.lower()
    fmt = check_audio_magic_bytes(data, suffix)
    if not fmt:
        raise HTTPException(
            status_code=415,
            detail=(
                "Upload a supported audio file (WAV, MP3, FLAC, M4A, OGG). "
                "The audio signature was unrecognized."
            ),
        )
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)
    try:
        pcm_wav = convert_audio_to_pcm_wav(tmp_path, max_duration_seconds=120)
    finally:
        tmp_path.unlink(missing_ok=True)

    technical = {
        "format": fmt,
        "media_type": "audio",
        "is_audio": True,
        "width": 0,
        "height": 0,
        "duration_seconds": round(len(pcm_wav) / (16000 * 2), 2),
        "preview_note": "Audio decoded to 16 kHz mono PCM WAV for forensic analysis.",
        "type_verification": {
            "verified": True,
            "format": fmt,
            "magic_signature": data[:8].hex().upper(),
            "status": "verified",
        },
    }
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), color=(14, 165, 233)).save(buf, format="JPEG")
    return fmt, 0, 0, technical, buf.getvalue()


def _validate_image(data: bytes, filename: str) -> tuple[str, int, int, dict, bytes]:
    from app.media_safety import check_image_magic_bytes

    suffix = Path(filename).suffix.lower()
    expected_format = ALLOWED_EXTENSIONS.get(suffix)
    if not expected_format:
        raise HTTPException(status_code=415, detail="Upload a JPEG, PNG, or WebP image.")
    magic_format = check_image_magic_bytes(data)
    if not magic_format:
        raise HTTPException(
            status_code=415,
            detail="Upload a supported JPEG, PNG, or WebP image. The image signature was unrecognized.",
        )
    if magic_format != expected_format:
        raise HTTPException(
            status_code=415,
            detail="The file extension does not match the image format.",
        )
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                detected_format = image.format
                if detected_format != expected_format:
                    raise HTTPException(
                        status_code=415,
                        detail="The file extension does not match the image format.",
                    )
                image.verify()
            with Image.open(io.BytesIO(data)) as image:
                width, height = image.size
                if width < 1 or height < 1 or width * height > MAX_IMAGE_PIXELS:
                    raise HTTPException(
                        status_code=413, detail="The image dimensions exceed the supported limit."
                    )
                if getattr(image, "n_frames", 1) > 1:
                    raise HTTPException(
                        status_code=415,
                        detail="Animated images are not supported; upload a still image.",
                    )
                exif = image.getexif()
                exif_present = bool(exif)
                from PIL.ExifTags import TAGS

                exif_fields = sorted({TAGS.get(tag, f"tag_{tag}") for tag in exif.keys()})[:80]
                icc_present = bool(image.info.get("icc_profile"))
                oriented = ImageOps.exif_transpose(image).convert("RGB")
                oriented.thumbnail((1200, 1200))
                output = io.BytesIO()
                oriented.save(output, format="JPEG", quality=88, optimize=True)
                preview = output.getvalue()
    except HTTPException:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise HTTPException(
            status_code=413, detail="The image dimensions exceed the supported limit."
        ) from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(
            status_code=415, detail="The image could not be safely decoded."
        ) from exc
    return (
        detected_format,
        width,
        height,
        {
            "format": detected_format,
            "width": width,
            "height": height,
            "frame_count": 1,
            "exif_present": exif_present,
            "exif_fields": exif_fields,
            "icc_profile_present": icc_present,
            "metadata_field_count": len(exif_fields) + int(icc_present),
            "pixel_limit": MAX_IMAGE_PIXELS,
            "type_verification": {
                "verified": True,
                "format": detected_format,
                "magic_signature": data[:8].hex().upper(),
                "status": "verified",
            },
            "preview_note": (
                "A normalized preview was created for display; it is not used "
                "as authenticity evidence."
            ),
        },
        preview,
    )


def _owned_analysis(analysis_id: str, owner_type: str, owner_id: str, db: Session) -> Analysis:
    if not re.fullmatch(r"[a-f0-9]{32}", analysis_id):
        raise HTTPException(status_code=404, detail="Analysis not found.")
    owner_filter = (
        Analysis.owner_id == owner_id if owner_type == "user" else Analysis.guest_id == owner_id
    )
    row = db.scalar(select(Analysis).where(Analysis.id == analysis_id, owner_filter))
    if not row:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return row


def _analysis_idempotency_key(owner_type: str, owner_id: str, client_key: str) -> str:
    raw = f"{owner_type}:{owner_id}:{client_key}".encode()
    return hashlib.sha256(raw).hexdigest()


def _find_idempotent_analysis(
    db: Session, owner_type: str, owner_id: str, client_key: str
) -> Analysis | None:
    owner_filter = (
        Analysis.owner_id == owner_id if owner_type == "user" else Analysis.guest_id == owner_id
    )
    idempotency_keys = {_analysis_idempotency_key(owner_type, owner_id, client_key), client_key}
    return db.scalar(
        select(Analysis).where(owner_filter, Analysis.idempotency_key.in_(idempotency_keys))
    )


@public_api.post("/analyses", status_code=201)
async def create_analysis(
    request: Request,
    response: Response,
    file: Annotated[UploadFile, File()],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    db: Session = Depends(get_db),
):
    owner_type, owner_id, user, guest, _hashed_ip, raw_ip = _resolve_analysis_owner(
        request, response, db
    )

    if idempotency_key is not None and not re.fullmatch(r"[A-Za-z0-9_-]{16,64}", idempotency_key):
        raise APIProblem(
            400, "INVALID_REQUEST", "The Idempotency-Key must be 16–64 URL-safe characters."
        )
    idempotency_key = idempotency_key or secrets.token_urlsafe(24)
    previous = _find_idempotent_analysis(db, owner_type, owner_id, idempotency_key)
    if previous:
        response.status_code = 200
        return serialize_analysis(previous)

    if not _runtime_setting(db, "inspections_enabled", True):
        raise APIProblem(
            503,
            "INSPECTIONS_PAUSED",
            "New inspections are temporarily paused. Please try again later.",
        )
    if user:
        _check_ip_account_access(db, raw_ip, user_id=user.id)
        _set_rls_principal(db, "user", user.id)
    else:
        _check_ip_account_access(db, raw_ip, guest=True)
        _set_guest_rls_principal(db, owner_id)

    suffix = Path(file.filename or "").suffix.lower()
    is_video = suffix in {".mp4", ".webm", ".mov", ".avi", ".mkv"}
    is_audio = suffix in {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac"}
    max_limit = MAX_VIDEO_BYTES if is_video else MAX_UPLOAD_BYTES

    data = await file.read(max_limit + 1)
    if len(data) > max_limit:
        limit_label = (
            f"{max_limit // (1024 * 1024)} MB" if max_limit >= 1024 * 1024 else f"{max_limit} bytes"
        )
        raise APIProblem(400, "INVALID_FILE", f"File exceeds the {limit_label} limit.")

    filename = _safe_filename(
        file.filename
        or ("uploaded-video" if is_video else ("uploaded-audio" if is_audio else "uploaded-image"))
    )

    try:
        if is_video:
            from app.video import validate_video

            detected_format, width, height, technical, preview = validate_video(
                data, filename, max_limit, MAX_VIDEO_SECONDS
            )
        elif is_audio:
            detected_format, width, height, technical, preview = _validate_audio(data, filename)
        else:
            detected_format, width, height, technical, preview = _validate_image(data, filename)
    except HTTPException as exc:
        raise APIProblem(400, "INVALID_FILE", str(exc.detail)) from exc

    declared_mime = (file.content_type or "").split(";", 1)[0].strip().lower()
    expected_mime = MEDIA_TYPES.get(detected_format, "application/octet-stream")
    allowed_mimes = {expected_mime, "application/octet-stream"}
    if is_video:
        allowed_mimes.update(
            {"video/mp4", "video/webm", "video/quicktime", "video/x-msvideo", "video/x-matroska"}
        )
    elif is_audio:
        allowed_mimes.update(
            {
                "audio/wav",
                "audio/mpeg",
                "audio/flac",
                "audio/ogg",
                "audio/mp4",
                "audio/aac",
                "audio/x-wav",
            }
        )
    if declared_mime and declared_mime not in allowed_mimes:
        raise APIProblem(
            400, "INVALID_FILE", "The declared content type does not match the file format."
        )

    analysis_id = uuid.uuid4().hex
    object_key = f"{analysis_id}.original"
    preview_key = f"{analysis_id}.jpg"
    stored_paths: list[Path] = []
    try:
        stored_paths.append(_write_private_storage(object_key, data))
        stored_paths.append(_write_private_storage(preview_key, preview))
        row = Analysis(
            id=analysis_id,
            owner_id=user.id if user else None,
            guest_id=guest.guest_id if guest else None,
            idempotency_key=_analysis_idempotency_key(owner_type, owner_id, idempotency_key),
            status="queued",
            original_filename=filename,
            object_key=object_key,
            preview_key=preview_key,
            detected_mime_type=MEDIA_TYPES.get(detected_format, "application/octet-stream"),
            size_bytes=len(data),
            width=width,
            height=height,
            sha256=hashlib.sha256(data).hexdigest(),
            metadata_json=json.dumps(technical),
            detector_result_json=json.dumps(
                {"status": "queued", "limitations": ["Analysis is waiting for a worker."]}
            ),
            provenance_json=json.dumps(
                {"status": "queued", "details": ["Content Credentials verification is queued."]}
            ),
            completed_at=None,
        )
        db.add(row)
        db.add(InferenceJob(analysis_id=analysis_id, status="queued"))
        if user:
            _record_user_activity(
                db,
                user.id,
                "inspection.created",
                subject_id=analysis_id,
                details={
                    "mime_type": MEDIA_TYPES.get(detected_format, "application/octet-stream"),
                    "size_bytes": len(data),
                },
            )
        db.commit()
        db.refresh(row)
    except APIProblem:
        db.rollback()
        for stored_path in stored_paths:
            stored_path.unlink(missing_ok=True)
        raise
    except IntegrityError:
        db.rollback()
        for stored_path in stored_paths:
            stored_path.unlink(missing_ok=True)
        if owner_type == "user":
            _set_rls_principal(db, "user", owner_id)
        else:
            _set_guest_rls_principal(db, owner_id)
        previous = _find_idempotent_analysis(db, owner_type, owner_id, idempotency_key)
        if previous:
            response.status_code = 200
            return serialize_analysis(previous)
        raise HTTPException(
            status_code=409, detail="This analysis request conflicts with an existing request."
        )
    except Exception:
        db.rollback()
        for stored_path in stored_paths:
            stored_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500, detail="The analysis could not be saved. Please try again."
        )
    return serialize_analysis(row)


@public_api.get("/analyses")
@public_api.get("/verifications")
def list_analyses(
    request: Request,
    response: Response,
    page: int = 1,
    page_size: int = 20,
    status_filter: str | None = None,
    q: str | None = None,
    created_from: date | None = None,
    created_to: date | None = None,
    db: Session = Depends(get_db),
):
    owner_type, owner_id, _user, _guest, _ip, _raw = _resolve_analysis_owner(request, response, db)
    page = max(1, page)
    page_size = min(100, max(1, page_size))
    owner_filter = (
        Analysis.owner_id == owner_id if owner_type == "user" else Analysis.guest_id == owner_id
    )
    query = select(Analysis).where(owner_filter)
    if status_filter in {"queued", "processing", "completed", "failed"}:
        query = query.where(Analysis.status == status_filter)
    if q:
        query = query.where(Analysis.id.contains(q.strip()[:32], autoescape=True))
    if created_from:
        query = query.where(
            Analysis.created_at >= datetime.combine(created_from, time.min, tzinfo=timezone.utc)
        )
    if created_to:
        query = query.where(
            Analysis.created_at
            < datetime.combine(created_to + timedelta(days=1), time.min, tzinfo=timezone.utc)
        )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    page = min(1_000_000, page)
    rows = db.scalars(
        query.order_by(Analysis.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    db.commit()
    return {
        "items": [serialize_analysis(row, include_image=False) for row in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@public_api.get("/analyses/{analysis_id}")
@public_api.get("/verifications/{analysis_id}")
def get_analysis(
    analysis_id: str, request: Request, response: Response, db: Session = Depends(get_db)
):
    owner_type, owner_id, _user, _guest, _ip, _raw = _resolve_analysis_owner(request, response, db)
    row = _owned_analysis(analysis_id, owner_type, owner_id, db)
    db.commit()
    return serialize_analysis(row)


@public_api.get("/analyses/{analysis_id}/image")
def get_analysis_image(
    analysis_id: str, request: Request, response: Response, db: Session = Depends(get_db)
):
    owner_type, owner_id, _user, _guest, _ip, _raw = _resolve_analysis_owner(request, response, db)
    row = _owned_analysis(analysis_id, owner_type, owner_id, db)
    try:
        path = private_storage_path(row.preview_key)
    except ValueError as exc:
        logger.error("Invalid stored preview key for analysis %s", row.id)
        raise HTTPException(
            status_code=404, detail="Image preview is no longer available."
        ) from exc
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Image preview is no longer available.")
    return FileResponse(
        path,
        media_type="image/jpeg",
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@public_api.get("/analyses/{analysis_id}/original")
def get_analysis_original(
    analysis_id: str, request: Request, response: Response, db: Session = Depends(get_db)
):
    owner_type, owner_id, _user, _guest, _ip, _raw = _resolve_analysis_owner(request, response, db)
    row = _owned_analysis(analysis_id, owner_type, owner_id, db)
    try:
        path = private_storage_path(row.object_key)
    except ValueError as exc:
        logger.error("Invalid stored object key for analysis %s", row.id)
        raise HTTPException(status_code=404, detail="Media file is no longer available.") from exc
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Media file is no longer available.")
    return FileResponse(
        path,
        media_type=row.detected_mime_type,
        filename=row.original_filename,
        headers={"Cache-Control": "private, max-age=3600", "X-Content-Type-Options": "nosniff"},
    )


@public_api.delete("/analyses/{analysis_id}", status_code=204)
def delete_analysis(
    analysis_id: str, request: Request, response: Response, db: Session = Depends(get_db)
):
    owner_type, owner_id, user, _guest, _ip, _raw = _resolve_analysis_owner(request, response, db)
    row = _owned_analysis(analysis_id, owner_type, owner_id, db)
    keys = (row.object_key, row.preview_key)
    if user:
        _record_user_activity(db, user.id, "inspection.deleted", subject_id=analysis_id)
    db.delete(row)
    db.commit()
    for key in keys:
        try:
            private_storage_path(key).unlink(missing_ok=True)
        except ValueError:
            logger.error("Invalid stored object key while deleting analysis %s", analysis_id)
    return Response(status_code=204)


@private_api.delete("/auth/account", status_code=204)
def delete_account(
    response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    # ── IMMUTABILITY GUARD: Administrator accounts are cryptographically locked ──
    if user.role == "admin" or _normalized_email(user.email) in _admin_emails():
        db.add(
            AuditEvent(
                actor_id=user.id,
                action="admin.account.delete_blocked",
                subject_id=user.id,
                details_json=json.dumps({"reason": "immutable_admin_policy"}),
            )
        )
        db.commit()
        raise HTTPException(
            status_code=403,
            detail=(
                "Administrator accounts are cryptographically locked and strictly cannot "
                "be deleted through the web application."
            ),
        )
    rows = db.scalars(select(Analysis).where(Analysis.owner_id == user.id)).all()
    keys = [key for row in rows for key in (row.object_key, row.preview_key)]
    _record_user_activity(
        db, user.id, "account.deleted", details={"inspections_deleted": len(rows)}
    )
    db.delete(user)
    db.commit()
    for key in keys:
        try:
            private_storage_path(key).unlink(missing_ok=True)
        except ValueError:
            logger.error("Invalid stored object key while deleting account %s", user.id)
    response.delete_cookie(
        COOKIE_NAME, path="/", httponly=True, secure=COOKIE_SECURE, samesite="lax"
    )
    response.status_code = 204
    return response


@private_api.get("/admin/analyses")
def admin_analyses(
    q: str | None = None,
    status_filter: str | None = None,
    page: int = 1,
    page_size: int = 20,
    actor: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if actor.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    _set_rls_principal(db, "admin", actor.id)
    query = select(Analysis, User.email, User.display_name).outerjoin(
        User, Analysis.owner_id == User.id
    )
    if status_filter:
        if status_filter not in {"queued", "processing", "completed", "failed"}:
            raise HTTPException(status_code=422, detail="Choose a supported inspection status.")
        query = query.where(Analysis.status == status_filter)
    term = (q or "").strip()[:120]
    if term:
        query = query.where(
            or_(
                Analysis.id.contains(term, autoescape=True),
                Analysis.original_filename.contains(term, autoescape=True),
                User.email.contains(term, autoescape=True),
            )
        )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    page = min(1_000_000, max(1, page))
    page_size = min(100, max(1, page_size))
    rows = db.execute(
        query.order_by(Analysis.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    items = []
    for row, owner_email, owner_name in rows:
        report = serialize_analysis(row, include_image=False)
        items.append(
            {
                "analysis_id": report["analysis_id"],
                "status": report["status"],
                "created_at": report["created_at"],
                "completed_at": report["completed_at"],
                "file": report["file"],
                "summary": report["summary"],
                "owner_email": owner_email,
                "owner_name": owner_name,
            }
        )
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@private_api.get("/admin/contact-inquiries")
def admin_contact_inquiries(
    q: str | None = None,
    status_filter: str | None = None,
    page: int = 1,
    page_size: int = 50,
    actor: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if actor.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    _set_rls_principal(db, "admin", actor.id)
    query = select(ContactInquiry)
    if status_filter:
        if status_filter not in {"new", "in_progress", "resolved"}:
            raise HTTPException(status_code=422, detail="Choose a supported inquiry status.")
        query = query.where(ContactInquiry.status == status_filter)
    term = (q or "").strip()[:120]
    if term:
        query = query.where(
            or_(
                ContactInquiry.name.contains(term, autoescape=True),
                ContactInquiry.email.contains(term, autoescape=True),
                ContactInquiry.topic.contains(term, autoescape=True),
                ContactInquiry.message.contains(term, autoescape=True),
            )
        )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    page = min(1_000_000, max(1, page))
    page_size = min(100, max(1, page_size))
    rows = db.scalars(
        query.order_by(ContactInquiry.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [
            {
                "id": row.id,
                "name": row.name,
                "email": row.email,
                "topic": row.topic,
                "message": row.message,
                "status": row.status,
                "admin_note": row.admin_note,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
            for row in rows
        ],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@private_api.patch("/admin/contact-inquiries/{inquiry_id}")
def admin_update_contact_inquiry(
    inquiry_id: str,
    payload: AdminContactInquiryUpdate,
    actor: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if actor.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    if payload.status is None and "admin_note" not in payload.model_fields_set:
        raise HTTPException(
            status_code=422, detail="Choose a status or enter an internal note to update."
        )
    _set_rls_principal(db, "admin", actor.id)
    row = db.get(ContactInquiry, inquiry_id)
    if not row:
        raise HTTPException(status_code=404, detail="Contact inquiry not found.")
    changed = {}
    if payload.status is not None:
        row.status = payload.status
        changed["status"] = payload.status
    if "admin_note" in payload.model_fields_set:
        row.admin_note = payload.admin_note
        changed["admin_note_updated"] = True
    row.updated_at = utcnow()
    db.add(
        AuditEvent(
            actor_id=actor.id,
            action="admin.contact_inquiry.updated",
            subject_id=row.id,
            details_json=json.dumps(changed),
        )
    )
    db.commit()
    return {
        "id": row.id,
        "status": row.status,
        "admin_note": row.admin_note,
        "updated_at": row.updated_at,
    }


@private_api.get("/admin/settings")
def admin_get_settings(actor: User = Depends(current_user), db: Session = Depends(get_db)):
    if actor.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    _set_rls_principal(db, "admin", actor.id)
    rows = db.scalars(select(SystemSetting)).all()
    stored = {row.key: row for row in rows}
    defaults = {"registration_enabled": True, "inspections_enabled": True}
    settings = {key: _runtime_setting(db, key, default) for key, default in defaults.items()}
    updated_at = max((stored[key].updated_at for key in defaults if key in stored), default=None)
    return {"settings": settings, "updated_at": updated_at}


@private_api.patch("/admin/settings")
def admin_update_settings(
    payload: AdminSettingsUpdate, actor: User = Depends(current_user), db: Session = Depends(get_db)
):
    if actor.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    changes = {
        key: getattr(payload, key)
        for key in ("registration_enabled", "inspections_enabled")
        if getattr(payload, key) is not None
    }
    if not changes:
        raise HTTPException(status_code=422, detail="Change at least one platform setting.")
    _set_rls_principal(db, "admin", actor.id)
    for key, value in changes.items():
        row = db.get(SystemSetting, key)
        if row is None:
            row = SystemSetting(key=key, value_json=json.dumps(value), updated_by=actor.id)
            db.add(row)
        else:
            row.value_json = json.dumps(value)
            row.updated_by = actor.id
            row.updated_at = utcnow()
    db.add(
        AuditEvent(
            actor_id=actor.id,
            action="admin.platform_settings.updated",
            subject_id="platform",
            details_json=json.dumps(changes),
        )
    )
    db.commit()
    return {
        "settings": {
            key: _runtime_setting(db, key, True)
            for key in ("registration_enabled", "inspections_enabled")
        }
    }


@private_api.post("/admin/security/revoke-other-sessions")
def admin_revoke_other_sessions(
    payload: AdminDangerActionPayload,
    request: Request,
    actor: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if actor.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    _set_rls_principal(db, "admin", actor.id)
    current_token = request.cookies.get(COOKIE_NAME, "")
    if not current_token:
        raise HTTPException(
            status_code=401, detail="Sign in again before changing administrator sessions."
        )
    result = db.execute(
        update(UserSession)
        .where(
            UserSession.user_id == actor.id,
            UserSession.token_hash != token_digest(current_token),
            UserSession.revoked_at.is_(None),
        )
        .values(revoked_at=utcnow())
    )
    revoked = result.rowcount or 0
    db.add(
        AuditEvent(
            actor_id=actor.id,
            action="admin.security.other_sessions_revoked",
            subject_id=actor.id,
            details_json=json.dumps({"revoked_sessions": revoked}),
        )
    )
    db.commit()
    return {"revoked_sessions": revoked}


@private_api.get("/admin/overview")
def admin_overview(user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    _set_rls_principal(db, "admin", user.id)
    counts = dict(db.execute(select(Analysis.status, func.count()).group_by(Analysis.status)).all())
    queue_counts = dict(
        db.execute(select(InferenceJob.status, func.count()).group_by(InferenceJob.status)).all()
    )
    detector = synthetic_detector.healthcheck()
    temporal_health = {"status": "unavailable"}
    try:
        from app.temporal_detector import create_temporal_detector

        temporal_health = create_temporal_detector().healthcheck()
    except Exception as exc:
        logger.debug("Temporal healthcheck ignored: %s", exc)
    worker_cutoff = utcnow() - timedelta(seconds=30)
    active_workers = (
        db.scalar(
            select(func.count())
            .select_from(WorkerHeartbeat)
            .where(WorkerHeartbeat.last_seen >= worker_cutoff)
        )
        or 0
    )
    return {
        "analysis_counts": counts,
        "queue_counts": queue_counts,
        "detector": detector,
        "temporal_detector": temporal_health,
        "active_users": db.scalar(
            select(func.count()).select_from(User).where(User.active.is_(True))
        )
        or 0,
        "total_users": db.scalar(select(func.count()).select_from(User)) or 0,
        "worker": {
            "status": "ready" if active_workers else "offline",
            "active_workers": active_workers,
        },
        "note": "Counts and health status reflect current database and worker records.",
    }


@private_api.get("/admin/users")
def admin_users(
    q: str | None = None,
    page: int = 1,
    page_size: int = 25,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    _set_rls_principal(db, "admin", user.id)
    page = max(1, page)
    page = min(1_000_000, page)
    page_size = min(100, max(1, page_size))
    query = select(User).where(User.role == "user")
    if q and q.strip():
        term = f"%{_escape_like(q.strip()[:120])}%"
        query = query.where(
            User.email.ilike(term, escape="\\")
            | User.display_name.ilike(term, escape="\\")
            | User.username.ilike(term, escape="\\")
            | User.phone_number.ilike(term, escape="\\")
        )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    users = db.scalars(
        query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    analysis_counts = dict(
        db.execute(select(Analysis.owner_id, func.count()).group_by(Analysis.owner_id)).all()
    )
    return {
        "items": [
            {
                "id": row.id,
                "email": row.email,
                "display_name": row.display_name,
                "username": row.username,
                "phone_number": row.phone_number,
                "role": row.role,
                "active": row.active,
                "signup_method": row.signup_method,
                "signup_ip": row.signup_ip,
                "email_verified": row.email_verified_at is not None,
                "created_at": row.created_at,
                "analysis_count": analysis_counts.get(row.id, 0),
            }
            for row in users
        ],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@private_api.patch("/admin/users/{user_id}")
def admin_update_user(
    user_id: str,
    payload: AdminUserUpdate,
    actor: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if actor.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    _set_rls_principal(db, "admin", actor.id)
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="Account not found.")
    if target.role != "user":
        raise HTTPException(
            status_code=409, detail="Use Admin Management to change an administrator account."
        )
    if payload.active is None:
        raise HTTPException(
            status_code=422, detail="Choose whether to ban or restore this account."
        )
    if target.id == actor.id:
        raise HTTPException(status_code=409, detail="You cannot ban your own account.")
    changes: dict[str, object] = (
        {"active": payload.active} if payload.active != target.active else {}
    )
    if changes:
        target.active = payload.active
        if not payload.active:
            sessions = db.scalars(
                select(UserSession).where(
                    UserSession.user_id == target.id, UserSession.revoked_at.is_(None)
                )
            ).all()
            for session in sessions:
                session.revoked_at = utcnow()
    if changes:
        db.add(
            AuditEvent(
                actor_id=actor.id,
                action="admin.user.updated",
                subject_id=target.id,
                details_json=json.dumps(
                    {**changes, "sessions_revoked": len(sessions) if not payload.active else 0}
                ),
            )
        )
        db.commit()
        db.refresh(target)
    return {
        "id": target.id,
        "email": target.email,
        "display_name": target.display_name,
        "role": target.role,
        "active": target.active,
    }


@private_api.delete("/admin/users/{user_id}")
def admin_delete_user(
    user_id: str,
    payload: AdminUserDeletePayload,
    actor: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if actor.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    _set_rls_principal(db, "admin", actor.id)
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="Account not found.")
    if target.role != "user" or target.id == actor.id or _is_protected_admin(target.email):
        raise HTTPException(
            status_code=403, detail="Administrator and protected accounts cannot be deleted here."
        )
    expected = f"DELETE USER {target.email}"
    if payload.confirmation != expected:
        raise HTTPException(
            status_code=422,
            detail=f"Type {expected} exactly to delete this account and its inspection media.",
        )
    analyses = db.scalars(select(Analysis).where(Analysis.owner_id == target.id)).all()
    keys = [key for row in analyses for key in (row.object_key, row.preview_key)]
    db.add(
        AuditEvent(
            actor_id=actor.id,
            action="admin.user.deleted",
            subject_id=target.id,
            details_json=json.dumps({"inspections_deleted": len(analyses)}),
        )
    )
    db.delete(target)
    db.commit()
    for key in keys:
        try:
            private_storage_path(key).unlink(missing_ok=True)
        except ValueError:
            logger.error("Invalid stored object key while deleting user %s", user_id)
    return {"deleted": True, "inspections_deleted": len(analyses)}


@private_api.get("/admin/admins")
def admin_list_admins(
    q: str | None = None, actor: User = Depends(current_user), db: Session = Depends(get_db)
):
    if actor.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    _set_rls_principal(db, "admin", actor.id)
    query = select(User).where(User.role == "admin")
    term = (q or "").strip()[:120]
    if term:
        pattern = f"%{_escape_like(term)}%"
        query = query.where(
            User.email.ilike(pattern, escape="\\")
            | User.display_name.ilike(pattern, escape="\\")
            | User.username.ilike(pattern, escape="\\")
        )
    rows = db.scalars(query.order_by(User.created_at.asc())).all()
    invitation_query = select(AdminInvitation).where(
        AdminInvitation.accepted_at.is_(None),
        AdminInvitation.canceled_at.is_(None),
        AdminInvitation.expires_at > utcnow(),
    )
    if term:
        invitation_query = invitation_query.where(AdminInvitation.email.ilike(pattern, escape="\\"))
    invitations = db.scalars(invitation_query.order_by(AdminInvitation.created_at.desc())).all()
    return {
        "items": [
            {
                "id": row.id,
                "email": row.email,
                "display_name": row.display_name,
                "username": row.username,
                "phone_number": row.phone_number,
                "active": row.active,
                "email_verified": row.email_verified_at is not None,
                "created_at": row.created_at,
                "protected": _is_protected_admin(row.email),
            }
            for row in rows
        ],
        "invitations": [
            {
                "id": row.id,
                "email": row.email,
                "created_at": row.created_at,
                "expires_at": row.expires_at,
            }
            for row in invitations
        ],
    }


@private_api.post("/admin/admins", status_code=201)
def admin_create_admin(
    payload: AdminInvitationCreatePayload,
    actor: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if actor.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    _set_rls_principal(db, "admin", actor.id)
    email = _normalized_email(str(payload.email))
    identity = _email_identity(email)
    existing = db.scalar(
        select(User).where((User.email_identity == identity) | (User.email == email))
    )
    if existing:
        if existing.role == "admin":
            raise HTTPException(status_code=409, detail="This account is already an administrator.")
        if not existing.active or not existing.email_verified_at:
            raise HTTPException(
                status_code=409,
                detail=(
                    "The account must be active and email-verified before it can become "
                    "an administrator."
                ),
            )
        existing.role = "admin"
        sessions = db.scalars(
            select(UserSession).where(
                UserSession.user_id == existing.id, UserSession.revoked_at.is_(None)
            )
        ).all()
        for session in sessions:
            session.revoked_at = utcnow()
        db.add(
            AuditEvent(
                actor_id=actor.id,
                action="admin.user.promoted",
                subject_id=existing.id,
                details_json=json.dumps({"sessions_revoked": len(sessions)}),
            )
        )
        db.commit()
        return {"promoted": True, "id": existing.id, "email": existing.email}

    if _is_protected_admin(email):
        raise HTTPException(
            status_code=409,
            detail="This address is reserved for a configured bootstrap administrator.",
        )
    pending_invitations = db.scalars(
        select(AdminInvitation).where(
            AdminInvitation.accepted_at.is_(None), AdminInvitation.canceled_at.is_(None)
        )
    ).all()
    previous = [
        invitation
        for invitation in pending_invitations
        if _email_identity(invitation.email) == identity
    ]
    now = utcnow()
    for invitation in previous:
        invitation.canceled_at = now
    token = secrets.token_urlsafe(36)
    invitation = AdminInvitation(
        email=email,
        token_hash=token_digest(token),
        invited_by=actor.id,
        created_at=now,
        expires_at=now + timedelta(hours=24),
    )
    db.add(invitation)
    db.flush()
    db.add(
        AuditEvent(
            actor_id=actor.id,
            action="admin.invitation.created",
            subject_id=invitation.id,
            details_json=json.dumps(
                {"email": email, "expires_at": invitation.expires_at.isoformat()}
            ),
        )
    )
    db.commit()
    invite_url = f"{PUBLIC_APP_ORIGIN.rstrip('/')}/admin-invite?token={quote(token, safe='')}"
    email_sent = _send_account_email(
        email,
        "Administrator invitation for CGS DeepFake Shield",
        "An administrator invited you to create a CGS DeepFake Shield administrator account.\n\n"
        f"Open this one-time link within 24 hours:\n\n{invite_url}\n\n"
        "If you were not expecting this invitation, you can ignore this message.",
    )
    return {
        "invited": True,
        "id": invitation.id,
        "email": email,
        "expires_at": invitation.expires_at,
        "email_sent": email_sent,
        # Only return this bearer link to the authenticated admin who just created it,
        # and only when SMTP did not deliver it.
        "invite_url": invite_url if not email_sent else None,
    }


@private_api.delete("/admin/admin-invitations/{invitation_id}")
def admin_cancel_invitation(
    invitation_id: str, actor: User = Depends(current_user), db: Session = Depends(get_db)
):
    if actor.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    _set_rls_principal(db, "admin", actor.id)
    invitation = db.get(AdminInvitation, invitation_id)
    if not invitation or invitation.accepted_at:
        raise HTTPException(status_code=404, detail="Pending invitation not found.")
    invitation.canceled_at = utcnow()
    db.add(
        AuditEvent(
            actor_id=actor.id,
            action="admin.invitation.canceled",
            subject_id=invitation.id,
            details_json=json.dumps({"email": invitation.email}),
        )
    )
    db.commit()
    return {"canceled": True}


@private_api.patch("/admin/admins/{user_id}")
def admin_update_admin(
    user_id: str,
    payload: AdminRoleActionPayload,
    actor: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if actor.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    _set_rls_principal(db, "admin", actor.id)
    target = db.get(User, user_id)
    if not target or target.role != "admin":
        raise HTTPException(status_code=404, detail="Administrator account not found.")
    if target.id == actor.id:
        raise HTTPException(
            status_code=409, detail="You cannot disable or revoke your own administrator access."
        )
    if _is_protected_admin(target.email):
        raise HTTPException(
            status_code=403,
            detail="Configured bootstrap administrators are protected from web changes.",
        )
    if payload.action in {"disable", "revoke"}:
        remaining = (
            db.scalar(
                select(func.count())
                .select_from(User)
                .where(User.role == "admin", User.active.is_(True), User.id != target.id)
            )
            or 0
        )
        if target.active and remaining == 0:
            raise HTTPException(
                status_code=409,
                detail="The last active administrator cannot be disabled or revoked.",
            )
    changes: dict[str, object] = {}
    if payload.action == "disable" and target.active:
        target.active = False
        changes["active"] = False
    elif payload.action == "restore" and not target.active:
        target.active = True
        changes["active"] = True
    elif payload.action == "revoke":
        target.role = "user"
        changes["role"] = "user"
    sessions_revoked = 0
    if payload.action in {"disable", "revoke"} and changes:
        sessions = db.scalars(
            select(UserSession).where(
                UserSession.user_id == target.id, UserSession.revoked_at.is_(None)
            )
        ).all()
        for session in sessions:
            session.revoked_at = utcnow()
        sessions_revoked = len(sessions)
    if changes:
        action_name = (
            "admin.account.revoked"
            if payload.action == "revoke"
            else "admin.account.status_changed"
        )
        db.add(
            AuditEvent(
                actor_id=actor.id,
                action=action_name,
                subject_id=target.id,
                details_json=json.dumps({**changes, "sessions_revoked": sessions_revoked}),
            )
        )
        db.commit()
    return {"id": target.id, "email": target.email, "active": target.active, "role": target.role}


@private_api.get("/admin/queue")
def admin_queue(
    status_filter: str | None = None,
    page_size: int = 50,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    _set_rls_principal(db, "admin", user.id)
    page_size = min(100, max(1, page_size))
    query = select(InferenceJob).order_by(InferenceJob.created_at.desc())
    if status_filter in {"queued", "processing", "completed", "failed"}:
        query = query.where(InferenceJob.status == status_filter)
    jobs = db.scalars(query.limit(page_size)).all()
    return {
        "items": [
            {
                "id": job.id,
                "analysis_id": job.analysis_id,
                "status": job.status,
                "attempts": job.attempts,
                "worker_id": job.worker_id,
                "last_error": job.last_error,
                "created_at": job.created_at,
                "updated_at": job.updated_at,
            }
            for job in jobs
        ]
    }


@private_api.post("/admin/analyses/{analysis_id}/retry", status_code=202)
def admin_retry_analysis(
    analysis_id: str, actor: User = Depends(current_user), db: Session = Depends(get_db)
):
    if actor.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    _set_rls_principal(db, "admin", actor.id)
    analysis = db.get(Analysis, analysis_id)
    job = db.scalar(select(InferenceJob).where(InferenceJob.analysis_id == analysis_id))
    if not analysis or not job:
        raise HTTPException(status_code=404, detail="Analysis job not found.")
    if job.status not in {"failed", "completed"}:
        raise HTTPException(status_code=409, detail="Only finished jobs can be queued again.")
    now = utcnow()
    job.status = "queued"
    job.attempts = 0
    job.available_at = now
    job.locked_until = None
    job.worker_id = None
    job.last_error = None
    job.updated_at = now
    analysis.status = "queued"
    analysis.completed_at = None
    db.add(AuditEvent(actor_id=actor.id, action="admin.analysis.retried", subject_id=analysis_id))
    db.commit()
    return {"analysis_id": analysis_id, "status": "queued"}


@private_api.get("/admin/audit")
def admin_audit(
    q: str | None = None,
    page: int = 1,
    page_size: int = 50,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    _set_rls_principal(db, "admin", user.id)
    query = select(AuditEvent, User.email, User.display_name).outerjoin(
        User, AuditEvent.actor_id == User.id
    )
    term = (q or "").strip()[:120]
    if term:
        pattern = f"%{_escape_like(term)}%"
        query = query.where(
            AuditEvent.action.ilike(pattern, escape="\\")
            | AuditEvent.subject_id.ilike(pattern, escape="\\")
            | AuditEvent.details_json.ilike(pattern, escape="\\")
            | User.email.ilike(pattern, escape="\\")
            | User.display_name.ilike(pattern, escape="\\")
        )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    page = min(1_000_000, max(1, page))
    page_size = min(100, max(1, page_size))
    rows = db.execute(
        query.order_by(AuditEvent.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return {
        "items": [
            {
                "id": row.id,
                "actor_id": row.actor_id,
                "actor_email": actor_email,
                "actor_name": actor_name,
                "action": row.action,
                "subject_id": row.subject_id,
                "details": json.loads(row.details_json),
                "created_at": row.created_at,
            }
            for row, actor_email, actor_name in rows
        ],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@private_api.delete("/admin/audit")
def admin_clear_audit(
    payload: AdminLogPurgePayload,
    actor: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if actor.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    if payload.confirmation != "DELETE ALL ADMIN LOGS":
        raise HTTPException(
            status_code=422,
            detail="Type DELETE ALL ADMIN LOGS exactly to clear the administrator log.",
        )
    _set_rls_principal(db, "admin", actor.id)
    deleted = db.scalar(select(func.count()).select_from(AuditEvent)) or 0
    db.execute(delete(AuditEvent))
    db.add(
        AuditEvent(
            actor_id=actor.id,
            action="admin.audit_log.cleared",
            subject_id="admin-audit-log",
            details_json=json.dumps({"deleted_entries": deleted}),
        )
    )
    db.commit()
    return {"deleted_entries": deleted, "retained_purge_record": True}


@private_api.get("/admin/user-logs")
def admin_user_logs(
    q: str | None = None,
    page: int = 1,
    page_size: int = 50,
    actor: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if actor.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    _set_rls_principal(db, "admin", actor.id)
    query = select(UserActivityEvent, User.email, User.display_name).outerjoin(
        User, UserActivityEvent.actor_id == User.id
    )
    term = (q or "").strip()[:120]
    if term:
        pattern = f"%{_escape_like(term)}%"
        query = query.where(
            UserActivityEvent.action.ilike(pattern, escape="\\")
            | UserActivityEvent.subject_id.ilike(pattern, escape="\\")
            | UserActivityEvent.details_json.ilike(pattern, escape="\\")
            | User.email.ilike(pattern, escape="\\")
            | User.display_name.ilike(pattern, escape="\\")
        )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    page = min(1_000_000, max(1, page))
    page_size = min(100, max(1, page_size))
    rows = db.execute(
        query.order_by(UserActivityEvent.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [
            {
                "id": row.id,
                "actor_id": row.actor_id,
                "actor_email": email,
                "actor_name": name,
                "action": row.action,
                "subject_id": row.subject_id,
                "details": json.loads(row.details_json),
                "created_at": row.created_at,
            }
            for row, email, name in rows
        ],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@private_api.delete("/admin/user-logs")
def admin_clear_user_logs(
    payload: AdminLogPurgePayload,
    actor: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if actor.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    if payload.confirmation != "DELETE ALL USER LOGS":
        raise HTTPException(
            status_code=422,
            detail="Type DELETE ALL USER LOGS exactly to clear user activity history.",
        )
    _set_rls_principal(db, "admin", actor.id)
    deleted = db.scalar(select(func.count()).select_from(UserActivityEvent)) or 0
    db.execute(delete(UserActivityEvent))
    db.add(
        AuditEvent(
            actor_id=actor.id,
            action="admin.user_logs.cleared",
            subject_id="user-activity-log",
            details_json=json.dumps({"deleted_entries": deleted}),
        )
    )
    db.commit()
    return {"deleted_entries": deleted}


@private_api.get("/admin/traffic")
def admin_traffic(actor: User = Depends(current_user), db: Session = Depends(get_db)):
    if actor.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    _set_rls_principal(db, "admin", actor.id)
    now_epoch = int(datetime.now(timezone.utc).timestamp())
    now = utcnow()
    cutoff = now - timedelta(hours=24)
    action_counts = db.execute(
        select(AccessAuditEvent.action, func.count())
        .where(AccessAuditEvent.created_at >= cutoff)
        .group_by(AccessAuditEvent.action)
        .order_by(func.count().desc())
    ).all()
    return {
        "window_hours": 24,
        "access_events_24h": db.scalar(
            select(func.count())
            .select_from(AccessAuditEvent)
            .where(AccessAuditEvent.created_at >= cutoff)
        )
        or 0,
        "inspections_24h": db.scalar(
            select(func.count()).select_from(Analysis).where(Analysis.created_at >= cutoff)
        )
        or 0,
        "signups_24h": db.scalar(
            select(func.count()).select_from(User).where(User.created_at >= cutoff)
        )
        or 0,
        "active_rate_limit_buckets": db.scalar(
            select(func.count())
            .select_from(RateLimitBucket)
            .where(RateLimitBucket.resets_at > now_epoch)
        )
        or 0,
        "expired_rate_limit_buckets": db.scalar(
            select(func.count())
            .select_from(RateLimitBucket)
            .where(RateLimitBucket.resets_at <= now_epoch)
        )
        or 0,
        "blocked_networks": db.scalar(
            select(func.count()).select_from(IpBlock).where(IpBlock.status == "blocked")
        )
        or 0,
        "allowlisted_networks": db.scalar(select(func.count()).select_from(IpWhitelist)) or 0,
        "event_breakdown": [{"action": action, "count": count} for action, count in action_counts],
    }


@private_api.post("/admin/traffic/clear-expired")
def admin_clear_expired_traffic(
    payload: AdminTrafficCleanupPayload,
    actor: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if actor.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    if payload.confirmation != "CLEAR EXPIRED TRAFFIC COUNTERS":
        raise HTTPException(
            status_code=422,
            detail=(
                "Type CLEAR EXPIRED TRAFFIC COUNTERS exactly to clear expired rate-limit counters."
            ),
        )
    _set_rls_principal(db, "admin", actor.id)
    now_epoch = int(datetime.now(timezone.utc).timestamp())
    result = db.execute(delete(RateLimitBucket).where(RateLimitBucket.resets_at <= now_epoch))
    deleted = result.rowcount or 0
    db.add(
        AuditEvent(
            actor_id=actor.id,
            action="admin.traffic.expired_counters_cleared",
            subject_id="rate-limit-buckets",
            details_json=json.dumps({"deleted_entries": deleted}),
        )
    )
    db.commit()
    return {"deleted_entries": deleted}


@private_api.post("/admin/security/block-ip", status_code=201)
def admin_block_ip(
    payload: AdminBlockIpPayload, actor: User = Depends(current_user), db: Session = Depends(get_db)
):
    if actor.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    try:
        raw_ip = ipaddress.ip_address(payload.ip_address.strip()).compressed
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Enter a valid IPv4 or IPv6 address.") from exc
    _set_rls_principal(db, "admin", actor.id)
    hashed_ip = _ip_hash(raw_ip)
    if db.get(IpWhitelist, hashed_ip):
        raise HTTPException(
            status_code=409,
            detail="Remove this address from the network allowlist before blocking it.",
        )
    existing = _ip_block_for_hash(db, hashed_ip)
    if existing:
        return {"id": existing.id, "reference_id": existing.reference_id, "status": existing.status}
    linked_ids = _linked_account_ids(db, hashed_ip)
    reason = payload.reason.strip()[:80] or "Administrator network restriction"
    block = IpBlock(
        ip_hash=hashed_ip,
        reference_id=f"CGS-BLK-{secrets.token_hex(3).upper()}",
        status="blocked",
        reason=reason,
        linked_account_ids_json=json.dumps(linked_ids),
        resolved_by=None,
    )
    db.add(block)
    db.add(
        AuditEvent(
            actor_id=actor.id,
            action="admin.ip_block.created",
            subject_id=block.reference_id,
            details_json=json.dumps({"reason": reason, "linked_accounts": len(linked_ids)}),
        )
    )
    _append_access_audit(
        db,
        "admin.ip_block.created",
        reason=reason,
        ip_hash=hashed_ip,
        reference_id=block.reference_id,
        actor_id=actor.id,
    )
    db.commit()
    return {"id": block.id, "reference_id": block.reference_id, "status": block.status}


@private_api.get("/admin/ip-whitelist")
def admin_ip_whitelist(actor: User = Depends(current_user), db: Session = Depends(get_db)):
    if actor.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    _set_rls_principal(db, "admin", actor.id)
    rows = db.scalars(select(IpWhitelist).order_by(IpWhitelist.created_at.desc())).all()
    return {
        "items": [
            {
                "ip_hash": row.ip_hash,
                "fingerprint": row.ip_hash[:12],
                "reason": row.reason,
                "created_at": row.created_at,
            }
            for row in rows
        ]
    }


@private_api.delete("/admin/ip-whitelist/{ip_hash}")
def admin_remove_ip_whitelist(
    ip_hash: str, actor: User = Depends(current_user), db: Session = Depends(get_db)
):
    if actor.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    if not re.fullmatch(r"[a-f0-9]{64}", ip_hash):
        raise HTTPException(status_code=422, detail="This network allowlist entry is invalid.")
    _set_rls_principal(db, "admin", actor.id)
    row = db.get(IpWhitelist, ip_hash)
    if not row:
        raise HTTPException(status_code=404, detail="Network allowlist entry not found.")
    db.delete(row)
    db.add(
        AuditEvent(actor_id=actor.id, action="admin.ip_whitelist.removed", subject_id=ip_hash[:12])
    )
    _append_access_audit(db, "admin.ip_whitelist.removed", ip_hash=ip_hash, actor_id=actor.id)
    db.commit()
    return {"removed": True}


@private_api.get("/admin/ip-blocks")
def admin_ip_blocks(
    limit: int = 100, actor: User = Depends(current_user), db: Session = Depends(get_db)
):
    if actor.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    _set_rls_principal(db, "admin", actor.id)
    rows = db.scalars(
        select(IpBlock).order_by(IpBlock.created_at.desc()).limit(min(500, max(1, limit)))
    ).all()
    result = []
    for row in rows:
        ids = json.loads(row.linked_account_ids_json or "[]")
        users = db.scalars(select(User).where(User.id.in_(ids))).all() if ids else []
        result.append(
            {
                "id": row.id,
                "reference_id": row.reference_id,
                "status": row.status,
                "reason": row.reason,
                "linked_accounts": [{"id": user.id, "email": user.email} for user in users],
                "created_at": row.created_at,
                "raised_limit": row.raised_limit,
            }
        )
    return {"items": result}


@private_api.post("/admin/ip-blocks/{block_id}/unblock")
def admin_unblock_ip(
    block_id: str, actor: User = Depends(current_user), db: Session = Depends(get_db)
):
    if actor.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    _set_rls_principal(db, "admin", actor.id)
    block = db.get(IpBlock, block_id)
    if not block:
        raise HTTPException(status_code=404, detail="IP restriction not found.")
    linked_count = len(_linked_account_ids(db, block.ip_hash))
    block.raised_limit = max(block.raised_limit or MAX_ACCOUNTS_PER_IP, linked_count + 1)
    block.status = "unblocked"
    block.resolved_by = actor.id
    db.add(
        AuditEvent(
            actor_id=actor.id, action="admin.ip_block.unblocked", subject_id=block.reference_id
        )
    )
    _append_access_audit(
        db,
        "admin.ip_block.unblocked",
        ip_hash=block.ip_hash,
        reference_id=block.reference_id,
        actor_id=actor.id,
        details={"next_account_limit": block.raised_limit},
    )
    db.commit()
    return {"reference_id": block.reference_id, "status": block.status}


@private_api.post("/admin/ip-blocks/{block_id}/raise-limit")
def admin_raise_ip_limit(
    block_id: str,
    payload: RaiseIpLimitPayload,
    actor: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if actor.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    _set_rls_principal(db, "admin", actor.id)
    block = db.get(IpBlock, block_id)
    if not block:
        raise HTTPException(status_code=404, detail="IP restriction not found.")
    linked_count = len(_linked_account_ids(db, block.ip_hash))
    if payload.limit <= linked_count:
        raise HTTPException(
            status_code=422, detail="The raised limit must exceed the number of linked accounts."
        )
    block.raised_limit = payload.limit
    db.add(
        AuditEvent(
            actor_id=actor.id,
            action="admin.ip_block.limit_raised",
            subject_id=block.reference_id,
            details_json=json.dumps({"limit": payload.limit}),
        )
    )
    _append_access_audit(
        db,
        "admin.ip_block.limit_raised",
        ip_hash=block.ip_hash,
        reference_id=block.reference_id,
        actor_id=actor.id,
        details={"limit": payload.limit},
    )
    db.commit()
    return {"reference_id": block.reference_id, "status": block.status, "limit": payload.limit}


@private_api.post("/admin/ip-whitelist")
def admin_whitelist_ip(
    payload: WhitelistIpPayload, actor: User = Depends(current_user), db: Session = Depends(get_db)
):
    if actor.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    try:
        raw_ip = ipaddress.ip_address(payload.ip_address.strip()).compressed
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Enter a valid IPv4 or IPv6 address.") from exc
    hashed_ip = _ip_hash(raw_ip)
    _set_rls_principal(db, "admin", actor.id)
    entry = db.get(IpWhitelist, hashed_ip)
    if entry:
        entry.reason = payload.reason
    else:
        db.add(IpWhitelist(ip_hash=hashed_ip, added_by=actor.id, reason=payload.reason))
    blocks = db.scalars(
        select(IpBlock).where(IpBlock.ip_hash == hashed_ip, IpBlock.status == "blocked")
    ).all()
    for block in blocks:
        block.status = "whitelisted"
        block.resolved_by = actor.id
    db.add(
        AuditEvent(
            actor_id=actor.id,
            action="admin.ip_whitelisted",
            subject_id=hashed_ip[:16],
            details_json=json.dumps({"reason": payload.reason}),
        )
    )
    _append_access_audit(
        db,
        "admin.ip_whitelisted",
        ip_hash=hashed_ip,
        actor_id=actor.id,
        details={"reason": payload.reason},
    )
    db.commit()
    return {"whitelisted": True}


@private_api.get("/admin/unblock-requests")
def admin_unblock_requests(
    status_filter: str | None = "pending",
    limit: int = 100,
    actor: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if actor.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    _set_rls_principal(db, "admin", actor.id)
    query = select(UnblockRequest).order_by(UnblockRequest.created_at.desc())
    if status_filter in {"pending", "approved", "rejected"}:
        query = query.where(UnblockRequest.status == status_filter)
    rows = db.scalars(query.limit(min(500, max(1, limit)))).all()
    return {
        "items": [
            {
                "id": row.id,
                "reference_id": row.reference_id,
                "name": row.name,
                "email": row.email,
                "reason": row.reason,
                "status": row.status,
                "created_at": row.created_at,
            }
            for row in rows
        ]
    }


@private_api.post("/admin/unblock-requests/{request_id}/resolve")
def admin_resolve_unblock_request(
    request_id: str,
    payload: ResolveUnblockPayload,
    actor: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if actor.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    _set_rls_principal(db, "admin", actor.id)
    request_row = db.get(UnblockRequest, request_id)
    if not request_row:
        raise HTTPException(status_code=404, detail="Unblock request not found.")
    request_row.status = payload.status
    request_row.resolved_by = actor.id
    request_row.resolution_note = payload.note
    request_row.resolved_at = utcnow()
    blocks = db.scalars(
        select(IpBlock).where(
            IpBlock.reference_id == request_row.reference_id, IpBlock.status == "blocked"
        )
    ).all()
    if payload.status == "approved":
        for block in blocks:
            linked_count = len(_linked_account_ids(db, block.ip_hash))
            block.raised_limit = max(block.raised_limit or MAX_ACCOUNTS_PER_IP, linked_count + 1)
            block.status = "unblocked"
            block.resolved_by = actor.id
    db.add(
        AuditEvent(
            actor_id=actor.id,
            action="admin.unblock_request.resolved",
            subject_id=request_row.reference_id,
            details_json=json.dumps({"status": payload.status, "note": payload.note}),
        )
    )
    _append_access_audit(
        db,
        "admin.unblock_request.resolved",
        reference_id=request_row.reference_id,
        actor_id=actor.id,
        details={"status": payload.status},
    )
    db.commit()
    return {"id": request_row.id, "status": request_row.status}


@public_api.post("/support/unblock-request", status_code=201)
def create_unblock_request(
    payload: UnblockRequestPayload, request: Request, db: Session = Depends(get_db)
):
    if payload.website:
        # Honeypot submissions look successful to avoid teaching bots the field name.
        return {"submitted": True}
    raw_ip = _client_ip(request)
    hashed_ip = _ip_hash(raw_ip)
    set_auth_rls_principal(db)
    block = db.scalar(
        select(IpBlock).where(
            IpBlock.ip_hash == hashed_ip,
            IpBlock.reference_id == payload.reference_id,
            IpBlock.status == "blocked",
        )
    )
    if not block:
        raise HTTPException(
            status_code=404, detail="The restriction reference could not be found for this network."
        )
    row = UnblockRequest(
        reference_id=payload.reference_id,
        name=payload.name.strip(),
        email=_normalized_email(str(payload.email)),
        reason=payload.reason.strip(),
    )
    db.add(row)
    _append_access_audit(
        db, "ip.unblock_request.created", ip_hash=hashed_ip, reference_id=payload.reference_id
    )
    db.commit()
    return {"submitted": True, "request_id": row.id}


@public_api.post("/support/contact", status_code=201)
def submit_contact_inquiry(
    payload: ContactInquiryPayload, request: Request, db: Session = Depends(get_db)
):
    if payload.website:
        return {
            "submitted": True,
            "message": "Thank you for contacting us. Your message has been received.",
        }
    raw_ip = _client_ip(request)
    hashed_ip = _ip_hash(raw_ip)

    # Fixed window rate limit: 5 submissions per 10 minutes per IP
    key = f"contact:{hashed_ip}"
    count, resets_at = _consume_rate_limit(key, 5, 600)
    if count > 5:
        retry_after = max(1, resets_at - int(datetime.now(timezone.utc).timestamp()))
        raise HTTPException(
            status_code=429,
            detail=(
                "Too many inquiries submitted from this network. Please wait a few "
                "minutes before trying again."
            ),
            headers={"Retry-After": str(retry_after)},
        )

    name = payload.name.strip()
    email = _normalized_email(str(payload.email))
    topic = payload.topic.strip()
    message = payload.message.strip()
    set_auth_rls_principal(db)
    inquiry = ContactInquiry(
        id=str(uuid.uuid4()), name=name, email=email, topic=topic, message=message
    )
    db.add(inquiry)
    _append_access_audit(
        db,
        "support.contact_inquiry",
        reason=topic[:80],
        ip_hash=hashed_ip,
        details={
            "contact_inquiry_id": inquiry.id,
            "name": name,
            "email": email,
            "topic": topic,
            "message_length": len(message),
        },
    )
    db.commit()

    if SUPPORT_CONTACT_EMAIL:
        subject = f"[CGS DeepFake Shield Inquiry] {topic} - {name}"
        body = (
            f"New support/contact inquiry received:\n\n"
            f"Name: {name}\n"
            f"Email: {email}\n"
            f"Topic: {topic}\n\n"
            f"Message:\n{message}\n"
        )
        _send_account_email(SUPPORT_CONTACT_EMAIL, subject, body)

    return {
        "submitted": True,
        "inquiry_id": inquiry.id,
        "message": (
            "Thank you for reaching out. Your inquiry has been successfully "
            "submitted and our team will review it shortly."
        ),
    }


@app.get("/health", include_in_schema=False)
def health_alias():
    return {"status": "ok"}


app.include_router(public_api)
app.include_router(private_api)

_PUBLIC_API_OPERATIONS = {
    ("GET", "/api/v1/config"),
    ("POST", "/api/v1/auth/signup"),
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/verify-email"),
    ("POST", "/api/v1/auth/forgot-password"),
    ("POST", "/api/v1/auth/reset-password"),
    ("GET", "/api/v1/account/status"),
    ("POST", "/api/v1/analyses"),
    ("GET", "/api/v1/analyses"),
    ("GET", "/api/v1/verifications"),
    ("GET", "/api/v1/analyses/{analysis_id}"),
    ("GET", "/api/v1/verifications/{analysis_id}"),
    ("GET", "/api/v1/analyses/{analysis_id}/image"),
    ("GET", "/api/v1/analyses/{analysis_id}/original"),
    ("DELETE", "/api/v1/analyses/{analysis_id}"),
    ("POST", "/api/v1/support/unblock-request"),
    ("POST", "/api/v1/support/contact"),
}


def _has_current_user_dependency(dependant) -> bool:
    if dependant.call is current_user:
        return True
    return any(_has_current_user_dependency(child) for child in dependant.dependencies)


for api_route in app.routes:
    if isinstance(api_route, APIRoute) and api_route.path.startswith("/api/v1/"):
        for method in api_route.methods or set():
            if (
                method,
                api_route.path,
            ) not in _PUBLIC_API_OPERATIONS and not _has_current_user_dependency(
                api_route.dependant
            ):
                raise RuntimeError(
                    f"Private API route {method} {api_route.path} is missing "
                    "server-side authentication."
                )
