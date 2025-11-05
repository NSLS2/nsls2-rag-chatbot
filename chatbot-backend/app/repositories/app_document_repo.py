from __future__ import annotations

from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from app.models.app_document import AppDocument


def create_or_update_doc(db: Session, *, app_id: str, filename: str, stored_path: str, size_bytes: Optional[int], checksum_sha256: Optional[str], chunk_size: Optional[int], chunk_count: Optional[int], model: Optional[str]) -> AppDocument:
  obj = AppDocument(app_id=app_id, filename=filename, stored_path=stored_path, size_bytes=size_bytes, checksum_sha256=checksum_sha256, chunk_size=chunk_size, chunk_count=chunk_count, model=model)
  db.add(obj)
  db.commit()
  db.refresh(obj)
  return obj


def list_docs(db: Session, app_id: Optional[str], limit: int = 200) -> list[AppDocument]:
  stmt = select(AppDocument).order_by(AppDocument.created_at.desc())
  if app_id:
    stmt = stmt.where(AppDocument.app_id == app_id)
  if limit:
    stmt = stmt.limit(limit)
  return list(db.execute(stmt).scalars().all())


def delete_doc(db: Session, doc_id: int) -> bool:
  obj = db.get(AppDocument, doc_id)
  if not obj:
    return False
  db.delete(obj)
  db.commit()
  return True
