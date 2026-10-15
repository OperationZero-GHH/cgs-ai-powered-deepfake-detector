"""Enforce PostgreSQL tenant and administrator row access policies.

SQLite remains the local single-user development backend and relies on the
application's owner-scoped queries. Production PostgreSQL applies these rules
at the database boundary as an additional authorization layer.
"""

from alembic import op

revision = "0003_postgres_rls"
down_revision = "0002_queue_security_admin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE users FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY users_select_self_or_auth ON users
        FOR SELECT
        USING (
            current_setting('cgs.actor', true) IN ('admin', 'auth')
            OR id = NULLIF(current_setting('cgs.user_id', true), '')
        )
        """
    )
    op.execute(
        """
        CREATE POLICY users_insert_auth_or_admin ON users
        FOR INSERT
        WITH CHECK (current_setting('cgs.actor', true) IN ('admin', 'auth'))
        """
    )
    op.execute(
        """
        CREATE POLICY users_update_auth_or_admin ON users
        FOR UPDATE
        USING (current_setting('cgs.actor', true) IN ('admin', 'auth'))
        WITH CHECK (current_setting('cgs.actor', true) IN ('admin', 'auth'))
        """
    )
    op.execute(
        """
        CREATE POLICY users_delete_self_or_admin ON users
        FOR DELETE
        USING (
            current_setting('cgs.actor', true) = 'admin'
            OR id = NULLIF(current_setting('cgs.user_id', true), '')
        )
        """
    )

    op.execute("ALTER TABLE sessions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE sessions FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY sessions_select_self_or_admin ON sessions
        FOR SELECT
        USING (
            current_setting('cgs.actor', true) = 'admin'
            OR user_id = NULLIF(current_setting('cgs.user_id', true), '')
            OR token_hash = NULLIF(current_setting('cgs.session_hash', true), '')
        )
        """
    )
    op.execute(
        """
        CREATE POLICY sessions_insert_self_or_admin ON sessions
        FOR INSERT
        WITH CHECK (
            current_setting('cgs.actor', true) = 'admin'
            OR user_id = NULLIF(current_setting('cgs.user_id', true), '')
        )
        """
    )
    op.execute(
        """
        CREATE POLICY sessions_update_self_or_admin ON sessions
        FOR UPDATE
        USING (
            current_setting('cgs.actor', true) = 'admin'
            OR user_id = NULLIF(current_setting('cgs.user_id', true), '')
        )
        WITH CHECK (
            current_setting('cgs.actor', true) = 'admin'
            OR user_id = NULLIF(current_setting('cgs.user_id', true), '')
        )
        """
    )
    op.execute(
        """
        CREATE POLICY sessions_delete_self_or_admin ON sessions
        FOR DELETE
        USING (
            current_setting('cgs.actor', true) = 'admin'
            OR user_id = NULLIF(current_setting('cgs.user_id', true), '')
        )
        """
    )

    op.execute("ALTER TABLE analyses ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE analyses FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY analyses_owner_or_service ON analyses
        FOR ALL
        USING (
            current_setting('cgs.actor', true) IN ('admin', 'worker')
            OR owner_id = NULLIF(current_setting('cgs.user_id', true), '')
        )
        WITH CHECK (
            current_setting('cgs.actor', true) IN ('admin', 'worker')
            OR owner_id = NULLIF(current_setting('cgs.user_id', true), '')
        )
        """
    )

    op.execute("ALTER TABLE inference_jobs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE inference_jobs FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY inference_jobs_owner_or_service ON inference_jobs
        FOR ALL
        USING (
            current_setting('cgs.actor', true) IN ('admin', 'worker')
            OR EXISTS (
                SELECT 1 FROM analyses AS owner_analysis
                WHERE owner_analysis.id = inference_jobs.analysis_id
                  AND owner_analysis.owner_id = NULLIF(current_setting('cgs.user_id', true), '')
            )
        )
        WITH CHECK (
            current_setting('cgs.actor', true) IN ('admin', 'worker')
            OR EXISTS (
                SELECT 1 FROM analyses AS owner_analysis
                WHERE owner_analysis.id = inference_jobs.analysis_id
                  AND owner_analysis.owner_id = NULLIF(current_setting('cgs.user_id', true), '')
            )
        )
        """
    )

    op.execute("ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_events FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY audit_events_admin_only ON audit_events
        FOR ALL
        USING (current_setting('cgs.actor', true) = 'admin')
        WITH CHECK (current_setting('cgs.actor', true) = 'admin')
        """
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    op.execute("DROP POLICY IF EXISTS audit_events_admin_only ON audit_events")
    op.execute("ALTER TABLE audit_events NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_events DISABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS inference_jobs_owner_or_service ON inference_jobs")
    op.execute("ALTER TABLE inference_jobs NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE inference_jobs DISABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS analyses_owner_or_service ON analyses")
    op.execute("ALTER TABLE analyses NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE analyses DISABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS sessions_delete_self_or_admin ON sessions")
    op.execute("DROP POLICY IF EXISTS sessions_update_self_or_admin ON sessions")
    op.execute("DROP POLICY IF EXISTS sessions_insert_self_or_admin ON sessions")
    op.execute("DROP POLICY IF EXISTS sessions_select_self_or_admin ON sessions")
    op.execute("ALTER TABLE sessions NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE sessions DISABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS users_delete_self_or_admin ON users")
    op.execute("DROP POLICY IF EXISTS users_update_auth_or_admin ON users")
    op.execute("DROP POLICY IF EXISTS users_insert_auth_or_admin ON users")
    op.execute("DROP POLICY IF EXISTS users_select_self_or_auth ON users")
    op.execute("ALTER TABLE users NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY")
