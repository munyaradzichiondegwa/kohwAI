# FastAPI router for Identity & Access
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.deps import get_current_user
from app.models.user import User
from app.modules.identity import service
from app.modules.identity.schemas import (
    OTPRequest, OTPVerify, RefreshRequest, TokenResponse, UserOut, UserUpdate,
)

router = APIRouter()


@router.post("/otp/request", summary="Request a login/registration OTP")
async def otp_request(body: OTPRequest, request: Request, db: Session = Depends(get_db)):
    return service.request_otp(db, body.phone, ip=request.client.host if request.client else "")


@router.post("/otp/verify", response_model=TokenResponse, summary="Verify OTP and receive tokens")
async def otp_verify(body: OTPVerify, db: Session = Depends(get_db)):
    user, access, refresh = service.verify_otp(db, body.phone, body.otp, body.language, body.district)
    return TokenResponse(
        access_token=access, refresh_token=refresh,
        user=UserOut(id=str(user.id), phone=user.phone, language=user.language,
                     district=user.district, roles=user.roles, created_at=user.created_at),
    )


@router.post("/refresh", summary="Exchange a refresh token for a new access token")
async def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    return {"access_token": service.refresh_access_token(db, body.refresh_token), "token_type": "bearer"}


@router.get("/me", response_model=UserOut, summary="Get the current user's profile")
async def me(user: User = Depends(get_current_user)):
    return UserOut(id=str(user.id), phone=user.phone, language=user.language,
                    district=user.district, roles=user.roles, created_at=user.created_at)


@router.patch("/me", response_model=UserOut, summary="Update the current user's profile")
async def update_me(body: UserUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return UserOut(id=str(user.id), phone=user.phone, language=user.language,
                    district=user.district, roles=user.roles, created_at=user.created_at)
