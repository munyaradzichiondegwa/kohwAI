"""Business logic for Platform Settings — feature flags & OTA config.
Defaults are seeded lazily on first read so the admin panel always has
something sensible to show, without requiring a separate seed step."""
from sqlalchemy.orm import Session
from app.models.settings import PlatformSetting
from app.utils.audit import write_audit_log

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
    # ON CONFLICT DO NOTHING: two concurrent first requests must not race into a unique violation.
    from sqlalchemy.dialects.postgresql import insert
    existing = {s.key for s in db.query(PlatformSetting.key).all()}
    missing = [{"key": k, "value": v} for k, v in DEFAULTS.items() if k not in existing]
    if missing:
        db.execute(insert(PlatformSetting).values(missing).on_conflict_do_nothing(index_elements=["key"]))
        db.commit()


def flag_enabled(db: Session, name: str) -> bool:
    """Read a feature flag (defaults apply when unset). Unknown flags are OFF."""
    row = get_setting(db, "feature_flags")
    flags = (row.value if row else None) or DEFAULTS["feature_flags"]
    return bool(flags.get(name, False))


def list_settings(db: Session) -> list[PlatformSetting]:
    _ensure_defaults(db)
    return db.query(PlatformSetting).order_by(PlatformSetting.key).all()


def get_setting(db: Session, key: str) -> PlatformSetting | None:
    _ensure_defaults(db)
    return db.query(PlatformSetting).filter(PlatformSetting.key == key).first()


def upsert_setting(db: Session, key: str, value, description: str | None, updated_by: str) -> PlatformSetting:
    setting = db.query(PlatformSetting).filter(PlatformSetting.key == key).first()
    before = setting.value if setting else None
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
    write_audit_log(db, updated_by, "settings.update", "platform_setting", key, before=before, after=value)
    return setting
