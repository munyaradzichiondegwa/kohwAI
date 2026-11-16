# FastAPI router for Zunde — Agriculture & Early Warning
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.deps import get_current_user
from app.models.user import User
from app.modules.zunde import service
from app.modules.zunde.pests import PEST_SPECIES
from app.modules.ussd.rules_engine import CROP_SYMPTOMS, CROPS
from app.utils.validation import required_district
from app.modules.zunde.schemas import (
    CropDiagnoseRequest, DiagnosisOut, PestSightingRequest, AdvisoryCardOut, PlantingCalendarOut,
)

router = APIRouter()


@router.get("/reference/crop-symptoms", summary="Symptom options for the crop triage form")
async def crop_symptoms():
    return [{"code": c, "label": full} for c, full, _short in CROP_SYMPTOMS]


@router.get("/reference/crop-types", summary="Crop types the rules currently cover")
async def crop_types():
    return [{"code": c, "label": label} for c, label in CROPS]


@router.get("/reference/pest-species", summary="Allowed pest species for sighting reports")
async def pest_species():
    return PEST_SPECIES


@router.post("/diagnose", response_model=DiagnosisOut, summary="Rules-based crop symptom triage")
def diagnose(body: CropDiagnoseRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    report = service.diagnose_crop(
        db, str(user.id), body.crop_type_code, body.symptom_code,
        body.district or user.district, body.image_s3_key,
    )
    top3 = report.top3_json or {}
    return DiagnosisOut(id=str(report.id), top_disease=report.top_disease,
                         second_disease=top3.get("disease2"), action=top3.get("action", ""),
                         known=top3.get("known", True))


@router.post("/pest-sightings", summary="Report a pest sighting for community validation")
def create_pest_sighting(body: PestSightingRequest, db: Session = Depends(get_db),
                                user: User = Depends(get_current_user)):
    sighting = service.report_pest_sighting(db, str(user.id), body.model_dump())
    return {"id": str(sighting.id), "status": sighting.status}


@router.get("/advisory-cards", response_model=list[AdvisoryCardOut], summary="Advisory content library")
async def advisory_cards(language: str = Query("en"), category: Optional[str] = Query(None),
                          db: Session = Depends(get_db)):
    cards = service.list_advisory_cards(db, language, category)
    return [AdvisoryCardOut(id=str(c.id), title=c.title, category=c.category,
                             language=c.language, content=c.content, version=c.version) for c in cards]


@router.get("/planting-calendar", response_model=PlantingCalendarOut,
            summary="Satellite rainfall snapshot + simple onset-of-rains guidance")
def planting_calendar(district: str = Depends(required_district), user: User = Depends(get_current_user)):
    # Sync def: fetch_nasa_power does a blocking HTTP call: FastAPI runs sync
    # path operations in a thread pool automatically, so this won't block the event loop.
    return service.get_planting_calendar(district)


@router.get("/risk-score", summary="Simplified real-data drought risk indicator for a district")
def risk_score(district: str = Depends(required_district), user: User = Depends(get_current_user)):
    from app.utils.risk import compute_drought_index
    return compute_drought_index(district)
