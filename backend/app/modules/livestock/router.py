# FastAPI router for Livestock Health
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.deps import get_current_user
from app.models.user import User
from app.modules.livestock import service
from app.modules.ussd.rules_engine import LIVESTOCK_SYMPTOMS, ANIMALS
from app.modules.livestock.schemas import (
    LivestockDiagnoseRequest, LivestockDiagnoseOut, LivestockProfileCreate, LivestockProfileOut,
)

router = APIRouter()


@router.get("/reference/symptoms", summary="Symptom options for livestock triage")
async def symptoms():
    return [{"code": c, "label": full} for c, full, _short in LIVESTOCK_SYMPTOMS]


@router.get("/reference/animal-types", summary="Animal types the rules currently cover")
async def animal_types():
    return [{"code": c, "label": label} for c, label in ANIMALS]


@router.post("/diagnose", response_model=LivestockDiagnoseOut, summary="Rules-based livestock symptom triage")
def diagnose(body: LivestockDiagnoseRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        result = service.diagnose(db, str(user.id), body.animal_type_code, body.symptom_code,
                                  body.animal_id, body.district or user.district)
    except LookupError:
        raise HTTPException(404, "Animal not found")
    return LivestockDiagnoseOut(**result)


@router.post("/profiles/{animal_id}/recovered", summary="Mark one of my animals as recovered")
def recovered(animal_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not service.mark_recovered(db, str(user.id), animal_id):
        raise HTTPException(404, "Animal not found")
    return {"status": "healthy"}


@router.post("/profiles", response_model=LivestockProfileOut, summary="Register an animal")
async def create_profile(body: LivestockProfileCreate, db: Session = Depends(get_db),
                          user: User = Depends(get_current_user)):
    profile = service.create_profile(db, str(user.id), body.model_dump())
    return LivestockProfileOut(id=str(profile.id), name=profile.name, animal_type=profile.animal_type,
                                breed=profile.breed, tag_number=profile.tag_number,
                                health_status=profile.health_status, last_diagnosed=profile.last_diagnosed,
                                district=profile.district)


@router.get("/profiles", response_model=list[LivestockProfileOut], summary="List my registered animals")
async def list_profiles(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    profiles = service.list_profiles(db, str(user.id))
    return [LivestockProfileOut(id=str(p.id), name=p.name, animal_type=p.animal_type, breed=p.breed,
                                 tag_number=p.tag_number, health_status=p.health_status,
                                 last_diagnosed=p.last_diagnosed, district=p.district) for p in profiles]
