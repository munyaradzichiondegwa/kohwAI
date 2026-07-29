"""Shared alerts endpoint used by AlertCarousel and WebSocket clients."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.deps import get_current_user, require_admin
from app.models.alerts import Alert
from app.models.user import User

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


@router.post("", summary="Create an alert (admin/worker only)")
async def create_alert(payload: dict, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    required = {"pillar", "type", "severity", "title", "body", "district"}
    missing = required - payload.keys()
    if missing:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Missing fields: {', '.join(missing)}")
    alert = Alert(**{k: payload[k] for k in required}, extra_data=payload.get("extra_data"))
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return {"id": str(alert.id)}
