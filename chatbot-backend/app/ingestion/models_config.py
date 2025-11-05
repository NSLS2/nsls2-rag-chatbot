# app/ingestion/models_config.py

MODEL_INFO = {
    "sentence-transformers/all-MiniLM-L6-v2": {
        "max_tokens": 256,
        "embedding_dim": 384,
        "recommended_chunk_tokens": 150,
    },
    # You can easily extend this for other models later
    # "intfloat/e5-base-v2": {"max_tokens": 512, "embedding_dim": 768, "recommended_chunk_tokens": 400},
}
