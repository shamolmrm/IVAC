import uuid

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.net import client_ip
from app.modules.audit.models import AuditEvent


def audit(
    db: Session,
    action: str,
    *,
    actor_id: uuid.UUID | None = None,
    target_type: str | None = None,
    target_id: uuid.UUID | str | None = None,
    detail: dict | None = None,
    request: Request | None = None,
) -> None:
    """Add an audit event to the current transaction (committed with the caller's change)."""
    db.add(
        AuditEvent(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id else None,
            detail=detail,
            ip=client_ip(request) if request else None,
            user_agent=(request.headers.get("user-agent") or "")[:255] if request else None,
        )
    )
