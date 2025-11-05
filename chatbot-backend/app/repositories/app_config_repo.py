from __future__ import annotations

from typing import Iterable, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.app_config import AppConfig


def upsert_app(db: Session, app_id: str, display_name: Optional[str] = None, description: Optional[str] = None, settings: Optional[dict] = None) -> AppConfig:
  existing = db.get(AppConfig, app_id)
  if existing:
    if display_name is not None:
      existing.display_name = display_name
    if description is not None:
      existing.description = description
    if settings is not None:
      existing.settings = settings
    db.add(existing)
    db.commit()
    db.refresh(existing)
    return existing
  obj = AppConfig(app_id=app_id, display_name=display_name, description=description, settings=settings)
  db.add(obj)
  db.commit()
  db.refresh(obj)
  return obj


def list_apps(db: Session) -> list[AppConfig]:
  # Select the full entity so callers receive AppConfig objects
  stmt = select(AppConfig).order_by(AppConfig.app_id.asc())
  return list(db.execute(stmt).scalars().all())


def get_app(db: Session, app_id: str) -> Optional[AppConfig]:
  return db.get(AppConfig, app_id)


def delete_app(db: Session, app_id: str) -> bool:
  obj = db.get(AppConfig, app_id)
  if not obj:
    return False
  db.delete(obj)
  db.commit()
  return True
