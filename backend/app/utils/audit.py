"""Immutable audit log writer. Every action records: user, action, entity, before/after, IP, timestamp."""
import json
import uuid as uuid_lib
from sqlalchemy.orm import Session
from app.models.user import AuditLog


def write_audit_log(
    db: Session,
    user_id: str | None,
    action: str,
    entity_type: str,
    entity_id: str,
    before: dict | None = None,
    after: dict | None = None,
    ip: str = "",
):
    """Write an immutable audit log entry (no UPDATE/DELETE ever issued against this table)."""
    entry = AuditLog(
        user_id=uuid_lib.UUID(user_id) if user_id else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        before=json.dumps(before, default=str) if before is not None else None,
        after=json.dumps(after, default=str) if after is not None else None,
        ip_address=ip or None,
    )
    db.add(entry)
    db.commit()
