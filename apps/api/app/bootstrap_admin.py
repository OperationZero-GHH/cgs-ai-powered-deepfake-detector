"""Create the first administrator from a trusted local operator session."""

from __future__ import annotations

import argparse
import getpass
import os

from sqlalchemy import select

from app import main, migrate


def bootstrap(email: str, password: str, display_name: str | None = None) -> None:
    normalized = main._normalized_email(email)
    if normalized not in main._admin_emails():
        raise SystemExit("That email address is not listed in ADMIN_EMAILS.")
    if len(password) < 15 or len(password) > 128:
        raise SystemExit("Password must be 15 to 128 characters.")
    cleaned_name = (display_name or normalized.split("@", 1)[0]).strip()
    if os.getenv("APP_ENV") != "test":
        migrate.main()
    with main.SessionLocal() as db:
        main.set_auth_rls_principal(db)
        user = db.scalar(select(main.User).where(main.User.email == normalized))
        if user is None:
            user = main.User(
                email=normalized,
                email_identity=main._email_identity(normalized),
                email_verified_at=main.utcnow(),
                display_name=cleaned_name,
                password_hash=main.PASSWORDS.hash(password),
                role="admin",
            )
            db.add(user)
        else:
            user.email_identity = main._email_identity(normalized)
            user.email_verified_at = user.email_verified_at or main.utcnow()
            user.role = "admin"
            user.password_hash = main.PASSWORDS.hash(password)
            if display_name:
                user.display_name = cleaned_name
        db.flush()
        main._set_rls_principal(db, "admin", user.id)
        db.add(main.AuditEvent(actor_id=user.id, action="admin.bootstrap.completed", subject_id=user.id))
        db.commit()
    print(f"Administrator account is ready for {normalized}.")


def cli() -> None:
    parser = argparse.ArgumentParser(description="Create an allowlisted CGS DeepFake Shield administrator.")
    parser.add_argument("email", help="An address present in ADMIN_EMAILS")
    parser.add_argument("--name", help="Display name for a new account")
    args = parser.parse_args()

    if main.APP_ENV == "e2e":
        password = os.getenv("E2E_ADMIN_PASSWORD", "")
        if not password:
            raise SystemExit("E2E_ADMIN_PASSWORD is required for the isolated browser-test administrator.")
    else:
        password = getpass.getpass("Administrator password (15–128 characters): ")
        confirmation = getpass.getpass("Confirm password: ")
        if password != confirmation:
            raise SystemExit("Passwords did not match.")
    bootstrap(args.email, password, args.name)


if __name__ == "__main__":
    cli()
