from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.utils.logger import get_logger
from app.ingestion.vector_store import search_qdrant
from app.config import settings

router = APIRouter(prefix="/search", tags=["Search"])
logger = get_logger(__name__)


class SearchRequest(BaseModel):
    query: str
    top_k: int = settings.DEFAULT_TOP_K
    app_id: str


class SearchResult(BaseModel):
    id: str | int
    score: float
    payload: Optional[dict] = None


class SearchResponse(BaseModel):
    results: List[SearchResult]


@router.post("/", response_model=SearchResponse)
async def search_endpoint(req: SearchRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    if not req.app_id:
        raise HTTPException(status_code=400, detail="app_id is required.")
    collection = f"{req.app_id}_docs"
    logger.info(f"Search request: query='{req.query}' top_k={req.top_k} collection='{collection}'")

    try:
        raw = search_qdrant(
            query=req.query,
            collection_name=collection,
            top_k=req.top_k,
            with_payload=True,
            with_vectors=False,
        )
    except Exception as e:
        logger.exception("Search failed")
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")

    # Pydantic will coerce the dicts to SearchResult schema
    return SearchResponse(results=raw)
