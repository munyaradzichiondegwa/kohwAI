"""Batch 3: alert dispatch tracking, account PIN, consent/preferences

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("terms_version", sa.String(30), nullable=True))
    op.add_column("users", sa.Column("sms_alerts", sa.Boolean(), nullable=False, server_default="true"))
    op.add_column("users", sa.Column("pin_hash", sa.String(128), nullable=True))
    op.add_column("users", sa.Column("pin_failed_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("pin_locked_until", sa.DateTime(timezone=True), nullable=True))

    op.add_column("alerts", sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_alerts_dispatched_at", "alerts", ["dispatched_at"])
    # Alerts that already exist were never sent by any worker; do not blast them out now.
    op.execute("UPDATE alerts SET dispatched_at = now() WHERE dispatched_at IS NULL")

    op.create_table(
        "alert_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("channel", sa.String(10), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("provider_status", sa.String(100), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("alert_id", "user_id", "channel", name="uq_delivery_alert_user_channel"),
    )
    op.create_index("ix_alert_deliveries_alert_id", "alert_deliveries", ["alert_id"])
    op.create_index("ix_alert_deliveries_user_id", "alert_deliveries", ["user_id"])


def downgrade() -> None:
    op.drop_table("alert_deliveries")
    op.drop_index("ix_alerts_dispatched_at", table_name="alerts")
    op.drop_column("alerts", "dispatched_at")
    for c in ("pin_locked_until", "pin_failed_attempts", "pin_hash", "sms_alerts", "terms_version"):
        op.drop_column("users", c)
