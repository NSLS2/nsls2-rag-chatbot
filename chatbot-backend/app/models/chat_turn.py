from __future__ import annotations

from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.db import Base


class ChatTurn(Base):
    __tablename__ = "chat_turns"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(String(128), index=True, nullable=False)
    user_message = Column(Text, nullable=False)
    assistant_answer = Column(Text, nullable=False)
    sources = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    __table_args__ = (
        Index("ix_chat_turns_app_created_at", "app_id", "created_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ChatTurn id={self.id} app_id='{self.app_id}' created_at={self.created_at}>"
