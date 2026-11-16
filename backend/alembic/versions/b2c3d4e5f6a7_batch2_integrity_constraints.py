"""Batch 2: integrity constraints and review status

* borehole_reports.status (pending/approved/rejected) - `validated=true` used to be set on
  rejections too, so rejected reports were indistinguishable from approved ones.
* market_listings.share_phone - sellers opt in to showing their phone (default hidden).
* insurance_enrollments: unique per (user, season) instead of one row per user for life.
* payout_records: one payout per enrolment. Pre-existing duplicates (the old code could
  pay once per differing drought index) are marked 'void_duplicate', never deleted.
* satellite_readings: unique (district, reading_date, source) so ingestion can upsert.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
"""
from alembic import op
import sqlalchemy as sa

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("borehole_reports", sa.Column("status", sa.String(20), nullable=False, server_default="pending"))
    op.create_index("ix_borehole_reports_status", "borehole_reports", ["status"])
    op.execute("UPDATE borehole_reports SET status='rejected' WHERE validated IS TRUE AND rejection_reason IS NOT NULL")
    op.execute("UPDATE borehole_reports SET status='approved' WHERE validated IS TRUE AND rejection_reason IS NULL")

    op.add_column("market_listings", sa.Column("share_phone", sa.Boolean(), nullable=False, server_default="false"))

    op.drop_constraint("insurance_enrollments_user_id_key", "insurance_enrollments", type_="unique")
    op.create_unique_constraint("uq_enrollment_user_season", "insurance_enrollments", ["user_id", "season"])

    op.execute("""
        UPDATE payout_records p SET status='void_duplicate'
        WHERE p.id IN (
            SELECT id FROM (
                SELECT id, ROW_NUMBER() OVER (PARTITION BY enrollment_id ORDER BY created_at, id) AS rn
                FROM payout_records WHERE status <> 'void_duplicate'
            ) t WHERE t.rn > 1
        )
    """)
    op.create_index("uq_payout_enrollment", "payout_records", ["enrollment_id"], unique=True,
                    postgresql_where=sa.text("status <> 'void_duplicate'"))

    op.create_unique_constraint("uq_reading_district_date_source", "satellite_readings",
                                ["district", "reading_date", "source"])


def downgrade() -> None:
    op.drop_constraint("uq_reading_district_date_source", "satellite_readings", type_="unique")
    op.drop_index("uq_payout_enrollment", table_name="payout_records")
    op.drop_constraint("uq_enrollment_user_season", "insurance_enrollments", type_="unique")
    op.create_unique_constraint("insurance_enrollments_user_id_key", "insurance_enrollments", ["user_id"])
    op.drop_column("market_listings", "share_phone")
    op.drop_index("ix_borehole_reports_status", table_name="borehole_reports")
    op.drop_column("borehole_reports", "status")
