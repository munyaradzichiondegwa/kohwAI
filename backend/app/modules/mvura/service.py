"""Business logic for Mvura — Water Security.

Trust model: `Borehole.status` is the last status CONFIRMED by a validator/admin.
A farmer's report is stored as a pending BoreholeReport and shown as an *unverified*
signal (`pending_report`); it only changes the public status once approved
(see modules/community/service.decide). This stops one person flipping a borehole to
"dry" for everyone and stamping it "verified".
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.mvura import Borehole, BoreholeReport
from app.utils.audit import write_audit_log


def list_boreholes(db: Session, district: Optional[str] = None) -> list[dict]:
    q = db.query(Borehole)
    if district:
        q = q.filter(Borehole.district == district)
    boreholes = q.order_by(Borehole.name).all()
    if not boreholes:
        return []

    ids = [b.id for b in boreholes]
    pending = db.query(BoreholeReport).filter(
        BoreholeReport.borehole_id.in_(ids), BoreholeReport.status == "pending"
    ).order_by(BoreholeReport.created_at.desc()).all()
    latest: dict = {}
    counts: dict = {}
    for r in pending:                       # ordered newest-first: first seen = newest
        latest.setdefault(r.borehole_id, r.new_status)
        counts[r.borehole_id] = counts.get(r.borehole_id, 0) + 1

    return [to_dict(b, latest.get(b.id), counts.get(b.id, 0)) for b in boreholes]


def to_dict(b: Borehole, pending_report: Optional[str] = None, pending_reports: int = 0) -> dict:
    return {
        "id": str(b.id), "name": b.name, "village": b.village, "district": b.district,
        "lat": b.lat, "lng": b.lng, "status": b.status, "depth_m": b.depth_m,
        "last_verified": b.last_verified, "verified": b.last_verified is not None,
        "pending_report": pending_report, "pending_reports": pending_reports,
    }


def create_borehole(db: Session, payload: dict, admin_id: str | None = None) -> Borehole:
    now = datetime.now(timezone.utc)
    # An admin registering a borehole is itself a verification.
    borehole = Borehole(status="working", last_verified=now, verified_by=admin_id, **payload)
    db.add(borehole)
    db.commit()
    db.refresh(borehole)
    write_audit_log(db, admin_id, "borehole.create", "borehole", str(borehole.id), after=payload)
    return borehole


def report_status(db: Session, borehole_id, user_id: str, new_status: str, note: Optional[str]) -> BoreholeReport:
    """Store the report as PENDING. Does not touch the public borehole status."""
    borehole = db.query(Borehole).filter(Borehole.id == borehole_id).first()
    if not borehole:
        raise ValueError("Borehole not found")

    # One open report per farmer per borehole: a repeat updates it instead of stacking up.
    report = db.query(BoreholeReport).filter(
        BoreholeReport.borehole_id == borehole_id, BoreholeReport.reported_by == user_id,
        BoreholeReport.status == "pending").first()
    if report:
        report.new_status, report.note = new_status, note
    else:
        report = BoreholeReport(borehole_id=borehole_id, reported_by=user_id, new_status=new_status,
                                note=note, status="pending", validated=False)
        db.add(report)
    db.commit()
    db.refresh(report)
    return report
