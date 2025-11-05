from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app import db as db_mod
from app.repositories import app_document_repo
from app.ingestion.vector_store import get_qdrant_client
from app.models.app_document import AppDocument
from qdrant_client import models

router = APIRouter(prefix="/documents", tags=["Documents"])


def get_db():
    if db_mod.SessionLocal is None:
        db_mod.get_engine()
    db = db_mod.SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/")
def list_documents(app_id: Optional[str] = None, limit: int = 200, db: Session = Depends(get_db)):
    items = app_document_repo.list_docs(db, app_id=app_id, limit=limit)
    return {
        "items": [
            {
                "id": d.id,
                "app_id": d.app_id,
                "filename": d.filename,
                "size_bytes": d.size_bytes,
                "chunk_size": d.chunk_size,
                "chunk_count": d.chunk_count,
                "model": d.model,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in items
        ]
    }


@router.delete("/{doc_id}")
def delete_document(doc_id: int, confirm: bool = Query(False), db: Session = Depends(get_db)):
    if not confirm:
        raise HTTPException(status_code=400, detail="Confirmation required: pass ?confirm=true")
    doc = db.get(AppDocument, doc_id)
    if not doc:
        return {"deleted": False}
    # Attempt to delete vectors from Qdrant by filtering on payload
    try:
        client = get_qdrant_client()
        collection = f"{doc.app_id}_docs"
        q_filter = models.Filter(must=[
            models.FieldCondition(key="app_id", match=models.MatchValue(value=doc.app_id)),
            models.FieldCondition(key="filename", match=models.MatchValue(value=doc.filename)),
        ])
        client.delete(collection_name=collection, points_selector=models.FilterSelector(filter=q_filter))
    except Exception:
        # Best-effort; ignore failures
        pass
    ok = app_document_repo.delete_doc(db, doc_id)
    return {"deleted": bool(ok)}


@router.post("/{doc_id}/reindex")
def reindex_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.get(AppDocument, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    # Re-run ingestion using stored_path; set recreate=False to append
    from app.ingestion.pipeline import process_and_store
    res = process_and_store(doc.stored_path, app_id=doc.app_id, chunk_size=doc.chunk_size, extra_payload={"app_id": doc.app_id, "filename": doc.filename})
    return {"status": "ok", "result": res}
