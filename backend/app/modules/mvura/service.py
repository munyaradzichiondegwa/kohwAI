"""Business logic for Mvura — Water Security."""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.mvura import Borehole, BoreholeReport


def list_boreholes(db: Session, district: Optional[str] = None):
    q = db.query(Borehole)
    if district:
        q = q.filter(Borehole.district == district)
    return q.order_by(Borehole.name).all()


def create_borehole(db: Session, payload: dict) -> Borehole:
    borehole = Borehole(status="working", **payload)
    db.add(borehole)
    db.commit()
    db.refresh(borehole)
    return borehole


def report_status(db: Session, borehole_id: str, user_id: str, new_status: str, note: Optional[str]) -> BoreholeReport:
    """Community status reports are logged immediately AND applied optimistically
    to the borehole's displayed status (offline-first: farmers need to see this
    fast), but flagged `validated=False` until a validator confirms or overturns it."""
    borehole = db.query(Borehole).filter(Borehole.id == borehole_id).first()
    if not borehole:
        raise ValueError("Borehole not found")

    report = BoreholeReport(borehole_id=borehole_id, reported_by=user_id, new_status=new_status,
                             note=note, validated=False)
    db.add(report)
    borehole.status = new_status
    borehole.last_verified = datetime.now(timezone.utc)
    db.commit()
    db.refresh(report)
    return report
