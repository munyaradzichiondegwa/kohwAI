# Pydantic schemas for Identity & Access
from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
import re

PHONE_RE = re.compile(r"^\+2637\d{8}$|^07\d{8}$")


def normalise_phone(v: str) -> str:
    v = v.strip().replace(" ", "")
    if not PHONE_RE.match(v):
        raise ValueError("Enter a valid Zimbabwean mobile number, e.g. 0771234567 or +263771234567")
    if v.startswith("07"):
        v = "+263" + v[1:]
    return v


class OTPRequest(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return normalise_phone(v)


class OTPVerify(BaseModel):
    phone: str
    otp: str
    language: Optional[str] = "en"
    district: Optional[str] = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return normalise_phone(v)


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: str
    phone: str
    language: str
    district: Optional[str] = None
    roles: List[str] = []
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class UserUpdate(BaseModel):
    language: Optional[str] = None
    district: Optional[str] = None
    fcm_token: Optional[str] = None
