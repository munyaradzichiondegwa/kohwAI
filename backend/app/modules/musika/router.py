# FastAPI router for Musika — Resilient Marketplace
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.deps import get_current_user, require_admin
from app.models.user import User
from app.modules.musika import service, insurance_service
from app.modules.musika.schemas import ListingCreate, ListingOut
from app.modules.musika.insurance_schemas import (
    EnrollmentRequest, EnrollmentOut, PayoutOut, MarkSentRequest, EvaluatePayoutRequest,
)

router = APIRouter()


@router.get("/listings", response_model=list[ListingOut], summary="Browse marketplace listings")
async def list_listings(type: Optional[str] = Query(None), district: Optional[str] = Query(None),
                         db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    listings = service.list_listings(db, type, district)
    return [
        ListingOut(id=str(l.id), type=l.type, title=l.title, description=l.description,
                   quantity=float(l.quantity), unit=l.unit, price_usd=float(l.price_usd),
                   district=l.district, seller_phone=service.seller_phone_for(db, l.seller_id),
                   is_active=l.is_active, expires_at=l.expires_at)
        for l in listings
    ]


@router.post("/listings", response_model=ListingOut, summary="Create a marketplace listing")
async def create_listing(body: ListingCreate, db: Session = Depends(get_db),
                          user: User = Depends(get_current_user)):
    listing = service.create_listing(db, str(user.id), body.model_dump())
    return ListingOut(id=str(listing.id), type=listing.type, title=listing.title,
                       description=listing.description, quantity=float(listing.quantity),
                       unit=listing.unit, price_usd=float(listing.price_usd), district=listing.district,
                       seller_phone=user.phone, is_active=listing.is_active, expires_at=listing.expires_at)


@router.delete("/listings/{listing_id}", summary="Deactivate my listing (e.g. once sold)")
async def deactivate_listing(listing_id: str, db: Session = Depends(get_db),
                              user: User = Depends(get_current_user)):
    ok = service.deactivate_listing(db, listing_id, str(user.id))
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Listing not found or not yours")
    return {"status": "deactivated"}


# ─── Parametric drought insurance ────────────────────────────────────────
# Real limitation, stated plainly: enrollment and payout records are fully
# real and persisted, but there is no live EcoCash integration, so payouts
# are created as 'pending_manual_disbursement' rather than actually sent.

@router.post("/insurance/enroll", response_model=EnrollmentOut, summary="Enroll in parametric drought insurance")
async def enroll(body: EnrollmentRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    e = insurance_service.enroll(db, str(user.id), body.district, body.season, body.ecocash_number)
    return EnrollmentOut(id=str(e.id), district=e.district, season=e.season,
                          payout_amount_usd=float(e.payout_amount_usd), is_active=e.is_active,
                          ecocash_number=e.ecocash_number)


@router.get("/insurance/my-enrollment", summary="My current enrollment, if any")
async def my_enrollment(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    e = insurance_service.get_my_enrollment(db, str(user.id))
    if not e:
        return None
    return EnrollmentOut(id=str(e.id), district=e.district, season=e.season,
                          payout_amount_usd=float(e.payout_amount_usd), is_active=e.is_active,
                          ecocash_number=e.ecocash_number)


@router.get("/insurance/my-payouts", response_model=list[PayoutOut], summary="My payout history")
async def my_payouts(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    payouts = insurance_service.list_my_payouts(db, str(user.id))
    return [PayoutOut(id=str(p.id), district=p.district, drought_index=p.drought_index,
                       amount_usd=float(p.amount_usd), status=p.status,
                       ecocash_ref=p.ecocash_ref, sent_at=p.sent_at) for p in payouts]


@router.post("/insurance/evaluate-payout", summary="Check a district's real drought index and create pending payouts if triggered (admin)")
async def evaluate_payout(body: EvaluatePayoutRequest, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return insurance_service.evaluate_district_payout(db, body.district, body.season, body.drought_index_threshold)


@router.post("/insurance/payouts/{payout_id}/mark-sent", summary="Record that a payout was actually sent via EcoCash out-of-band (admin)")
async def mark_sent(payout_id: str, body: MarkSentRequest, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    payout = insurance_service.mark_payout_sent(db, payout_id, body.ecocash_ref)
    if not payout:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payout not found")
    return {"status": "recorded as sent"}
