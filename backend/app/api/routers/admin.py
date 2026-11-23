"""Administrator endpoints: user management, aggregate statistics, feedback review, audit log, model status."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.api.routers.dashboard import DAYS, daily_counts
from app.api.routers.feedback import feedback_out
from app.core.errors import APIError
from app.db.session import get_db
from app.models import AnalysisResult, AuditLog, ModelVersion, User, UserFeedback
from app.schemas.analysis import AdminUserUpdate, FeedbackOut, FeedbackReview
from app.schemas.user import UserOut
from app.services import accounts
from app.services.registry import list_models
from app.utils.audit import audit

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/stats", summary="System-wide statistics (counts only, no user content)")
def stats(db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=DAYS)
    dates = [d for (d,) in db.query(AnalysisResult.created_at).filter(AnalysisResult.created_at >= since).all()]
    return {
        "users": {
            "total": db.query(func.count(User.id)).scalar(),
            "active": db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar(),
            "admins": db.query(func.count(User.id)).filter(User.role == "admin").scalar(),
            "new_last_7_days": db.query(func.count(User.id)).filter(User.created_at >= now - timedelta(days=7)).scalar(),
        },
        "analyses": {
            "total": db.query(func.count(AnalysisResult.id)).scalar(),
            "by_type": dict(db.query(AnalysisResult.analysis_type, func.count()).group_by(AnalysisResult.analysis_type).all()),
            "by_verdict": dict(db.query(AnalysisResult.verdict, func.count()).group_by(AnalysisResult.verdict).all()),
            "daily": daily_counts(dates),
        },
        "feedback": dict(db.query(UserFeedback.status, func.count()).group_by(UserFeedback.status).all()),
        "models": list_models(),
    }


@router.get("/users", summary="List users")
def list_users(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), q: str | None = Query(None, max_length=100),
               db: Session = Depends(get_db)):
    query = db.query(User)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(User.email.ilike(like) | User.username.ilike(like) | User.full_name.ilike(like))
    total = query.count()
    rows = query.order_by(User.id).offset((page - 1) * page_size).limit(page_size).all()
    counts = dict(db.query(AnalysisResult.user_id, func.count()).group_by(AnalysisResult.user_id).all())
    items = [{**accounts.user_out(u).model_dump(mode="json"), "analysis_count": counts.get(u.id, 0)} for u in rows]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.patch("/users/{user_id}", response_model=UserOut, summary="Change a user's role or enable/disable the account")
def update_user(user_id: int, body: AdminUserUpdate, request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    target = db.get(User, user_id)
    if target is None:
        raise APIError(404, "NOT_FOUND", "User not found.")
    if target.id == admin.id and (body.role == "user" or body.is_active is False):
        raise APIError(400, "SELF_LOCKOUT", "You cannot remove your own administrator access or disable your own account.")
    changes: dict = {}
    if body.role is not None and body.role != target.role:
        target.role = body.role
        changes["role"] = body.role
    if body.is_active is not None and body.is_active != target.is_active:
        target.is_active = body.is_active
        changes["is_active"] = body.is_active
    db.commit()
    audit(db, request, admin, "admin.update_user", "user", target.id, changes or None)
    return accounts.user_out(target)


@router.get("/feedback", response_model=list[FeedbackOut], summary="All feedback")
def all_feedback(status: str | None = Query(None, pattern="^(new|reviewed|dismissed)$"), db: Session = Depends(get_db)):
    q = db.query(UserFeedback, User.username).join(User, User.id == UserFeedback.user_id, isouter=True)
    if status:
        q = q.filter(UserFeedback.status == status)
    return [feedback_out(f, name) for f, name in q.order_by(UserFeedback.created_at.desc()).limit(200).all()]


@router.patch("/feedback/{feedback_id}", response_model=FeedbackOut, summary="Mark feedback as reviewed or dismissed")
def review_feedback(feedback_id: int, body: FeedbackReview, request: Request, admin: User = Depends(require_admin),
                    db: Session = Depends(get_db)):
    row = db.get(UserFeedback, feedback_id)
    if row is None:
        raise APIError(404, "NOT_FOUND", "Feedback not found.")
    row.status = body.status
    row.reviewed_by = admin.id if body.status != "new" else None
    row.reviewed_at = datetime.now(timezone.utc) if body.status != "new" else None
    db.commit()
    audit(db, request, admin, "admin.review_feedback", "feedback", row.id, {"status": body.status})
    author = db.get(User, row.user_id)
    return feedback_out(row, author.username if author else None)


@router.get("/audit-logs", summary="Audit log")
def audit_logs(page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), action: str | None = Query(None, max_length=60),
               db: Session = Depends(get_db)):
    q = db.query(AuditLog, User.username).join(User, User.id == AuditLog.user_id, isouter=True)
    if action:
        q = q.filter(AuditLog.action == action)
    total = q.count()
    rows = q.order_by(AuditLog.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = [{"id": a.id, "created_at": a.created_at, "user": name, "action": a.action, "entity": a.entity,
              "entity_id": a.entity_id, "ip_address": a.ip_address, "detail": a.detail} for a, name in rows]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/models", summary="Model registry with database records")
def models(db: Session = Depends(get_db)):
    rows = db.query(ModelVersion).order_by(ModelVersion.id).all()
    return {"registry": list_models(),
            "database": [{"id": m.id, "module": m.module, "name": m.name, "version": m.version, "status": m.status,
                          "is_active": m.is_active, "created_at": m.created_at} for m in rows]}
