"""Business logic for Community & Validation — the moderator queue that
spans several underlying tables (pest sightings, borehole status reports,
and generic community reports)."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.zunde import PestSighting
from app.models.mvura import BoreholeReport, Borehole
from app.models.community import CommunityReport, ValidatorAssignment
from app.models.user import User


def get_queue(db: Session, district: str | None = None) -> list[dict]:
    items = []

    pest_q = db.query(PestSighting).filter(PestSighting.status == "pending")
    if district:
        pest_q = pest_q.filter(PestSighting.district == district)
    for p in pest_q.order_by(PestSighting.created_at.desc()).limit(50):
        items.append({
            "kind": "pest_sighting", "id": str(p.id), "district": p.district,
            "summary": f"{p.species} ({p.severity}) — {p.affected_ha or '?'} ha affected",
            "reporter_phone": _phone(db, p.user_id), "created_at": p.created_at,
        })

    bh_q = db.query(BoreholeReport).filter(BoreholeReport.validated.is_(False))
    for r in bh_q.order_by(BoreholeReport.created_at.desc()).limit(50):
        borehole = db.query(Borehole).filter(Borehole.id == r.borehole_id).first()
        if district and borehole and borehole.district != district:
            continue
        items.append({
            "kind": "borehole_report", "id": str(r.id),
            "district": borehole.district if borehole else "?",
            "summary": f"{borehole.name if borehole else 'Unknown borehole'} reported as '{r.new_status}'",
            "reporter_phone": _phone(db, r.reported_by), "created_at": r.created_at,
        })

    cr_q = db.query(CommunityReport).filter(CommunityReport.status == "pending")
    if district:
        cr_q = cr_q.filter(CommunityReport.district == district)
    for c in cr_q.order_by(CommunityReport.created_at.desc()).limit(50):
        items.append({
            "kind": "community_report", "id": str(c.id), "district": c.district,
            "summary": c.description or c.report_type,
            "reporter_phone": _phone(db, c.submitter_id), "created_at": c.created_at,
        })

    items.sort(key=lambda x: x["created_at"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return items


def _phone(db: Session, user_id) -> str | None:
    if not user_id:
        return None
    u = db.query(User).filter(User.id == user_id).first()
    return u.phone if u else None


def _record_review(db: Session, validator_id: str):
    assignment = db.query(ValidatorAssignment).filter(ValidatorAssignment.user_id == validator_id).first()
    if assignment:
        assignment.reports_reviewed = (assignment.reports_reviewed or 0) + 1
        assignment.last_active_at = datetime.now(timezone.utc)
        db.commit()


def decide(db: Session, kind: str, item_id: str, validator_id: str, approve: bool, reason: str | None) -> bool:
    now = datetime.now(timezone.utc)
    if kind == "pest_sighting":
        row = db.query(PestSighting).filter(PestSighting.id == item_id).first()
        if not row:
            return False
        row.status = "approved" if approve else "rejected"
        row.validated_by = validator_id
        row.validated_at = now
        if not approve:
            row.rejection_reason = reason
    elif kind == "borehole_report":
        row = db.query(BoreholeReport).filter(BoreholeReport.id == item_id).first()
        if not row:
            return False
        row.validated = True
        row.validated_by = validator_id
        row.validated_at = now
        if not approve:
            row.rejection_reason = reason
            # Overturned — the borehole's status field was set optimistically
            # when reported; revert is out of scope without a status history
            # table, so we flag it for a follow-up report instead.
    elif kind == "community_report":
        row = db.query(CommunityReport).filter(CommunityReport.id == item_id).first()
        if not row:
            return False
        row.status = "approved" if approve else "rejected"
        row.reviewed_by = validator_id
        row.reviewed_at = now
        if not approve:
            row.rejection_reason = reason
    else:
        return False

    db.commit()
    _record_review(db, validator_id)
    return True
