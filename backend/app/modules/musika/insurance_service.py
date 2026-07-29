"""Business logic for parametric drought insurance.

Real, honest limitation: there is no live EcoCash merchant integration here.
Enrollment and payout *records* are entirely real and persisted; the actual
movement of money is not automated — a payout is created with
status='pending_manual_disbursement' and an admin must record the real-world
EcoCash transaction reference once they've sent it through their own merchant
channel outside this app. Pretending otherwise would misrepresent what a
payout record actually does today.
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.musika import InsuranceEnrollment, PayoutRecord
from app.utils.risk import compute_drought_index


def enroll(db: Session, user_id: str, district: str, season: str, ecocash_number: str | None) -> InsuranceEnrollment:
    existing = db.query(InsuranceEnrollment).filter(InsuranceEnrollment.user_id == user_id).first()
    if existing:
        existing.district = district
        existing.season = season
        existing.ecocash_number = ecocash_number
        existing.is_active = True
        db.commit()
        db.refresh(existing)
        return existing

    enrollment = InsuranceEnrollment(
        user_id=user_id, district=district, season=season,
        ecocash_number=ecocash_number, is_active=True,
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment


def get_my_enrollment(db: Session, user_id: str) -> InsuranceEnrollment | None:
    return db.query(InsuranceEnrollment).filter(InsuranceEnrollment.user_id == user_id).first()


def list_my_payouts(db: Session, user_id: str) -> list[PayoutRecord]:
    enrollment = get_my_enrollment(db, user_id)
    if not enrollment:
        return []
    return (
        db.query(PayoutRecord)
        .filter(PayoutRecord.enrollment_id == enrollment.id)
        .order_by(PayoutRecord.created_at.desc())
        .all()
    )


def evaluate_district_payout(db: Session, district: str, season: str, threshold: int) -> dict:
    """Check the real drought index for a district and create pending payout
    records for every active enrollment there if it clears the threshold.
    This does NOT send any money — see module docstring."""
    risk = compute_drought_index(district)
    if risk["drought_index"] is None:
        return {"triggered": False, "reason": "No satellite data available", "risk": risk}

    if risk["drought_index"] < threshold:
        return {"triggered": False, "reason": "Below threshold", "risk": risk}

    enrollments = db.query(InsuranceEnrollment).filter(
        InsuranceEnrollment.district == district,
        InsuranceEnrollment.season == season,
        InsuranceEnrollment.is_active.is_(True),
    ).all()

    created = []
    for e in enrollments:
        already = db.query(PayoutRecord).filter(
            PayoutRecord.enrollment_id == e.id, PayoutRecord.drought_index == risk["drought_index"],
        ).first()
        if already:
            continue
        payout = PayoutRecord(
            enrollment_id=e.id, district=district, drought_index=risk["drought_index"],
            amount_usd=e.payout_amount_usd, status="pending_manual_disbursement",
        )
        db.add(payout)
        created.append(payout)
    db.commit()

    return {
        "triggered": True, "risk": risk, "enrollments_matched": len(enrollments),
        "payouts_created": len(created),
    }


def mark_payout_sent(db: Session, payout_id: str, ecocash_ref: str) -> PayoutRecord | None:
    payout = db.query(PayoutRecord).filter(PayoutRecord.id == payout_id).first()
    if not payout:
        return None
    payout.status = "sent"
    payout.ecocash_ref = ecocash_ref
    payout.sent_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(payout)
    return payout
