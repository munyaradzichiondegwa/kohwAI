"""Business logic for parametric drought insurance.

Real, honest limitation: there is no live EcoCash merchant integration here. Enrolment and
payout *records* are real and persisted; actual money movement is not automated — a payout
is created as 'pending_manual_disbursement' and an admin records the real EcoCash reference
after sending it through their own merchant channel.

TRIGGER RULES (all must hold, evaluated on stored daily satellite readings):
  1. today is inside the policy season window (default Nov 1 – Mar 31). Outside it, the
     rainfall-deficit index is ~100 by construction and must never pay out.
  2. the district's drought_index is >= threshold on at least `min_consecutive_days`
     consecutive days ending at the latest reading, and that reading is recent (<= 4 days old).
  3. the farmer enrolled at least `INSURANCE_WAITING_DAYS` before the dry spell began
     (stops people enrolling after the drought has already started).
  4. at most ONE payout per enrolment (database-enforced), however many times we evaluate.

Licensing note (not code): paying out on this product in Zimbabwe requires a licensed
underwriter; keep the `musika_insurance_enrollment` flag OFF until that is in place.
"""
import calendar
import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.musika import InsuranceEnrollment, PayoutRecord
from app.models.satellite import SatelliteReading
from app.models.user import User
from app.utils.audit import write_audit_log
from app.utils.satellite import require_district
from app.utils.sms import send_sms

logger = logging.getLogger(__name__)
MAX_READING_AGE_DAYS = 4


class InsuranceError(Exception):
    """Business-rule rejection; `.status` is the suggested HTTP status."""
    def __init__(self, msg: str, status: int = 400):
        super().__init__(msg)
        self.status = status


def season_window(season: str) -> tuple[date, date]:
    y = int(season[:4])
    start = date(y, settings.INSURANCE_SEASON_START_MONTH, 1)
    end_year = y + 1 if settings.INSURANCE_SEASON_END_MONTH < settings.INSURANCE_SEASON_START_MONTH else y
    end = date(end_year, settings.INSURANCE_SEASON_END_MONTH,
               calendar.monthrange(end_year, settings.INSURANCE_SEASON_END_MONTH)[1])
    return start, end


def qualifying_run(db: Session, district: str, threshold: int, today: date | None = None) -> dict:
    """Longest run of consecutive qualifying days ending at the most recent stored reading."""
    today = today or date.today()
    rows = (db.query(SatelliteReading.reading_date, SatelliteReading.drought_index)
            .filter(SatelliteReading.district == district, SatelliteReading.drought_index.isnot(None),
                    SatelliteReading.reading_date <= today)
            .order_by(SatelliteReading.reading_date.desc()).limit(120).all())
    if not rows:
        return {"qualifies": False, "run_days": 0, "run_start": None, "latest": None, "latest_index": None,
                "stale": True, "reason": "no stored satellite readings"}
    latest, latest_idx = rows[0]
    stale = (today - latest).days > MAX_READING_AGE_DAYS
    run, run_start, prev = 0, None, None
    for d, idx in rows:
        if prev is not None and (prev - d).days != 1:
            break
        if idx < threshold:
            break
        run, run_start, prev = run + 1, d, d
    return {"qualifies": run >= settings.INSURANCE_MIN_CONSECUTIVE_DAYS and not stale, "run_days": run,
            "run_start": run_start, "latest": latest, "latest_index": latest_idx, "stale": stale}


# ── enrolment ────────────────────────────────────────────────────────────
def enroll(db: Session, user_id: str, district: str, season: str, ecocash_number: str | None,
           today: date | None = None) -> InsuranceEnrollment:
    today = today or date.today()
    require_district(district)
    start, end = season_window(season)
    if today > end:
        raise InsuranceError(f"Season {season} has ended — enrolment is closed.", 409)

    existing = db.query(InsuranceEnrollment).filter(
        InsuranceEnrollment.user_id == user_id, InsuranceEnrollment.season == season).first()
    if existing:
        if existing.district != district:
            raise InsuranceError("Your cover for this season is tied to the district you enrolled in. "
                                 "Contact support to change it.", 409)
        existing.ecocash_number = ecocash_number or existing.ecocash_number
        existing.is_active = True
        db.commit()
        db.refresh(existing)
        return existing

    run = qualifying_run(db, district, settings.INSURANCE_DROUGHT_THRESHOLD, today)
    if run["run_days"] >= settings.INSURANCE_MIN_CONSECUTIVE_DAYS and start <= today <= end and not run["stale"]:
        raise InsuranceError(f"Dry-spell conditions already exist in {district}; new enrolments are paused.", 409)

    enrollment = InsuranceEnrollment(user_id=user_id, district=district, season=season,
                                     ecocash_number=ecocash_number, is_active=True)
    db.add(enrollment)
    try:
        db.commit()
    except IntegrityError:           # concurrent double-submit
        db.rollback()
        raise InsuranceError("You are already enrolled for this season.", 409)
    db.refresh(enrollment)
    write_audit_log(db, user_id, "insurance.enroll", "enrollment", str(enrollment.id),
                    after={"district": district, "season": season})
    return enrollment


def get_my_enrollment(db: Session, user_id: str) -> InsuranceEnrollment | None:
    return (db.query(InsuranceEnrollment).filter(InsuranceEnrollment.user_id == user_id)
            .order_by(InsuranceEnrollment.created_at.desc()).first())


def list_my_payouts(db: Session, user_id: str) -> list[PayoutRecord]:
    return (db.query(PayoutRecord).join(InsuranceEnrollment, InsuranceEnrollment.id == PayoutRecord.enrollment_id)
            .filter(InsuranceEnrollment.user_id == user_id, PayoutRecord.status != "void_duplicate")
            .order_by(PayoutRecord.created_at.desc()).all())


# ── trigger evaluation ───────────────────────────────────────────────────
def evaluate_district_payout(db: Session, district: str, season: str, threshold: int | None = None,
                             today: date | None = None, actor_id: str | None = None) -> dict:
    """Create pending payouts for eligible enrolments if the trigger rules hold. Idempotent."""
    today = today or date.today()
    threshold = threshold if threshold is not None else settings.INSURANCE_DROUGHT_THRESHOLD
    require_district(district)
    start, end = season_window(season)
    if not (start <= today <= end):
        return {"triggered": False, "reason": f"Outside policy season {season} ({start}..{end})"}

    run = qualifying_run(db, district, threshold, today)
    info = {k: (v.isoformat() if isinstance(v, date) else v) for k, v in run.items()}
    if run["latest"] is None:
        return {"triggered": False, "reason": "No satellite data stored yet", "run": info}
    if run["stale"]:
        return {"triggered": False, "reason": f"Latest satellite reading ({run['latest']}) is stale", "run": info}
    if not run["qualifies"]:
        return {"triggered": False, "run": info,
                "reason": f"Index >= {threshold} for {run['run_days']} consecutive day(s); "
                          f"need {settings.INSURANCE_MIN_CONSECUTIVE_DAYS}"}

    cutoff = run["run_start"] - timedelta(days=settings.INSURANCE_WAITING_DAYS)
    enrollments = db.query(InsuranceEnrollment).filter(
        InsuranceEnrollment.district == district, InsuranceEnrollment.season == season,
        InsuranceEnrollment.is_active.is_(True)).all()

    created, skipped_waiting, already = [], 0, 0
    for e in enrollments:
        if e.created_at.date() > cutoff:
            skipped_waiting += 1
            continue
        payout = PayoutRecord(enrollment_id=e.id, district=district, drought_index=run["latest_index"],
                              amount_usd=e.payout_amount_usd, status="pending_manual_disbursement")
        try:
            with db.begin_nested():
                db.add(payout)
                db.flush()
        except IntegrityError:        # unique(enrollment) -> this farmer was already paid for the season
            already += 1
            continue
        created.append((payout, e))
    db.commit()

    for payout, e in created:
        write_audit_log(db, actor_id, "insurance.payout_created", "payout", str(payout.id),
                        after={"enrollment": str(e.id), "district": district, "amount_usd": float(payout.amount_usd),
                               "drought_index": run["latest_index"], "run_days": run["run_days"]})
        _notify(db, e, float(payout.amount_usd))

    return {"triggered": True, "run": info, "enrollments_matched": len(enrollments),
            "payouts_created": len(created), "already_paid": already, "skipped_waiting_period": skipped_waiting}


def _notify(db: Session, e: InsuranceEnrollment, amount: float) -> None:
    try:
        u = db.query(User).filter(User.id == e.user_id).first()
        if u:   # Truthful wording: a record exists; money is NOT claimed to have been sent.
            send_sms([u.phone], f"KohwAI: drought cover triggered in {e.district}. A payout of USD {amount:.2f} "
                                f"has been approved and will be sent to your EcoCash number. We will SMS you when sent.")
    except Exception:  # noqa: BLE001
        logger.warning("payout SMS failed", exc_info=True)


def mark_payout_sent(db: Session, payout_id, ecocash_ref: str, admin_id: str | None = None) -> PayoutRecord | None:
    payout = db.query(PayoutRecord).filter(PayoutRecord.id == payout_id).first()
    if not payout:
        return None
    if payout.status == "sent":
        raise InsuranceError("Payout is already marked as sent.", 409)
    if payout.status == "void_duplicate":
        raise InsuranceError("Voided duplicate payouts cannot be sent.", 409)
    before = {"status": payout.status, "ecocash_ref": payout.ecocash_ref}
    payout.status = "sent"
    payout.ecocash_ref = ecocash_ref
    payout.sent_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(payout)
    write_audit_log(db, admin_id, "insurance.payout_marked_sent", "payout", str(payout.id),
                    before=before, after={"status": "sent", "ecocash_ref": ecocash_ref})
    return payout
