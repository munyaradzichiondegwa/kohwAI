"""Business logic for Livestock Health."""
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models.livestock import LivestockProfile, TreatmentRecord
from app.models.zunde import DiagnosisReport
from app.modules.ussd.rules_engine import RulesEngine
from app.utils.audit import write_audit_log

rules = RulesEngine()


def diagnose(db: Session, user_id: str, animal_type_code: str, symptom_code: str,
             animal_id=None, district: Optional[str] = None) -> dict:
    """Rules-based triage. The result is ALWAYS persisted as a DiagnosisReport (it was never
    saved before, so outbreak maps / notifiable reporting / analytics had no data)."""
    result = rules.diagnose_livestock(symptom_code, animal_type_code)
    notifiable = bool(result.get("notifiable"))
    animal = None
    if animal_id:
        animal = db.query(LivestockProfile).filter(
            LivestockProfile.id == animal_id, LivestockProfile.owner_id == user_id).first()
        if animal is None:
            raise LookupError("Animal not found")      # not yours / doesn't exist -> 404, not a silent skip

    report = DiagnosisReport(
        user_id=user_id, subject_type="livestock",
        animal_type=(animal.animal_type if animal else animal_type_code),
        district=district or (animal.district if animal else None),
        top_disease=result["disease"],
        top3_json={"disease": result["disease"], "action": result["action"], "notifiable": notifiable,
                   "symptom_code": symptom_code, "animal_type_code": animal_type_code, "known": result["known"]},
        synced=True)
    db.add(report)

    if animal:
        if result["known"]:
            animal.health_status = "sick"
        animal.last_diagnosed = datetime.now(timezone.utc)
        db.add(TreatmentRecord(animal_id=animal.id, diagnosis=result["disease"], treatment=result["action"],
                               treated_by="Farmer (rules-based triage)", date_treated=datetime.now(timezone.utc)))
    db.commit()
    db.refresh(report)

    if notifiable:
        write_audit_log(db, user_id, "livestock.notifiable_suspected", "diagnosis", str(report.id),
                        after={"disease": result["disease"], "district": report.district})
    return {"id": str(report.id), "disease": result["disease"], "action": result["action"],
            "notifiable": notifiable, "known": result["known"]}


def mark_recovered(db: Session, user_id: str, animal_id) -> bool:
    animal = db.query(LivestockProfile).filter(
        LivestockProfile.id == animal_id, LivestockProfile.owner_id == user_id).first()
    if not animal:
        return False
    before = animal.health_status
    animal.health_status = "healthy"
    db.commit()
    write_audit_log(db, user_id, "livestock.recovered", "livestock", str(animal.id), before=before, after="healthy")
    return True


def create_profile(db: Session, owner_id: str, payload: dict) -> LivestockProfile:
    profile = LivestockProfile(owner_id=owner_id, **payload)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def list_profiles(db: Session, owner_id: str):
    return db.query(LivestockProfile).filter(
        LivestockProfile.owner_id == owner_id, LivestockProfile.is_active.is_(True),
    ).order_by(LivestockProfile.name).all()
