# FastAPI router for Platform Settings
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.deps import get_current_user, require_admin
from app.models.user import User
from app.modules.settings_module import service
from app.modules.settings_module.schemas import SettingOut, SettingUpsert

router = APIRouter()


@router.get("", response_model=list[SettingOut], summary="List all platform settings (any authenticated user — flags are read by clients to gate features)")
async def list_settings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [SettingOut(key=s.key, value=s.value, description=s.description) for s in service.list_settings(db)]


@router.put("/{key}", response_model=SettingOut, summary="Update a setting (admin only)")
async def upsert_setting(key: str, body: SettingUpsert, db: Session = Depends(get_db),
                          admin: User = Depends(require_admin)):
    setting = service.upsert_setting(db, key, body.value, body.description, str(admin.id))
    return SettingOut(key=setting.key, value=setting.value, description=setting.description)
