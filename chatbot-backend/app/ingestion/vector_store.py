# app/ingestion/vector_store.py
import os
import re
import numpy as np
from typing import List, Optional
from collections import OrderedDict
from uuid import uuid4
from qdrant_client import QdrantClient, models
from app.config import settings
from langchain.schema import Document


def get_qdrant_client() -> QdrantClient:
    """
    Initialize and return a Qdrant client using environment variables.
    """
    host = settings.QDRANT_HOST
    port = settings.QDRANT_PORT
    return QdrantClient(host=host, port=port)


def embed_and_store(
    docs: List[Document],
    collection_name: str = "default_docs",
    model_name: str = None,
    recreate: bool = True,
    extra_payload: Optional[dict] = None,
):
    """
    Generate embeddings for document chunks and store them in Qdrant.

    Args:
        docs: List of LangChain Document objects.
        collection_name: Qdrant collection name.
        model_name: SentenceTransformer model.
        recreate: If True, recreate the collection (drops old data).
    """
    if not docs:
        raise ValueError("No documents provided for embedding.")

    # Initialize embedding model (with caching)
    model_name = model_name or settings.EMBEDDING_MODEL
    model = get_embedding_model(model_name)
    embedding_dim = model.get_sentence_embedding_dimension()

    # Connect to Qdrant
    client = get_qdrant_client()

    # Create or reuse collection
    if recreate:
        print(f"Recreating collection '{collection_name}'...")
        client.recreate_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=embedding_dim, distance=models.Distance.COSINE),
        )
    else:
        collections = [c.name for c in client.get_collections().collections]
        if collection_name not in collections:
            print(f"Creating new collection '{collection_name}'...")
            client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(size=embedding_dim, distance=models.Distance.COSINE),
            )

    # Generate embeddings in batch
    embeddings = embed_chunks(model, docs)

    # Upsert embeddings
    print(f"Encoding complete. Upserting {len(docs)} chunks into Qdrant...")
    points = []
    for doc, vector in zip(docs, embeddings):
        payload = {**(doc.metadata or {}), "text": doc.page_content}
        if extra_payload:
            payload.update(extra_payload)
        points.append(
            models.PointStruct(
                id=str(uuid4()),
                vector=np.asarray(vector).tolist(),
                payload=payload,
            )
        )

    client.upsert(collection_name=collection_name, points=points)
    print(f"Stored {len(points)} chunks in Qdrant collection: '{collection_name}'.")


def embed_chunks(model, chunks: List[Document]) -> np.ndarray:
    """
    Batch-generate embeddings for a list of LangChain Documents using a SentenceTransformer model.

    Args:
        model: An initialized SentenceTransformer model.
        chunks: List of Documents whose page_content will be embedded.

    Returns:
        np.ndarray of shape (len(chunks), embedding_dim)
    """
    texts = [chunk.page_content for chunk in chunks]
    print(f"[INFO] Generating embeddings for {len(texts)} chunks...")
    embeddings = model.encode(texts, show_progress_bar=True)
    print(f"[INFO] Embeddings shape: {getattr(embeddings, 'shape', 'unknown')}")
    return embeddings


# Simple in-process model cache to avoid reloading on every call
_model_cache: dict[str, object] = {}


def get_embedding_model(model_name: Optional[str] = None):
    name = model_name or settings.EMBEDDING_MODEL
    if name in _model_cache:
        return _model_cache[name]
    print(f"Initializing embedding model: {name}")
    from sentence_transformers import SentenceTransformer  # Lazy import
    model = SentenceTransformer(name)
    _model_cache[name] = model
    return model


def embed_query(text: str, model_name: Optional[str] = None) -> np.ndarray:
    # Try cache first for identical or very similar queries
    key = _make_query_cache_key(text, model_name)
    cached = _query_vec_cache_get(key)
    if cached is not None:
        return cached

    model = get_embedding_model(model_name)
    vec = model.encode([text], show_progress_bar=False)[0]
    arr = np.asarray(vec)
    _query_vec_cache_put(key, arr)
    return arr


def search_qdrant(
    query: str,
    collection_name: str = "default_docs",
    model_name: Optional[str] = None,
    top_k: int = None,
    score_threshold: Optional[float] = None,
    app_id: Optional[str] = None,
    with_payload: bool = True,
    with_vectors: bool = False,
):
    """
    Perform a similarity search in Qdrant for the given query text.

    Returns a list of scored points with id, score, and payload (if requested).
    """
    client = get_qdrant_client()
    query_vector = embed_query(query, model_name=model_name).tolist()

    # Optional filter by app_id if provided
    query_filter = None
    if app_id:
        query_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="app_id",
                    match=models.MatchValue(value=app_id),
                )
            ]
        )

    # Fallback to unified default if caller passed None
    effective_top_k = top_k or settings.DEFAULT_TOP_K
    results = client.search(
        collection_name=collection_name,
        query_vector=query_vector,
        query_filter=query_filter,
        limit=effective_top_k,
        score_threshold=score_threshold,
        with_payload=with_payload,
        with_vectors=with_vectors,
    )

    # Normalize into simple dicts for ease of use by routes
    normalized = [
        {
            "id": r.id,
            "score": r.score,
            "payload": getattr(r, "payload", None),
        }
        for r in results
    ]
    return normalized


# -------------------------
# Query embedding LRU cache
# -------------------------

# Maximum number of cached query embeddings; configurable via env
_QUERY_EMBED_CACHE_SIZE = int(os.getenv("QUERY_EMBED_CACHE_SIZE", "1000"))
_query_vec_cache: "OrderedDict[str, np.ndarray]" = OrderedDict()


def _normalize_query(text: str) -> str:
    """Normalize query string to improve cache hit rate for very similar inputs.

    - Lowercase
    - Trim whitespace and collapse multiple spaces
    - Strip common trailing punctuation (.,!? )
    """
    if not text:
        return ""
    s = text.lower().strip()
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s)
    # Strip simple trailing punctuation
    s = s.rstrip(" .!?\t\n\r")
    return s


def _make_query_cache_key(text: str, model_name: Optional[str]) -> str:
    name = model_name or settings.EMBEDDING_MODEL
    return f"{name}::{_normalize_query(text)}"


def _query_vec_cache_get(key: str) -> Optional[np.ndarray]:
    try:
        arr = _query_vec_cache.pop(key)
        # reinsert to mark as most recently used
        _query_vec_cache[key] = arr
        return arr
    except KeyError:
        return None


def _query_vec_cache_put(key: str, arr: np.ndarray) -> None:
    # Insert/move to end, enforce capacity
    if key in _query_vec_cache:
        _query_vec_cache.pop(key, None)
    _query_vec_cache[key] = arr
    while len(_query_vec_cache) > _QUERY_EMBED_CACHE_SIZE:
        # Pop least-recently-used
        _query_vec_cache.popitem(last=False)
