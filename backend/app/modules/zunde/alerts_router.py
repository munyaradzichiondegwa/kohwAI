"""Shared alerts endpoint used by AlertCarousel and WebSocket clients."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.deps import get_current_user, require_admin
from app.models.alerts import Alert
from app.models.user import User
from app.utils.audit import write_audit_log
from app.utils.validation import District

router = APIRouter()


@router.get("/active", summary="Active alerts for the current user's district")
async def get_active_alerts(
    pillar: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return active, non-expired alerts for a district, optionally filtered by pillar.
    Falls back to the current user's registered district if none is supplied."""
    target_district = district or user.district
    q = db.query(Alert).filter(
        Alert.is_active.is_(True),
        or_(Alert.expires_at.is_(None), Alert.expires_at > datetime.now(timezone.utc)),
    )
    if target_district:
        q = q.filter(Alert.district == target_district)
    if pillar:
        q = q.filter(Alert.pillar == pillar)
    alerts = q.order_by(Alert.created_at.desc()).limit(20).all()
    return [
        {
            "id": str(a.id), "type": a.type, "severity": a.severity, "title": a.title,
            "body": a.body, "pillar": a.pillar, "district": a.district,
            "createdAt": a.created_at.isoformat() if a.created_at else None,
        }
        for a in alerts
    ]


class AlertCreate(BaseModel):
    pillar: str = Field(..., pattern="^(zunde|mvura|simba|musika|livestock|community)$")
    type: str = Field(..., min_length=2, max_length=50)
    severity: str = Field(..., pattern="^(green|amber|red|darkRed|blue)$")
    title: str = Field(..., min_length=3, max_length=300)
    body: str = Field(..., min_length=3, max_length=2000)
    district: District
    expires_at: Optional[datetime] = None
    extra_data: Optional[dict] = None


@router.post("", summary="Create an alert (admin only)")
@router.post("/", include_in_schema=False)      # same route with a trailing slash: no 307 redirect on POST
def create_alert(body: AlertCreate, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    alert = Alert(**body.model_dump())
    db.add(alert)
    db.commit()
    db.refresh(alert)
    write_audit_log(db, str(user.id), "alert.create", "alert", str(alert.id),
                    after={"severity": body.severity, "district": body.district, "title": body.title})
    return {"id": str(alert.id)}
