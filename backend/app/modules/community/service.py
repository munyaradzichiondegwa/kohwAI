"""Business logic for Community & Validation — the moderator queue that spans several
underlying tables (pest sightings, borehole status reports, generic community reports).

Integrity rules enforced here (PRD §Validators):
  * a reviewer can never approve/reject their OWN submission;
  * validators only see and act on districts they are assigned to (admins: all districts);
  * every report moves pending -> approved | rejected exactly once; rejection needs a reason;
  * a borehole status report changes the PUBLIC borehole status only once approved.
"""
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.zunde import PestSighting
from app.models.mvura import BoreholeReport, Borehole
from app.models.community import CommunityReport, ValidatorAssignment
from app.models.user import User
from app.utils.audit import write_audit_log
from app.utils.sms import send_sms
from app.utils.validation import mask_phone

logger = logging.getLogger(__name__)


class NotFound(Exception): ...
class Forbidden(Exception): ...
class Conflict(Exception): ...


def validator_districts(db: Session, user: User) -> list[str] | None:
    """None = unrestricted (admin). [] = validator with no active assignment = sees nothing."""
    if "admin" in (user.roles or []):
        return None
    rows = db.query(ValidatorAssignment.district).filter(
        ValidatorAssignment.user_id == user.id, ValidatorAssignment.is_active.is_(True)).all()
    return sorted({r[0] for r in rows})


def _phones(db: Session, ids: set) -> dict:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    return {u.id: u.phone for u in db.query(User).filter(User.id.in_(ids)).all()}


def get_queue(db: Session, user: User, district: str | None = None) -> list[dict]:
    scope = validator_districts(db, user)
    if scope is not None:
        if district and district not in scope:
            return []
        districts = [district] if district else scope
        if not districts:
            return []
    else:
        districts = [district] if district else None

    items: list[dict] = []

    pq = db.query(PestSighting).filter(PestSighting.status == "pending", PestSighting.user_id != user.id)
    if districts is not None:
        pq = pq.filter(PestSighting.district.in_(districts))
    pests = pq.order_by(PestSighting.created_at.desc()).limit(50).all()

    bq = (db.query(BoreholeReport, Borehole).join(Borehole, Borehole.id == BoreholeReport.borehole_id)
          .filter(BoreholeReport.status == "pending", BoreholeReport.reported_by != user.id))
    if districts is not None:
        bq = bq.filter(Borehole.district.in_(districts))
    bhs = bq.order_by(BoreholeReport.created_at.desc()).limit(50).all()

    cq = db.query(CommunityReport).filter(CommunityReport.status == "pending", CommunityReport.submitter_id != user.id)
    if districts is not None:
        cq = cq.filter(CommunityReport.district.in_(districts))
    crs = cq.order_by(CommunityReport.created_at.desc()).limit(50).all()

    phones = _phones(db, {p.user_id for p in pests} | {r.reported_by for r, _ in bhs} | {c.submitter_id for c in crs})

    for p in pests:
        items.append({"kind": "pest_sighting", "id": str(p.id), "district": p.district,
                      "summary": f"{p.species} ({p.severity}) — {p.affected_ha or '?'} ha affected",
                      "reporter_phone": mask_phone(phones.get(p.user_id)), "created_at": p.created_at})
    for r, b in bhs:
        items.append({"kind": "borehole_report", "id": str(r.id), "district": b.district,
                      "summary": f"{b.name} reported as '{r.new_status}' (currently shown: '{b.status}')",
                      "reporter_phone": mask_phone(phones.get(r.reported_by)), "created_at": r.created_at})
    for c in crs:
        items.append({"kind": "community_report", "id": str(c.id), "district": c.district,
                      "summary": c.description or c.report_type,
                      "reporter_phone": mask_phone(phones.get(c.submitter_id)), "created_at": c.created_at})

    items.sort(key=lambda x: x["created_at"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return items


def _record_review(db: Session, validator_id):
    a = db.query(ValidatorAssignment).filter(ValidatorAssignment.user_id == validator_id).first()
    if a:
        a.reports_reviewed = (a.reports_reviewed or 0) + 1
        a.last_active_at = datetime.now(timezone.utc)
        db.commit()


def _load(db: Session, kind: str, item_id):
    """-> (row, district, submitter_id, submitter_notice_text)"""
    if kind == "pest_sighting":
        row = db.query(PestSighting).filter(PestSighting.id == item_id).first()
        return row, (row.district if row else None), (row.user_id if row else None), "pest sighting"
    if kind == "borehole_report":
        row = db.query(BoreholeReport).filter(BoreholeReport.id == item_id).first()
        bh = db.query(Borehole).filter(Borehole.id == row.borehole_id).first() if row else None
        return row, (bh.district if bh else None), (row.reported_by if row else None), "borehole report"
    if kind == "community_report":
        row = db.query(CommunityReport).filter(CommunityReport.id == item_id).first()
        return row, (row.district if row else None), (row.submitter_id if row else None), "community report"
    raise NotFound(f"Unknown item kind '{kind}'")


def decide(db: Session, kind: str, item_id, validator: User, approve: bool, reason: str | None) -> None:
    row, district, submitter_id, label = _load(db, kind, item_id)
    if row is None:
        raise NotFound("Item not found")

    scope = validator_districts(db, validator)
    if scope is not None and district not in scope:
        # Same answer as "not found": don't reveal that items exist outside your district.
        raise NotFound("Item not found")
    if submitter_id is not None and str(submitter_id) == str(validator.id):
        raise Forbidden("You cannot review your own submission")
    if (row.status or "pending") != "pending":
        raise Conflict(f"Already {row.status}")

    now = datetime.now(timezone.utc)
    before = {"status": row.status}
    new_status = "approved" if approve else "rejected"
    row.status = new_status
    if kind == "pest_sighting":
        row.validated_by, row.validated_at = validator.id, now
        row.rejection_reason = None if approve else reason
    elif kind == "borehole_report":
        row.validated, row.validated_by, row.validated_at = True, validator.id, now
        row.rejection_reason = None if approve else reason
        if approve:  # the ONLY place a community report changes what everyone sees
            bh = db.query(Borehole).filter(Borehole.id == row.borehole_id).first()
            if bh:
                bh.status, bh.last_verified, bh.verified_by = row.new_status, now, validator.id
    else:
        row.reviewed_by, row.reviewed_at = validator.id, now
        row.rejection_reason = None if approve else reason

    db.commit()
    _record_review(db, validator.id)
    write_audit_log(db, str(validator.id), f"community.{'approve' if approve else 'reject'}", kind, str(item_id),
                    before=before, after={"status": new_status, "reason": reason, "district": district})

    # Tell the submitter (best effort — a failed SMS must never undo a decision).
    try:
        phone = _phones(db, {submitter_id}).get(submitter_id) if submitter_id else None
        if phone:
            msg = (f"KohwAI: your {label} was confirmed by a community validator. Thank you."
                   if approve else f"KohwAI: your {label} was not accepted. Reason: {reason}")
            send_sms([phone], msg)
    except Exception:  # noqa: BLE001
        logger.warning("Could not SMS submitter for %s %s", kind, item_id, exc_info=True)


# ── validator appointment (admin) ────────────────────────────────────────
def appoint_validator(db: Session, admin: User, phone: str, districts: list[str]) -> User:
    target = db.query(User).filter(User.phone == phone).first()
    if not target:
        raise NotFound("No registered user with that phone number")
    if "validator" not in (target.roles or []):
        target.roles = list(target.roles or []) + ["validator"]
    existing = {a.district: a for a in db.query(ValidatorAssignment).filter(ValidatorAssignment.user_id == target.id)}
    for d in districts:
        a = existing.get(d)
        if a:
            a.is_active = True
        else:
            db.add(ValidatorAssignment(user_id=target.id, district=d, assigned_by=admin.id, is_active=True))
    db.commit()
    write_audit_log(db, str(admin.id), "validator.appoint", "user", str(target.id), after={"districts": districts})
    return target


def revoke_validator(db: Session, admin: User, user_id) -> None:
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise NotFound("User not found")
    db.query(ValidatorAssignment).filter(ValidatorAssignment.user_id == target.id).update({"is_active": False})
    target.roles = [r for r in (target.roles or []) if r != "validator"]
    db.commit()
    write_audit_log(db, str(admin.id), "validator.revoke", "user", str(target.id))
