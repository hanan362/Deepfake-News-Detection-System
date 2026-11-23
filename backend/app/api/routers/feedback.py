"""User feedback. It is stored for human review only and is never used automatically as a training label."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import APIError
from app.db.session import get_db
from app.models import AnalysisResult, User, UserFeedback
from app.schemas.analysis import FeedbackCreate, FeedbackOut
from app.utils.audit import audit

router = APIRouter(prefix="/feedback", tags=["feedback"])


def feedback_out(f: UserFeedback, username: str | None = None) -> FeedbackOut:
    return FeedbackOut(id=f.id, analysis_id=f.analysis_id, category=f.category, message=f.message, status=f.status,
                       created_at=f.created_at, user_id=f.user_id, username=username)


@router.post("", response_model=FeedbackOut, status_code=201, summary="Send feedback about the system or a result")
def create_feedback(body: FeedbackCreate, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.analysis_id is not None:
        owned = db.query(AnalysisResult.id).filter(AnalysisResult.id == body.analysis_id, AnalysisResult.user_id == user.id).first()
        if owned is None:
            raise APIError(404, "NOT_FOUND", "Analysis not found.")
    row = UserFeedback(user_id=user.id, analysis_id=body.analysis_id, category=body.category, message=body.message.strip())
    db.add(row)
    db.commit()
    audit(db, request, user, "feedback.create", "feedback", row.id)
    return feedback_out(row, user.username)


@router.get("", response_model=list[FeedbackOut], summary="Your feedback and its review status")
def my_feedback(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(UserFeedback).filter(UserFeedback.user_id == user.id).order_by(UserFeedback.created_at.desc()).limit(100).all()
    return [feedback_out(r, user.username) for r in rows]
