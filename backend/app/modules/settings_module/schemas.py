# Pydantic schemas for Platform Settings
from pydantic import BaseModel
from typing import Any, Optional


class SettingOut(BaseModel):
    key: str
    value: Any
    description: Optional[str] = None


class SettingUpsert(BaseModel):
    value: Any
    description: Optional[str] = None
