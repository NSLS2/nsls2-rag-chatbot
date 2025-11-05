from __future__ import annotations

from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import select, delete

from app.models.chat_turn import ChatTurn


def add_turn(db: Session, app_id: str, user_message: str, assistant_answer: str, sources: list | None) -> ChatTurn:
    turn = ChatTurn(app_id=app_id, user_message=user_message, assistant_answer=assistant_answer, sources=sources or [])
    db.add(turn)
    db.commit()
    db.refresh(turn)
    return turn


def list_turns(db: Session, app_id: str, limit: int = 100) -> List[ChatTurn]:
    stmt = (
        select(ChatTurn)
        .where(ChatTurn.app_id == app_id)
        .order_by(ChatTurn.created_at.desc())
        .limit(limit)
    )
    return [row[0] for row in db.execute(stmt).all()]


def clear_turns(db: Session, app_id: str) -> int:
    stmt = delete(ChatTurn).where(ChatTurn.app_id == app_id)
    res = db.execute(stmt)
    db.commit()
    return res.rowcount or 0
