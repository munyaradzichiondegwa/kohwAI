"""audit_logs: real now() default + DB-level immutability

The initial migration used server_default='now()' (a string literal), which
PostgreSQL evaluated once at migration time, freezing every row's timestamp to
the moment the migration ran. This replaces it with the now() function and adds
triggers so audit rows can never be UPDATEd, DELETEd or TRUNCATEd by the app.

Retention purges (PRD: 24 months) must be done by a privileged maintenance job
that disables the trigger deliberately, never by the application role.

Revision ID: a1b2c3d4e5f6
Revises: fd14ce567518
"""
from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "fd14ce567518"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE audit_logs ALTER COLUMN timestamp SET DEFAULT now()")
    op.execute("""
        CREATE OR REPLACE FUNCTION audit_logs_immutable() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_logs is append-only (% not permitted)', TG_OP;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER audit_logs_no_update_delete
        BEFORE UPDATE OR DELETE ON audit_logs
        FOR EACH ROW EXECUTE FUNCTION audit_logs_immutable();
    """)
    op.execute("""
        CREATE TRIGGER audit_logs_no_truncate
        BEFORE TRUNCATE ON audit_logs
        FOR EACH STATEMENT EXECUTE FUNCTION audit_logs_immutable();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_logs_no_truncate ON audit_logs")
    op.execute("DROP TRIGGER IF EXISTS audit_logs_no_update_delete ON audit_logs")
    op.execute("DROP FUNCTION IF EXISTS audit_logs_immutable()")
    op.execute("ALTER TABLE audit_logs ALTER COLUMN timestamp SET DEFAULT now()  -- keep a working default (the original was a frozen constant)")
