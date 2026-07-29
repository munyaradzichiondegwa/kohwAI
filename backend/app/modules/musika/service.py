"""Business logic for Musika — Resilient Marketplace."""
from typing import Optional

from sqlalchemy.orm import Session

from app.models.musika import MarketListing
from app.models.user import User


def list_listings(db: Session, listing_type: Optional[str] = None, district: Optional[str] = None):
    q = db.query(MarketListing).filter(MarketListing.is_active.is_(True))
    if listing_type:
        q = q.filter(MarketListing.type == listing_type)
    if district:
        q = q.filter(MarketListing.district == district)
    return q.order_by(MarketListing.created_at.desc()).limit(100).all()


def create_listing(db: Session, seller_id: str, payload: dict) -> MarketListing:
    listing = MarketListing(seller_id=seller_id, is_active=True, **payload)
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


def deactivate_listing(db: Session, listing_id: str, seller_id: str) -> bool:
    listing = db.query(MarketListing).filter(
        MarketListing.id == listing_id, MarketListing.seller_id == seller_id,
    ).first()
    if not listing:
        return False
    listing.is_active = False
    db.commit()
    return True


def seller_phone_for(db: Session, seller_id) -> Optional[str]:
    if not seller_id:
        return None
    user = db.query(User).filter(User.id == seller_id).first()
    return user.phone if user else None
