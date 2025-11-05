# app/routes/ingest.py
import os
import hashlib
import re
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from app.ingestion.pipeline import process_and_store
from app.config import settings
from app import db as db_mod
from sqlalchemy.orm import Session
from app.repositories import app_config_repo
from app.repositories import app_document_repo

router = APIRouter()

def get_db():
    if db_mod.SessionLocal is None:
        db_mod.get_engine()
    db = db_mod.SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/ingest/file")
async def ingest_file(
    file: UploadFile = File(...),
    app_id: str = Form("default"),
    chunk_size: int = Form(800),
    db: Session = Depends(get_db),
):
    """
    API endpoint to upload a file, process it into chunks,
    embed the chunks, and store them in a Qdrant collection.
    """
    # Determine a safe suffix (keep only extension)
    ext = os.path.splitext(file.filename or "")[1]

    # Create directory structure: UPLOAD_DIR/app_id/filename
    # Sanitize filename to prevent directory traversal attacks
    import re
    safe_filename = file.filename or f"unnamed_file{os.path.splitext(file.filename or '')[1]}"
    safe_filename = re.sub(r'[<>:"/\\|?*]', '_', safe_filename)  # Replace unsafe chars
    safe_app_id = re.sub(r'[<>:"/\\|?*]', '_', app_id)  # Sanitize app_id too
    
    # Create app-specific directory
    app_upload_dir = os.path.join(settings.UPLOAD_DIR, safe_app_id)
    os.makedirs(app_upload_dir, exist_ok=True)
    
    # Handle filename conflicts by adding a counter if file already exists
    upload_path = os.path.join(app_upload_dir, safe_filename)
    counter = 1
    base_name, ext = os.path.splitext(safe_filename)
    while os.path.exists(upload_path):
        upload_path = os.path.join(app_upload_dir, f"{base_name}_{counter}{ext}")
        counter += 1

    # Write the uploaded file to the upload directory in chunks to avoid high memory usage
    max_bytes = int(getattr(settings, "MAX_FILE_SIZE_MB", 25)) * 1024 * 1024
    written = 0
    try:
        with open(upload_path, 'wb') as f:
            # read in 1MB chunks
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if max_bytes and written > max_bytes:
                    raise HTTPException(status_code=413, detail="File too large")
                f.write(chunk)

        # Ensure app exists in AppConfig for listing
        try:
            app_config_repo.upsert_app(db, app_id=app_id)
        except Exception:
            # non-fatal; continue ingestion
            pass

        # Process and store using the pipeline (expects a file path)
        result = process_and_store(
            upload_path,
            app_id=app_id,
            chunk_size=chunk_size,
            extra_payload={"app_id": app_id, "filename": file.filename or os.path.basename(upload_path)},
        )

        # Persist document metadata (best-effort; failures do not block ingestion)
        try:
            h = hashlib.sha256()
            with open(upload_path, 'rb') as rf:
                for b in iter(lambda: rf.read(1024 * 1024), b''):
                    h.update(b)
            checksum = h.hexdigest()
            app_document_repo.create_or_update_doc(
                db,
                app_id=app_id,
                filename=file.filename or os.path.basename(upload_path),
                stored_path=upload_path,
                size_bytes=written,
                checksum_sha256=checksum,
                chunk_size=chunk_size,
                chunk_count=result.get('chunks'),
                model=result.get('model'),
            )
        except Exception:
            pass

        return result
    except Exception as e:
        # If processing fails, clean up the uploaded file
        if os.path.exists(upload_path):
            try:
                os.remove(upload_path)
            except OSError:
                pass
        raise e
