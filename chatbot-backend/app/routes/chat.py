from fastapi import APIRouter, HTTPException, Depends, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from app.utils.logger import get_logger
from app.ingestion.vector_store import search_qdrant
from app.config import settings
from app.services.llm import generate_answer, stream_answer
from sqlalchemy.orm import Session
import app.db as dbmod
from app.repositories import chat_history_repo

router = APIRouter(prefix="/chat", tags=["Chat"])
logger = get_logger(__name__)

class ChatRequest(BaseModel):
    message: str
    # Use unified default from settings; user can still override per request
    top_k: int = settings.DEFAULT_TOP_K
    app_id: str

class ChatResponse(BaseModel):
    response: str
    sources: List[dict] = []


def get_db():
    if dbmod.SessionLocal is None:
        # Lazily initialize the engine/session factory if startup hasn't run yet
        dbmod.get_engine()
    db = dbmod.SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, response: Response, db: Session = Depends(get_db)):
    """
    Handle chat queries.  
    In future versions, this will use the RAG pipeline for context-aware responses.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    import time
    start_total = time.perf_counter()
    logger.info(
        f"[chat] Received user query app_id={request.app_id} top_k={request.top_k} collection={request.app_id}_docs message='{request.message[:120]}'"
    )

    # Retrieve top_k matches from the per-app collection
    try:
        start_retrieval = time.perf_counter()
        if not request.app_id:
            raise ValueError("app_id is required")
        collection = f"{request.app_id}_docs"
        results = search_qdrant(
            query=request.message,
            collection_name=collection,
            top_k=request.top_k,
            with_payload=True,
            with_vectors=False,
        )
        retrieval_ms = (time.perf_counter() - start_retrieval) * 1000.0
        if results:
            logger.info(
                "[chat] Retrieval completed in %.2f ms results=%d top_scores=%s" % (
                    retrieval_ms,
                    len(results),
                    ",".join(f"{r.get('score'):.4f}" for r in results[:5] if isinstance(r, dict) and r.get('score') is not None),
                )
            )
            if len(results) < request.top_k:
                logger.info(
                    f"[chat] Retrieved fewer than requested top_k={request.top_k}; collection may have limited chunks or low-similarity matches"
                )
        else:
            logger.info(f"[chat] Retrieval completed in {retrieval_ms:.2f} ms with 0 results")
    except Exception as e:
        logger.exception("Retrieval failed")
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {e}")

    # Simple heuristic answer using the top snippets (placeholder for an LLM)
    snippets = []
    for r in results:
        text = (r.get("payload") or {}).get("text") if isinstance(r, dict) else None
        if text:
            snippets.append(text)
    start_gen = time.perf_counter()
    answer = generate_answer(request.message, snippets, max_snippets=request.top_k)
    gen_ms = (time.perf_counter() - start_gen) * 1000.0
    total_ms = (time.perf_counter() - start_total) * 1000.0
    logger.info(f"[chat] Answer generation: {gen_ms:.2f} ms; total request time: {total_ms:.2f} ms")
    # Expose timing via response headers for downstream diagnostics
    response.headers["X-Retrieval-ms"] = f"{retrieval_ms:.2f}"
    response.headers["X-Generation-ms"] = f"{gen_ms:.2f}"
    response.headers["X-Total-ms"] = f"{total_ms:.2f}"
    # Persist chat turn
    try:
        chat_history_repo.add_turn(db, app_id=request.app_id, user_message=request.message, assistant_answer=answer, sources=results)
    except Exception:
        logger.exception("Failed to persist chat turn")

    return ChatResponse(response=answer, sources=results)


@router.post("/stream")
async def chat_stream(request: ChatRequest, db: Session = Depends(get_db)):
    """Stream LLM answer tokens for a chat query using Server-Sent Events.

    Returns a text/event-stream response where each event has 'data: <chunk>'.
    Final event contains a JSON object with full aggregated answer and sources.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    import time, json
    start_total = time.perf_counter()
    logger.info(
        f"[chat-stream] Received user query app_id={request.app_id} top_k={request.top_k} collection={request.app_id}_docs message='{request.message[:120]}'"
    )
    if not request.app_id:
        raise HTTPException(status_code=400, detail="app_id is required")
    collection = f"{request.app_id}_docs"
    try:
        start_retrieval = time.perf_counter()
        results = search_qdrant(
            query=request.message,
            collection_name=collection,
            top_k=request.top_k,
            with_payload=True,
            with_vectors=False,
        )
        retrieval_ms = (time.perf_counter() - start_retrieval) * 1000.0
        if results:
            logger.info(
                "[chat-stream] Retrieval %.2f ms results=%d top_scores=%s" % (
                    retrieval_ms,
                    len(results),
                    ",".join(f"{r.get('score'):.4f}" for r in results[:5] if isinstance(r, dict) and r.get('score') is not None),
                )
            )
            if len(results) < request.top_k:
                logger.info(
                    f"[chat-stream] Retrieved fewer than requested top_k={request.top_k}; collection may have limited chunks or low-similarity matches"
                )
        else:
            logger.info(f"[chat-stream] Retrieval {retrieval_ms:.2f} ms results=0")
    except Exception as e:
        logger.exception("[chat-stream] Retrieval failed")
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {e}")
    snippets = []
    for r in results:
        text = (r.get("payload") or {}).get("text") if isinstance(r, dict) else None
        if text:
            snippets.append(text)

    async def event_generator():
        aggregated = []
        try:
            for chunk in stream_answer(request.message, snippets, max_snippets=request.top_k):
                if not isinstance(chunk, str):
                    continue
                aggregated.append(chunk)
                # SSE data event (avoid newlines inside chunk by replacing with spaces)
                sanitized_chunk = chunk.replace('\n', ' ')
                yield f"data: {sanitized_chunk}\n\n"
        except Exception:
            logger.exception("[chat-stream] Streaming failed mid-way")
        full_answer = "".join(aggregated).strip() or "I don't have that information."
        total_ms = (time.perf_counter() - start_total) * 1000.0
        # Persist chat turn at end
        try:
            chat_history_repo.add_turn(db, app_id=request.app_id, user_message=request.message, assistant_answer=full_answer, sources=results)
        except Exception:
            logger.exception("[chat-stream] Persist turn failed")
        final_payload = {
            "answer": full_answer,
            "sources": results,
            "timing": {"retrieval_ms": retrieval_ms, "total_ms": total_ms},
        }
        yield f"event: done\ndata: {json.dumps(final_payload)}\n\n"
    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",  # Disable buffering in some proxies
        "Connection": "keep-alive",
    }
    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=headers)
