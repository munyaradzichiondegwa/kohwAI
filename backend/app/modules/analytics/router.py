# FastAPI router for Analytics
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.deps import require_admin
from app.models.user import User
from app.modules.analytics import service
from app.modules.analytics.schemas import OverviewOut

router = APIRouter()


@router.get("/overview", response_model=OverviewOut, summary="Admin dashboard overview (real DB counts)")
async def overview(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return service.get_overview(db)
