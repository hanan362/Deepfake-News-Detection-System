"""Audit logging helper."""
from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from app.models import AuditLog, User


def audit(db: Session, request: Request | None, user: User | None, action: str, entity: str | None = None,
          entity_id: object | None = None, detail: dict | None = None) -> None:
    ip = request.client.host if request is not None and request.client else None
    db.add(AuditLog(user_id=user.id if user else None, action=action, entity=entity,
                    entity_id=str(entity_id) if entity_id is not None else None, ip_address=ip, detail=detail))
    db.commit()
