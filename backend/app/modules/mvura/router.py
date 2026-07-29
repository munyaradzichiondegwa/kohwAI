# FastAPI router for Mvura — Water Security
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.deps import get_current_user, require_admin
from app.models.user import User
from app.modules.mvura import service
from app.modules.mvura.schemas import BoreholeOut, BoreholeCreate, BoreholeReportRequest

router = APIRouter()


def _to_out(b) -> BoreholeOut:
    return BoreholeOut(id=str(b.id), name=b.name, village=b.village, district=b.district,
                        lat=b.lat, lng=b.lng, status=b.status, depth_m=b.depth_m,
                        last_verified=b.last_verified)


@router.get("/boreholes", response_model=list[BoreholeOut], summary="List boreholes, optionally by district")
async def list_boreholes(district: Optional[str] = Query(None), db: Session = Depends(get_db),
                          user: User = Depends(get_current_user)):
    return [_to_out(b) for b in service.list_boreholes(db, district)]


@router.post("/boreholes", response_model=BoreholeOut, summary="Register a new borehole (admin only)")
async def create_borehole(body: BoreholeCreate, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    return _to_out(service.create_borehole(db, body.model_dump()))


@router.post("/boreholes/{borehole_id}/report", summary="Report a borehole's current status")
async def report_borehole(borehole_id: str, body: BoreholeReportRequest, db: Session = Depends(get_db),
                           user: User = Depends(get_current_user)):
    try:
        report = service.report_status(db, borehole_id, str(user.id), body.new_status, body.note)
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    return {"id": str(report.id), "status": "recorded, pending validator confirmation"}
