# app/ingestion/pipeline.py
from typing import List, Optional, Dict, Any
from langchain.schema import Document
from app.ingestion.universal_loader import load_any
from app.ingestion.chunking import chunk_documents
from app.ingestion.vector_store import embed_and_store
from app.config import settings

def process_and_store(
    source: str,
    app_id: str = "default",
    chunk_size: int = None,
    model_name: str = None,
    extra_payload: Optional[Dict[str, Any]] = None,
    **kwargs
):
    """
    Complete ingestion pipeline that:
    1. Loads data from any source (file, URL, API)
    2. Splits into manageable chunks
    3. Embeds each chunk
    4. Stores embeddings in Qdrant
    """
    print(f"Loading source: {source}")
    docs: List[Document] = load_any(source, **kwargs)

    chunk_size = chunk_size or settings.CHUNK_SIZE
    print(f"Splitting into chunks (chunk size: {chunk_size})")
    chunks = chunk_documents(docs, chunk_size=chunk_size)

    # Use a per-app collection, derived from app_id
    collection_name = f"{app_id}_docs"
    print(f"Embedding and storing chunks in collection: {collection_name}")
    model_name = model_name or settings.EMBEDDING_MODEL
    embed_and_store(
        chunks,
        collection_name=collection_name,
        model_name=model_name,
        recreate=False,
        extra_payload=extra_payload,
    )

    return {"source": source, "chunks": len(chunks), "collection": collection_name, "model": model_name}
