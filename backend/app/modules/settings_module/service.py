"""Business logic for Platform Settings — feature flags & OTA config.
Defaults are seeded lazily on first read so the admin panel always has
something sensible to show, without requiring a separate seed step."""
from sqlalchemy.orm import Session
from app.models.settings import PlatformSetting

DEFAULTS = {
    "feature_flags": {
        "musika_insurance_enrollment": False,  # requires EcoCash merchant credentials — off until configured
        "livestock_ai_photo_diagnosis": False,  # requires a trained on-device model — off until shipped
        "ussd_gateway": True,
    },
    "min_app_version": {"web": "1.0.0"},
    "maintenance_mode": {"enabled": False, "message": ""},
}


def _ensure_defaults(db: Session):
    existing = {s.key for s in db.query(PlatformSetting.key).all()}
    for key, value in DEFAULTS.items():
        if key not in existing:
            db.add(PlatformSetting(key=key, value=value))
    db.commit()


def list_settings(db: Session) -> list[PlatformSetting]:
    _ensure_defaults(db)
    return db.query(PlatformSetting).order_by(PlatformSetting.key).all()


def get_setting(db: Session, key: str) -> PlatformSetting | None:
    _ensure_defaults(db)
    return db.query(PlatformSetting).filter(PlatformSetting.key == key).first()


def upsert_setting(db: Session, key: str, value, description: str | None, updated_by: str) -> PlatformSetting:
    setting = db.query(PlatformSetting).filter(PlatformSetting.key == key).first()
    if setting:
        setting.value = value
        setting.updated_by = updated_by
        if description is not None:
            setting.description = description
    else:
        setting = PlatformSetting(key=key, value=value, description=description, updated_by=updated_by)
        db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting
