from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select, func

import app.db as dbmod
from app.models.chat_turn import ChatTurn
from app.models.feedback import Feedback


router = APIRouter(prefix="/analytics", tags=["Analytics"])


def get_db():
    if dbmod.SessionLocal is None:
        dbmod.get_engine()
    db = dbmod.SessionLocal()
    try:
        yield db
    finally:
        db.close()


class RatingsBreakdown(BaseModel):
    rating_1: int
    rating_2: int
    rating_3: int
    rating_4: int
    rating_5: int


class AnalyticsSummary(BaseModel):
    app_id: str
    total_requests: int
    feedback_count: int
    average_rating: float | None
    ratings: RatingsBreakdown


@router.get("/summary", response_model=AnalyticsSummary)
def summary(app_id: str = Query(...), db: Session = Depends(get_db)):
    try:
        # Total requests from chat turns
        total_requests = db.execute(select(func.count()).select_from(ChatTurn).where(ChatTurn.app_id == app_id)).scalar_one()

        # Feedback count and average
        fb_count_avg = db.execute(
            select(func.count(Feedback.id), func.avg(Feedback.rating)).where(Feedback.app_id == app_id)
        ).one()
        feedback_count = int(fb_count_avg[0] or 0)
        average_rating = float(fb_count_avg[1]) if fb_count_avg[1] is not None else None

        # Ratings breakdown
        rows = db.execute(
            select(Feedback.rating, func.count(Feedback.id)).where(Feedback.app_id == app_id).group_by(Feedback.rating)
        ).all()
        buckets = {int(r[0]): int(r[1]) for r in rows if r[0] is not None}
        ratings = RatingsBreakdown(
            rating_1=buckets.get(1, 0),
            rating_2=buckets.get(2, 0),
            rating_3=buckets.get(3, 0),
            rating_4=buckets.get(4, 0),
            rating_5=buckets.get(5, 0),
        )

        return AnalyticsSummary(
            app_id=app_id,
            total_requests=int(total_requests or 0),
            feedback_count=feedback_count,
            average_rating=average_rating,
            ratings=ratings,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compute analytics: {e}")
