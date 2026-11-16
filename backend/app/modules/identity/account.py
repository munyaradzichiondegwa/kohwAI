"""Data-subject rights: export everything we hold about a person, and delete/anonymise their account.

Deletion design (the audit log must stay append-only and keep its user FK, and we may need to keep financial
records), so we ANONYMISE the account row instead of dropping it, and delete everything personal:
  deleted : livestock profiles + treatments, diagnoses, marketplace listings, personal insights, alert-delivery
            records, validator assignments, OTP history for the phone number
  scrubbed: phone (replaced), district, device token, PIN, 2FA secret, EcoCash number on enrolments
  kept    : audit log rows, insurance enrolment/payout rows (financial record), and community reports already
            submitted (validation history) — none of which are linked to a phone number any more
Refused while a payout is still owed, so nobody loses money by closing an account.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.alerts import AlertDelivery
from app.models.community import CommunityReport, ValidatorAssignment
from app.models.intelligence import CrossPillarInsight
from app.models.livestock import LivestockProfile, TreatmentRecord
from app.models.musika import InsuranceEnrollment, MarketListing, PayoutRecord
from app.models.mvura import BoreholeReport
from app.models.user import User, OTPLog
from app.models.zunde import DiagnosisReport, PestSighting
from app.utils.audit import write_audit_log


class DeletionBlocked(Exception): ...


def _row(obj, *cols):
    out = {}
    for c in cols:
        v = getattr(obj, c, None)
        out[c] = v.isoformat() if hasattr(v, "isoformat") else (str(v) if isinstance(v, uuid.UUID) else (float(v) if v.__class__.__name__ == "Decimal" else v))
    return out


def export_user_data(db: Session, user: User) -> dict:
    uid = user.id
    animals = db.query(LivestockProfile).filter(LivestockProfile.owner_id == uid).all()
    enrolments = db.query(InsuranceEnrollment).filter(InsuranceEnrollment.user_id == uid).all()
    user.data_export_requested_at = datetime.now(timezone.utc)
    db.commit()
    write_audit_log(db, str(uid), "account.export", "user", str(uid))
    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "profile": _row(user, "id", "phone", "language", "district", "roles", "sms_alerts", "terms_accepted_at",
                        "terms_version", "created_at"),
        "livestock": [{**_row(a, "id", "name", "animal_type", "breed", "tag_number", "district", "health_status", "created_at"),
                       "treatments": [_row(t, "diagnosis", "treatment", "date_treated") for t in
                                      db.query(TreatmentRecord).filter(TreatmentRecord.animal_id == a.id)]} for a in animals],
        "diagnoses": [_row(d, "id", "subject_type", "top_disease", "district", "created_at")
                      for d in db.query(DiagnosisReport).filter(DiagnosisReport.user_id == uid)],
        "pest_sightings": [_row(p, "id", "species", "severity", "district", "status", "created_at")
                           for p in db.query(PestSighting).filter(PestSighting.user_id == uid)],
        "borehole_reports": [_row(r, "id", "borehole_id", "new_status", "status", "note", "created_at")
                             for r in db.query(BoreholeReport).filter(BoreholeReport.reported_by == uid)],
        "community_reports": [_row(c, "id", "report_type", "district", "description", "status", "created_at")
                              for c in db.query(CommunityReport).filter(CommunityReport.submitter_id == uid)],
        "listings": [_row(l, "id", "type", "title", "quantity", "unit", "price_usd", "district", "is_active", "share_phone", "created_at")
                     for l in db.query(MarketListing).filter(MarketListing.seller_id == uid)],
        "insurance": [{**_row(e, "id", "district", "season", "ecocash_number", "payout_amount_usd", "is_active", "created_at"),
                       "payouts": [_row(p, "id", "amount_usd", "status", "ecocash_ref", "sent_at") for p in
                                   db.query(PayoutRecord).filter(PayoutRecord.enrollment_id == e.id)]} for e in enrolments],
        "alert_sms_received": db.query(AlertDelivery).filter(AlertDelivery.user_id == uid, AlertDelivery.status == "sent").count(),
    }


def delete_account(db: Session, user: User) -> None:
    uid = user.id
    owed = (db.query(PayoutRecord).join(InsuranceEnrollment, InsuranceEnrollment.id == PayoutRecord.enrollment_id)
            .filter(InsuranceEnrollment.user_id == uid, PayoutRecord.status == "pending_manual_disbursement").count())
    if owed:
        raise DeletionBlocked("You have an insurance payout waiting to be sent. Account deletion is possible once it has been paid.")

    animal_ids = [a for (a,) in db.query(LivestockProfile.id).filter(LivestockProfile.owner_id == uid)]
    if animal_ids:
        db.query(TreatmentRecord).filter(TreatmentRecord.animal_id.in_(animal_ids)).delete(synchronize_session=False)
    db.query(LivestockProfile).filter(LivestockProfile.owner_id == uid).delete(synchronize_session=False)
    db.query(DiagnosisReport).filter(DiagnosisReport.user_id == uid).delete(synchronize_session=False)
    db.query(MarketListing).filter(MarketListing.seller_id == uid).delete(synchronize_session=False)
    db.query(CrossPillarInsight).filter(CrossPillarInsight.user_id == uid).delete(synchronize_session=False)
    db.query(AlertDelivery).filter(AlertDelivery.user_id == uid).delete(synchronize_session=False)
    db.query(ValidatorAssignment).filter(ValidatorAssignment.user_id == uid).delete(synchronize_session=False)
    db.query(OTPLog).filter(OTPLog.phone == user.phone).delete(synchronize_session=False)
    db.query(InsuranceEnrollment).filter(InsuranceEnrollment.user_id == uid).update({"ecocash_number": None}, synchronize_session=False)

    user.phone = f"del-{uuid.uuid4().hex[:15]}"
    user.district = None
    user.fcm_token = None
    user.pin_hash = None
    user.totp_secret = None
    user.roles = []
    user.is_active = False
    user.sms_alerts = False
    db.commit()
    write_audit_log(db, str(uid), "account.deleted", "user", str(uid))
