# FastAPI router for Zunde — Agriculture & Early Warning
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.deps import get_current_user
from app.models.user import User
from app.modules.zunde import service
from app.modules.zunde.schemas import (
    CropDiagnoseRequest, DiagnosisOut, PestSightingRequest, AdvisoryCardOut, PlantingCalendarOut,
)

router = APIRouter()


@router.get("/reference/crop-symptoms", summary="Symptom options for the crop triage form")
async def crop_symptoms():
    return [
        {"code": "1", "label": "Yellowing / discoloured leaves"},
        {"code": "2", "label": "Wilting despite watering"},
        {"code": "3", "label": "Chewed leaves / visible pests"},
        {"code": "4", "label": "Grey or white powdery spots"},
        {"code": "5", "label": "Stunted growth / weeds around roots"},
    ]


@router.get("/reference/crop-types", summary="Crop type options")
async def crop_types():
    return [{"code": "1", "label": "Maize"}, {"code": "2", "label": "Sorghum / Small grains"}]


@router.post("/diagnose", response_model=DiagnosisOut, summary="Rules-based crop symptom triage")
async def diagnose(body: CropDiagnoseRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    report = service.diagnose_crop(
        db, str(user.id), body.crop_type_code, body.symptom_code,
        body.district or user.district, body.image_s3_key,
    )
    top3 = report.top3_json or {}
    return DiagnosisOut(id=str(report.id), top_disease=report.top_disease,
                         second_disease=top3.get("disease2"), action=top3.get("action", ""))


@router.post("/pest-sightings", summary="Report a pest sighting for community validation")
async def create_pest_sighting(body: PestSightingRequest, db: Session = Depends(get_db),
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
def planting_calendar(district: str = Query(...), user: User = Depends(get_current_user)):
    # Sync def: fetch_nasa_power does a blocking HTTP call: FastAPI runs sync
    # path operations in a thread pool automatically, so this won't block the event loop.
    return service.get_planting_calendar(district)


@router.get("/risk-score", summary="Simplified real-data drought risk indicator for a district")
def risk_score(district: str = Query(...), user: User = Depends(get_current_user)):
    from app.utils.risk import compute_drought_index
    return compute_drought_index(district)
