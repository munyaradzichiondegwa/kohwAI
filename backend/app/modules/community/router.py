# FastAPI router for Community & Validation
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.deps import get_current_user, require_validator, require_admin
from app.models.user import User
from app.models.community import CommunityReport, ValidatorAssignment
from app.modules.community import service
from app.modules.community.schemas import QueueItemOut, RejectRequest, CommunityReportCreate

router = APIRouter()


@router.get("/validators", summary="List validator/admin accounts (admin only)")
async def list_validators(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    users = db.query(User).filter(User.roles.overlap(["validator", "admin"])).all()
    out = []
    for u in users:
        assignment = db.query(ValidatorAssignment).filter(ValidatorAssignment.user_id == u.id).first()
        out.append({
            "id": str(u.id), "phone": u.phone, "district": u.district, "roles": u.roles,
            "reports_reviewed": assignment.reports_reviewed if assignment else 0,
            "last_active_at": assignment.last_active_at.isoformat() if assignment and assignment.last_active_at else None,
        })
    return out


@router.get("/queue", response_model=list[QueueItemOut], summary="Pending items awaiting validation")
async def get_queue(district: Optional[str] = Query(None), db: Session = Depends(get_db),
                     validator: User = Depends(require_validator)):
    return service.get_queue(db, district)


@router.post("/queue/{kind}/{item_id}/approve", summary="Approve a pending report")
async def approve(kind: str, item_id: str, db: Session = Depends(get_db),
                   validator: User = Depends(require_validator)):
    ok = service.decide(db, kind, item_id, str(validator.id), approve=True, reason=None)
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    return {"status": "approved"}


@router.post("/queue/{kind}/{item_id}/reject", summary="Reject a pending report")
async def reject(kind: str, item_id: str, body: RejectRequest, db: Session = Depends(get_db),
                  validator: User = Depends(require_validator)):
    ok = service.decide(db, kind, item_id, str(validator.id), approve=False, reason=body.reason)
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    return {"status": "rejected"}


@router.post("/reports", summary="Submit a general community report")
async def submit_report(body: CommunityReportCreate, db: Session = Depends(get_db),
                         user: User = Depends(get_current_user)):
    report = CommunityReport(submitter_id=user.id, status="pending", **body.model_dump())
    db.add(report)
    db.commit()
    db.refresh(report)
    return {"id": str(report.id), "status": "pending"}
