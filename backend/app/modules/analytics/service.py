"""Business logic for Analytics — real aggregate counts from the database.
No projected/estimated figures here: every number is a direct SQL COUNT."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.zunde import DiagnosisReport, PestSighting
from app.models.alerts import Alert
from app.models.mvura import Borehole, BoreholeReport
from app.models.musika import MarketListing


def get_overview(db: Session) -> dict:
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    total_users = db.query(func.count(User.id)).scalar() or 0
    new_users = db.query(func.count(User.id)).filter(User.created_at >= week_ago).scalar() or 0
    diagnoses = db.query(func.count(DiagnosisReport.id)).filter(DiagnosisReport.created_at >= week_ago).scalar() or 0
    active_alerts = db.query(func.count(Alert.id)).filter(Alert.is_active.is_(True)).scalar() or 0
    active_listings = db.query(func.count(MarketListing.id)).filter(MarketListing.is_active.is_(True)).scalar() or 0

    status_rows = db.query(Borehole.status, func.count(Borehole.id)).group_by(Borehole.status).all()
    boreholes_by_status = {status: count for status, count in status_rows}

    pending_pest = db.query(func.count(PestSighting.id)).filter(PestSighting.status == "pending").scalar() or 0
    pending_borehole = db.query(func.count(BoreholeReport.id)).filter(BoreholeReport.validated.is_(False)).scalar() or 0

    return {
        "total_users": total_users,
        "new_users_last_7_days": new_users,
        "diagnoses_last_7_days": diagnoses,
        "active_alerts": active_alerts,
        "boreholes_by_status": boreholes_by_status,
        "active_market_listings": active_listings,
        "pending_validation_queue": pending_pest + pending_borehole,
        "generated_at": now.isoformat(),
    }
