from __future__ import annotations

import os
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings


Base = declarative_base()
_engine = None
SessionLocal = None



def get_engine():
    global _engine, SessionLocal
    if _engine is not None:
        return _engine
    url = getattr(settings, "DATABASE_URL", None) or os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL or POSTGRES_* env vars are not configured")
    # Log the raw URL as requested (note: this includes credentials)
    print(f"[DB] Using URL: {url}")
    _engine = create_engine(url, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine


def init_db():
    # Import models here to ensure they are registered with Base
    from app.models import feedback as _  # noqa: F401
    from app.models import app_config as __  # noqa: F401
    from app.models import app_document as ___  # noqa: F401
    from app.models import chat_turn as ____  # noqa: F401

    engine = get_engine()
    Base.metadata.create_all(bind=engine)
