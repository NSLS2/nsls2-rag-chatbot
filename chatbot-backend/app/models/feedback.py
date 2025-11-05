"""ORM models for feedback persistence.

This module defines the Feedback table used to store chat ratings and comments.
"""

from __future__ import annotations

from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.db import Base


class Feedback(Base):
    __tablename__ = "feedback"

    # Columns
    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(String(128), index=True, nullable=False)
    query = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    sources = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Helpful composite index for common list queries
    __table_args__ = (
        Index("ix_feedback_app_created_at", "app_id", "created_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug convenience
        return (
            f"<Feedback id={self.id} app_id='{self.app_id}' rating={self.rating} "
            f"created_at={self.created_at}>"
        )
