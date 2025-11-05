from __future__ import annotations

from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.db import Base


class AppConfig(Base):
    __tablename__ = "app_config"

    # Primary key is the app_id string to keep it simple and readable
    app_id = Column(String(128), primary_key=True, index=True)
    display_name = Column(String(256), nullable=True)
    description = Column(Text, nullable=True)
    settings = Column(JSONB, nullable=True)  # arbitrary per-app settings
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AppConfig app_id='{self.app_id}'>"
