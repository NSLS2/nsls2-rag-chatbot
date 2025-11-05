from __future__ import annotations

from sqlalchemy import Column, Integer, String, Text, DateTime, BigInteger, Index
from sqlalchemy.sql import func
from app.db import Base


class AppDocument(Base):
    __tablename__ = "app_document"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(String(128), index=True, nullable=False)
    filename = Column(String(512), nullable=False)  # original filename
    stored_path = Column(Text, nullable=False)      # absolute or workspace-relative path
    size_bytes = Column(BigInteger, nullable=True)
    checksum_sha256 = Column(String(64), nullable=True, index=True)
    chunk_size = Column(Integer, nullable=True)
    chunk_count = Column(Integer, nullable=True)
    model = Column(String(256), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_app_document_app_created", "app_id", "created_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AppDocument id={self.id} app_id='{self.app_id}' file='{self.filename}'>"
