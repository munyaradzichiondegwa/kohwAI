# FastAPI router for Mvura — Water Security
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.deps import get_current_user, require_admin
from app.models.user import User
from app.modules.mvura import service
from app.utils.validation import district_query
from app.modules.mvura.schemas import BoreholeOut, BoreholeCreate, BoreholeReportRequest

router = APIRouter()


@router.get("/boreholes", response_model=list[BoreholeOut], summary="List boreholes, optionally by district")
def list_boreholes(district: Optional[str] = Depends(district_query), db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    return service.list_boreholes(db, district)


@router.post("/boreholes", response_model=BoreholeOut, summary="Register a new borehole (admin only)")
def create_borehole(body: BoreholeCreate, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    return service.to_dict(service.create_borehole(db, body.model_dump(), str(user.id)))


@router.post("/boreholes/{borehole_id}/report", summary="Report a borehole's current status")
def report_borehole(borehole_id: uuid.UUID, body: BoreholeReportRequest, db: Session = Depends(get_db),
                           user: User = Depends(get_current_user)):
    try:
        report = service.report_status(db, borehole_id, str(user.id), body.new_status, body.note)
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    return {"id": str(report.id), "status": "pending",
            "message": "Report received. It will show as unverified until a community validator confirms it."}
