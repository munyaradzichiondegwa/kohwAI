"""Business logic for Livestock Health."""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.livestock import LivestockProfile, TreatmentRecord
from app.modules.ussd.rules_engine import RulesEngine

rules = RulesEngine()

NOTIFIABLE_DISEASES = {"Foot and Mouth Disease", "Anthrax"}  # Zimbabwe Vet Services notifiable list (partial)


def diagnose(db: Session, user_id: str, animal_type_code: str, symptom_code: str,
             animal_id: Optional[str]) -> dict:
    result = rules.diagnose_livestock(symptom_code, animal_type_code)
    notifiable = result["disease"] in NOTIFIABLE_DISEASES

    if animal_id:
        animal = db.query(LivestockProfile).filter(
            LivestockProfile.id == animal_id, LivestockProfile.owner_id == user_id,
        ).first()
        if animal:
            animal.health_status = "sick" if result["disease"] != "Unknown condition" else animal.health_status
            animal.last_diagnosed = datetime.now(timezone.utc)
            db.add(TreatmentRecord(
                animal_id=animal.id, diagnosis=result["disease"], treatment=result["action"],
                treated_by="Farmer (rules-based triage)", date_treated=datetime.now(timezone.utc),
            ))
            db.commit()

    return {"disease": result["disease"], "action": result["action"], "notifiable": notifiable}


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
