"""Dashboard statistics for the signed-in user. Every number is counted from the database."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import AnalysisResult, User, as_utc
from app.services import analysis_service as svc
from app.services.registry import list_models

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
DAYS = 14


def daily_counts(rows: list[datetime], days: int = DAYS) -> list[dict]:
    today = datetime.now(timezone.utc).date()
    counter = Counter(as_utc(r).date() for r in rows)
    return [{"date": (today - timedelta(days=i)).isoformat(), "count": counter.get(today - timedelta(days=i), 0)}
            for i in range(days - 1, -1, -1)]


@router.get("/stats", summary="Your usage statistics")
def stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    base = db.query(AnalysisResult).filter(AnalysisResult.user_id == user.id)
    total = base.count()
    by_type = dict(base.with_entities(AnalysisResult.analysis_type, func.count()).group_by(AnalysisResult.analysis_type).all())
    by_verdict = dict(base.with_entities(AnalysisResult.verdict, func.count()).group_by(AnalysisResult.verdict).all())
    since = datetime.now(timezone.utc) - timedelta(days=DAYS)
    recent_dates = [d for (d,) in base.filter(AnalysisResult.created_at >= since).with_entities(AnalysisResult.created_at).all()]
    rows, _ = svc.list_analyses(db, user, 1, 5, None, None, None)
    return {
        "total_analyses": total,
        "by_type": by_type,
        "by_verdict": by_verdict,
        "daily": daily_counts(recent_dates),
        "recent": [svc.serialise(r, include_details=False) for r in rows],
        "modules": [{"module": m["module"], "name": m["name"], "status": m["status"]} for m in list_models()],
    }
