from __future__ import annotations

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.feedback import Feedback


def create_feedback(db: Session, data: Dict[str, Any]) -> Feedback:
    fb = Feedback(
        app_id=data["app_id"],
        query=data["query"],
        response=data["response"],
        rating=data["rating"],
        comment=data.get("comment"),
        sources=data.get("sources"),
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb


def list_feedback(db: Session, app_id: Optional[str] = None, limit: int = 100) -> List[Feedback]:
    q = db.query(Feedback)
    if app_id:
        q = q.filter(Feedback.app_id == app_id)
    return q.order_by(desc(Feedback.created_at)).limit(limit).all()


def clear_feedback(db: Session, app_id: Optional[str] = None) -> int:
    q = db.query(Feedback)
    if app_id:
        q = q.filter(Feedback.app_id == app_id)
    count = q.count()
    q.delete(synchronize_session=False)
    db.commit()
    return count
