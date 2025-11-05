from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.utils.logger import get_logger
from app import db as db_mod
from sqlalchemy.orm import Session
from app.repositories import feedback_repo

router = APIRouter(prefix="/feedback", tags=["Feedback"])
logger = get_logger(__name__)


class FeedbackIn(BaseModel):
    app_id: str
    query: str
    response: str
    rating: int  # e.g., 1-5
    comment: Optional[str] = None
    sources: Optional[List[Dict[str, Any]]] = None


def get_db():
    # Ensure the engine and SessionLocal are initialized lazily
    if db_mod.SessionLocal is None:
        db_mod.get_engine()
    db = db_mod.SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/")
def submit_feedback(body: FeedbackIn, db: Session = Depends(get_db)):
    try:
        feedback_repo.create_feedback(db, body.model_dump())
        return {"status": "ok"}
    except Exception as e:
        logger.exception("Failed to write feedback")
        raise HTTPException(status_code=500, detail=f"Failed to write feedback: {e}")


@router.get("/")
def get_feedback(app_id: Optional[str] = None, limit: int = 100, db: Session = Depends(get_db)):
    try:
        items = feedback_repo.list_feedback(db, app_id=app_id, limit=limit)
        # Serialize SQLAlchemy objects to dicts
        return {"items": [
            {
                "id": fb.id,
                "app_id": fb.app_id,
                "query": fb.query,
                "response": fb.response,
                "rating": fb.rating,
                "comment": fb.comment,
                "sources": fb.sources,
                "created_at": fb.created_at.isoformat() if fb.created_at else None,
            }
            for fb in items
        ]}
    except Exception as e:
        logger.exception("Failed to list feedback")
        raise HTTPException(status_code=500, detail=f"Failed to list feedback: {e}")


@router.delete("/")
def delete_feedback(app_id: Optional[str] = None, confirm: bool = Query(False), db: Session = Depends(get_db)):
    if not confirm:
        raise HTTPException(status_code=400, detail="Confirmation required: pass ?confirm=true")
    try:
        removed = feedback_repo.clear_feedback(db, app_id=app_id)
        return {"removed": removed}
    except Exception as e:
        logger.exception("Failed to clear feedback")
        raise HTTPException(status_code=500, detail=f"Failed to clear feedback: {e}")
