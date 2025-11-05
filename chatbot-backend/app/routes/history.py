from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import select

import app.db as dbmod
from app.repositories import chat_history_repo
from app.models.feedback import Feedback


router = APIRouter(prefix="/history", tags=["History"])


def get_db():
    if dbmod.SessionLocal is None:
        dbmod.get_engine()
    db = dbmod.SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ChatTurnOut(BaseModel):
    id: int
    app_id: str
    user_message: str
    assistant_answer: str
    sources: list
    created_at: datetime
    rating: int | None = None
    comment: str | None = None

    class Config:
        from_attributes = True


@router.get("/", response_model=List[ChatTurnOut])
def list_history(app_id: str = Query(...), limit: int = Query(100, ge=1, le=1000), db: Session = Depends(get_db)):
    turns = chat_history_repo.list_turns(db, app_id=app_id, limit=limit)

    # Fetch feedback for this app and index by (query, response)
    fb_rows = db.execute(
        select(Feedback.query, Feedback.response, Feedback.rating, Feedback.comment).where(Feedback.app_id == app_id)
    ).all()
    fb_map = { (r[0] or "", r[1] or ""): (r[2], r[3]) for r in fb_rows }

    out: List[ChatTurnOut] = []
    for t in turns:
        rating = None
        comment = None
        key = (t.user_message or "", t.assistant_answer or "")
        if key in fb_map:
            rating, comment = fb_map[key]
        out.append(ChatTurnOut(
            id=t.id,
            app_id=t.app_id,
            user_message=t.user_message,
            assistant_answer=t.assistant_answer,
            sources=t.sources or [],
            created_at=t.created_at,
            rating=rating,
            comment=comment,
        ))
    return out


@router.delete("/", response_model=dict)
def clear_history(app_id: str = Query(...), confirm: bool = Query(False), db: Session = Depends(get_db)):
    if not confirm:
        raise HTTPException(status_code=400, detail="Set confirm=true to clear chat history")
    deleted = chat_history_repo.clear_turns(db, app_id=app_id)
    return {"deleted": deleted}
