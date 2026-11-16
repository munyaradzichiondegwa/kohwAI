"""Business logic for Musika — Resilient Marketplace."""
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.musika import MarketListing
from app.models.user import User
from app.modules.musika.schemas import DEFAULT_LISTING_DAYS


def list_listings(db: Session, listing_type: Optional[str] = None, district: Optional[str] = None,
                  limit: int = 100, offset: int = 0):
    now = datetime.now(timezone.utc)
    q = db.query(MarketListing).filter(
        MarketListing.is_active.is_(True),
        or_(MarketListing.expires_at.is_(None), MarketListing.expires_at > now))   # expired = gone
    if listing_type:
        q = q.filter(MarketListing.type == listing_type)
    if district:
        q = q.filter(MarketListing.district == district)
    return q.order_by(MarketListing.created_at.desc()).offset(offset).limit(limit).all()


def create_listing(db: Session, seller_id: str, payload: dict) -> MarketListing:
    if not payload.get("expires_at"):
        payload["expires_at"] = datetime.now(timezone.utc) + timedelta(days=DEFAULT_LISTING_DAYS)
    listing = MarketListing(seller_id=seller_id, is_active=True, **payload)
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


def deactivate_listing(db: Session, listing_id, seller_id: str) -> bool:
    listing = db.query(MarketListing).filter(
        MarketListing.id == listing_id, MarketListing.seller_id == seller_id,
    ).first()
    if not listing:
        return False
    listing.is_active = False
    db.commit()
    return True


def phones_for(db: Session, listings) -> dict:
    """seller_id -> phone, ONLY for sellers who opted in on that listing (one query, no N+1)."""
    ids = {l.seller_id for l in listings if l.share_phone and l.seller_id}
    if not ids:
        return {}
    return {u.id: u.phone for u in db.query(User).filter(User.id.in_(ids)).all()}
