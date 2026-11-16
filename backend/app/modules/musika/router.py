# FastAPI router for Musika — Resilient Marketplace
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.deps import get_current_user, require_admin
from app.models.user import User
from app.modules.musika import service, insurance_service
from app.modules.musika.insurance_service import InsuranceError
from app.modules.settings_module.service import flag_enabled
from app.utils.validation import district_query
from app.modules.musika.schemas import ListingCreate, ListingOut
from app.modules.musika.insurance_schemas import (
    EnrollmentRequest, EnrollmentOut, PayoutOut, MarkSentRequest, EvaluatePayoutRequest,
)

router = APIRouter()


def _listing_out(l, phones: dict, viewer: User) -> ListingOut:
    return ListingOut(
        id=str(l.id), type=l.type, title=l.title, description=l.description,
        quantity=float(l.quantity), unit=l.unit, price_usd=float(l.price_usd), district=l.district,
        seller_phone=phones.get(l.seller_id) if l.share_phone else None,
        is_mine=(l.seller_id == viewer.id), is_active=l.is_active, expires_at=l.expires_at)


@router.get("/listings", response_model=list[ListingOut], summary="Browse marketplace listings")
def list_listings(type: Optional[str] = Query(None, pattern="^(seed|produce|livestock|input)$"),
                  district: Optional[str] = Depends(district_query),
                  limit: int = Query(100, ge=1, le=200), offset: int = Query(0, ge=0),
                  db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    listings = service.list_listings(db, type, district, limit, offset)
    phones = service.phones_for(db, listings)
    return [_listing_out(l, phones, user) for l in listings]


@router.post("/listings", response_model=ListingOut, summary="Create a marketplace listing")
def create_listing(body: ListingCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    listing = service.create_listing(db, str(user.id), body.model_dump())
    return _listing_out(listing, {user.id: user.phone}, user)


@router.delete("/listings/{listing_id}", summary="Deactivate my listing (e.g. once sold)")
def deactivate_listing(listing_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not service.deactivate_listing(db, listing_id, str(user.id)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Listing not found or not yours")
    return {"status": "deactivated"}


# ─── Parametric drought insurance ────────────────────────────────────────
# Real limitation, stated plainly: enrollment and payout records are fully
# real and persisted, but there is no live EcoCash integration, so payouts
# are created as 'pending_manual_disbursement' rather than actually sent.

@router.post("/insurance/enroll", response_model=EnrollmentOut, summary="Enroll in parametric drought insurance")
def enroll(body: EnrollmentRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not flag_enabled(db, "musika_insurance_enrollment"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insurance enrolment is not open yet.")
    try:
        e = insurance_service.enroll(db, str(user.id), body.district, body.season, body.ecocash_number)
    except InsuranceError as err:
        raise HTTPException(err.status, str(err))
    return _enrollment_out(e)


def _enrollment_out(e) -> EnrollmentOut:
    return EnrollmentOut(id=str(e.id), district=e.district, season=e.season,
                         payout_amount_usd=float(e.payout_amount_usd), is_active=e.is_active,
                         ecocash_number=e.ecocash_number)


@router.get("/insurance/my-enrollment", summary="My most recent enrollment, if any")
def my_enrollment(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    e = insurance_service.get_my_enrollment(db, str(user.id))
    return _enrollment_out(e) if e else None


@router.get("/insurance/my-payouts", response_model=list[PayoutOut], summary="My payout history")
def my_payouts(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    payouts = insurance_service.list_my_payouts(db, str(user.id))
    return [PayoutOut(id=str(p.id), district=p.district, drought_index=p.drought_index,
                      amount_usd=float(p.amount_usd), status=p.status,
                      ecocash_ref=p.ecocash_ref, sent_at=p.sent_at) for p in payouts]


@router.post("/insurance/evaluate-payout", summary="Apply the trigger rules to a district now and create pending payouts (admin)")
def evaluate_payout(body: EvaluatePayoutRequest, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return insurance_service.evaluate_district_payout(db, body.district, body.season,
                                                      body.drought_index_threshold, actor_id=str(admin.id))


@router.post("/insurance/payouts/{payout_id}/mark-sent", summary="Record that a payout was actually sent via EcoCash out-of-band (admin)")
def mark_sent(payout_id: uuid.UUID, body: MarkSentRequest, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    try:
        payout = insurance_service.mark_payout_sent(db, payout_id, body.ecocash_ref, str(admin.id))
    except InsuranceError as err:
        raise HTTPException(err.status, str(err))
    if not payout:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payout not found")
    return {"status": "recorded as sent"}
