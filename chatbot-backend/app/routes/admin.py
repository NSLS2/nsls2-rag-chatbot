from fastapi import APIRouter, HTTPException, Query, Depends
from app.utils.logger import get_logger
from app.ingestion.vector_store import get_qdrant_client
from app import db as db_mod
from sqlalchemy.orm import Session
from app.repositories import app_config_repo

router = APIRouter(prefix="/admin", tags=["Admin"])
logger = get_logger(__name__)

def get_db():
    if db_mod.SessionLocal is None:
        db_mod.get_engine()
    db = db_mod.SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.delete("/collections")
def delete_all_collections(confirm: bool = Query(False, description="Set to true to confirm deletion of ALL collections.")):
    """
    Delete all Qdrant collections. This is destructive. Requires confirm=true.
    """
    if not confirm:
        raise HTTPException(status_code=400, detail="Confirmation required: pass ?confirm=true to proceed.")

    try:
        client = get_qdrant_client()
        cols = client.get_collections().collections
    except Exception as e:
        logger.exception("Failed to connect to Qdrant")
        raise HTTPException(status_code=503, detail=f"Failed to connect to Qdrant: {e}")

    names = [c.name for c in cols]
    deleted = []
    errors = {}
    for name in names:
        try:
            client.delete_collection(collection_name=name)
            deleted.append(name)
        except Exception as e:
            logger.exception(f"Failed to delete collection {name}")
            errors[name] = str(e)

    return {"deleted": deleted, "errors": errors}


@router.get("/apps")
def list_app_ids(db: Session = Depends(get_db)):
    """
    List app configurations from Postgres.
    Returns a sorted list of unique app_ids.
    """
    try:
        items = app_config_repo.list_apps(db)
        return {"app_ids": [a.app_id for a in items]}
    except Exception as e:
        logger.exception("Failed to list apps from database")
        raise HTTPException(status_code=500, detail=f"Failed to list apps: {e}")


@router.post("/apps")
def upsert_app(app_id: str, display_name: str | None = None, description: str | None = None, db: Session = Depends(get_db)):
    try:
        obj = app_config_repo.upsert_app(db, app_id=app_id, display_name=display_name, description=description)
        return {"app": {"app_id": obj.app_id, "display_name": obj.display_name, "description": obj.description, "created_at": obj.created_at.isoformat() if obj.created_at else None}}
    except Exception as e:
        logger.exception("Failed to upsert app")
        raise HTTPException(status_code=500, detail=f"Failed to upsert app: {e}")


@router.get("/apps/{app_id}")
def get_app(app_id: str, db: Session = Depends(get_db)):
    try:
        obj = app_config_repo.get_app(db, app_id)
        if not obj:
            raise HTTPException(status_code=404, detail="App not found")
        return {"app": {"app_id": obj.app_id, "display_name": obj.display_name, "description": obj.description, "created_at": obj.created_at.isoformat() if obj.created_at else None}}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get app")
        raise HTTPException(status_code=500, detail=f"Failed to get app: {e}")


@router.delete("/apps/{app_id}")
def delete_app(app_id: str, confirm: bool = Query(False), db: Session = Depends(get_db)):
    if not confirm:
        raise HTTPException(status_code=400, detail="Confirmation required: pass ?confirm=true")
    try:
        ok = app_config_repo.delete_app(db, app_id)
        return {"deleted": bool(ok)}
    except Exception as e:
        logger.exception("Failed to delete app")
        raise HTTPException(status_code=500, detail=f"Failed to delete app: {e}")
