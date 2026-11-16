# FastAPI router for Community & Validation
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.deps import get_current_user, require_validator, require_admin
from app.models.user import User
from app.models.community import CommunityReport, ValidatorAssignment
from app.modules.community import service
from app.modules.community.service import NotFound, Forbidden, Conflict
from app.modules.community.schemas import QueueItemOut, RejectRequest, CommunityReportCreate, AppointValidator
from app.utils.validation import district_query

router = APIRouter()


def _http(e: Exception) -> HTTPException:
    code = {NotFound: 404, Forbidden: 403, Conflict: 409}.get(type(e), 400)
    return HTTPException(code, str(e))


@router.get("/validators", summary="List validator/admin accounts and their districts (admin only)")
def list_validators(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    users = db.query(User).filter(User.roles.overlap(["validator", "admin"])).all()
    assignments = db.query(ValidatorAssignment).filter(ValidatorAssignment.is_active.is_(True)).all()
    by_user: dict = {}
    for a in assignments:
        by_user.setdefault(a.user_id, []).append(a)
    out = []
    for u in users:
        mine = by_user.get(u.id, [])
        last = max((a.last_active_at for a in mine if a.last_active_at), default=None)
        out.append({
            "id": str(u.id), "phone": u.phone, "district": u.district, "roles": u.roles,
            "districts": sorted(a.district for a in mine),
            "reports_reviewed": sum(a.reports_reviewed or 0 for a in mine),
            "last_active_at": last.isoformat() if last else None,
        })
    return out


@router.post("/validators", summary="Appoint a validator for one or more districts (admin only)")
def appoint(body: AppointValidator, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    phone = body.phone if body.phone.startswith("+") else "+263" + body.phone[1:]
    try:
        u = service.appoint_validator(db, admin, phone, body.districts)
    except NotFound as e:
        raise _http(e)
    return {"id": str(u.id), "roles": u.roles, "districts": body.districts}


@router.delete("/validators/{user_id}", summary="Revoke validator access (admin only)")
def revoke(user_id: uuid.UUID, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    try:
        service.revoke_validator(db, admin, user_id)
    except NotFound as e:
        raise _http(e)
    return {"status": "revoked"}


@router.get("/queue", response_model=list[QueueItemOut], summary="Pending items in YOUR districts")
def get_queue(district: Optional[str] = Depends(district_query), db: Session = Depends(get_db),
              validator: User = Depends(require_validator)):
    return service.get_queue(db, validator, district)


@router.post("/queue/{kind}/{item_id}/approve", summary="Approve a pending report")
def approve(kind: str, item_id: uuid.UUID, db: Session = Depends(get_db), validator: User = Depends(require_validator)):
    try:
        service.decide(db, kind, item_id, validator, approve=True, reason=None)
    except (NotFound, Forbidden, Conflict) as e:
        raise _http(e)
    return {"status": "approved"}


@router.post("/queue/{kind}/{item_id}/reject", summary="Reject a pending report (reason required)")
def reject(kind: str, item_id: uuid.UUID, body: RejectRequest, db: Session = Depends(get_db),
           validator: User = Depends(require_validator)):
    try:
        service.decide(db, kind, item_id, validator, approve=False, reason=body.reason)
    except (NotFound, Forbidden, Conflict) as e:
        raise _http(e)
    return {"status": "rejected"}


@router.post("/reports", summary="Submit a general community report")
def submit_report(body: CommunityReportCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    report = CommunityReport(submitter_id=user.id, status="pending", **body.model_dump())
    db.add(report)
    db.commit()
    db.refresh(report)
    return {"id": str(report.id), "status": "pending"}
