# FastAPI router for Identity & Access
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.deps import get_current_user
from app.models.user import User
from app.modules.identity import service, pin as pinlib, account
from app.modules.identity.schemas import (
    OTPRequest, OTPVerify, RefreshRequest, TokenResponse, UserOut, UserUpdate,
    ConsentRequest, PinSetRequest, DeleteAccountRequest,
)

router = APIRouter()


def _ip(request: Request) -> str:
    return request.client.host if request.client else ""


@router.post("/otp/request", summary="Request a login/registration OTP")
async def otp_request(body: OTPRequest, request: Request, db: Session = Depends(get_db)):
    return service.request_otp(db, body.phone, ip=_ip(request))


@router.post("/otp/verify", response_model=TokenResponse, summary="Verify OTP and receive tokens (new accounts must send accept_terms=true)")
def otp_verify(body: OTPVerify, request: Request, db: Session = Depends(get_db)):
    user, access, refresh = service.verify_otp(db, body.phone, body.otp, body.language, body.district,
                                               ip=_ip(request), accept_terms=body.accept_terms)
    return TokenResponse(access_token=access, refresh_token=refresh, user=service.user_out(user))


@router.post("/refresh", summary="Exchange a refresh token for a new access token")
async def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    return {"access_token": service.refresh_access_token(db, body.refresh_token), "token_type": "bearer"}


@router.get("/me", response_model=UserOut, summary="Get the current user's profile")
async def me(user: User = Depends(get_current_user)):
    return service.user_out(user)


@router.patch("/me", response_model=UserOut, summary="Update the current user's profile / preferences")
def update_me(body: UserUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return service.user_out(user)


@router.post("/consent", response_model=UserOut, summary="Accept the current Terms & Privacy Policy")
def consent(body: ConsentRequest, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not body.accept:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Consent is required to keep using KohwAI.")
    service.accept_terms(db, user, ip=_ip(request))
    db.refresh(user)
    return service.user_out(user)


@router.put("/me/pin", summary="Set or reset my 4-digit PIN (the OTP login is your proof of identity; also clears a lock-out)")
def set_pin(body: PinSetRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        pinlib.set_pin(db, user, body.pin, actor_note="web")
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))
    return {"status": "pin set"}


@router.get("/me/export", summary="Download all data we hold about me (JSON)")
def export_me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return account.export_user_data(db, user)


@router.post("/me/delete-account", summary="Permanently delete my account and personal data")
def delete_me(body: DeleteAccountRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not body.confirm:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Send {\"confirm\": true} to delete your account.")
    try:
        account.delete_account(db, user)
    except account.DeletionBlocked as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    return {"status": "deleted"}
