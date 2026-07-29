# FastAPI router for Cross-Pillar Intelligence Engine
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.deps import get_current_user, require_admin
from app.models.user import User
from app.modules.intelligence import service
from app.modules.intelligence.schemas import InsightOut, DistrictEvaluateRequest

router = APIRouter()


@router.get("/insights", response_model=list[InsightOut], summary="My cross-pillar insights (computed fresh, then listed)")
async def my_insights(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    service.evaluate_for_user(db, user)  # re-evaluate on read so this reflects the latest data
    insights = service.list_insights(db, user)
    return [InsightOut(id=str(i.id), district=i.district, source_pillar=i.source_pillar,
                        target_pillar=i.target_pillar, insight_type=i.insight_type,
                        severity=i.severity, message=i.message, created_at=i.created_at) for i in insights]


@router.post("/insights/{insight_id}/dismiss", summary="Dismiss an insight")
async def dismiss(insight_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ok = service.dismiss(db, insight_id, user)
    return {"dismissed": ok}


@router.post("/evaluate/district", summary="Run district-wide rules (pest outbreak, rains onset) — admin/ops trigger, intended to be called by a scheduled job")
async def evaluate_district(body: DistrictEvaluateRequest, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    pest = service.evaluate_pest_outbreak(db, body.district)
    rains = service.evaluate_rains_onset(db, body.district)
    return {
        "pest_outbreak_insight": pest.id.__str__() if pest else None,
        "rains_onset_insight": rains.id.__str__() if rains else None,
    }
