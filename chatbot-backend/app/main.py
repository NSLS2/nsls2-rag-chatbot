import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from app.routes import chat, ingest, search, admin, feedback, documents, history, analytics
from fastapi import HTTPException
from app.config import settings  # ensure config is imported and initialized
from app.utils.logger import get_logger
from app.db import init_db

# Accessing settings ensures app.config is imported and its module-level setup runs
USER_AGENT = getattr(settings, "USER_AGENT", None)

if not USER_AGENT:
    print("⚠️ USER_AGENT environment variable not set, consider setting it to identify your requests.")
else:
    print(f"✅ USER_AGENT loaded: {USER_AGENT}")

# Log a couple of config values at startup to verify config usage
print(f"✅ Config: Qdrant at {settings.QDRANT_HOST}:{settings.QDRANT_PORT}, model={settings.EMBEDDING_MODEL}")

logger = get_logger(__name__)


app = FastAPI(
    title="Generic RAG Chatbot API",
    description=(
        "This API provides a configurable Retrieval-Augmented Generation (RAG) backend "
        "that can ingest diverse data sources, convert them into LangChain Document format, "
        "store embeddings in a vector database, and generate context-aware responses "
        "using large language models (LLMs)."
        "\n\n"
        "### Modules\n"
        "1. **/ingest** — Upload and index data from multiple sources.\n"
        "2. **/chat** — Query the chatbot using a retrieval-augmented workflow."
    ),
    version="1.0.0",
    contact={
        "name": "Chatbot Backend Team",
        "url": "https://github.com/your-org/chatbot-backend",
        "email": "support@yourcompany.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    docs_url="/swagger",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1,
        "displayRequestDuration": True,
    },
)

# --- CORS Configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
app.include_router(chat.router)
app.include_router(ingest.router)
app.include_router(search.router)
app.include_router(admin.router)
app.include_router(feedback.router)
app.include_router(documents.router)
app.include_router(history.router)
app.include_router(analytics.router)


@app.get("/llm/health", tags=["LLM"], summary="Check Ollama availability")
def llm_health():
    """Return basic status of Ollama model availability."""
    from app.services.llm import _get_ollama_client  # type: ignore
    client = _get_ollama_client()
    if client is None:
        raise HTTPException(status_code=503, detail="Ollama client unavailable")
    return {
        "ollama_host": settings.OLLAMA_HOST,
        "model": settings.OLLAMA_MODEL,
        "num_predict": settings.OLLAMA_NUM_PREDICT,
        "temperature": settings.OLLAMA_TEMPERATURE,
        "status": "ready",
    }


@app.get("/", tags=["Root"])
def root():
    """Basic health check endpoint."""
    logger.info("Health check request received.")
    return {"message": "Generic RAG Chatbot backend is running."}


@app.on_event("startup")
def _on_startup():
    try:
        init_db()
        logger.info("Database initialized")
        # Optional warm-up for Ollama to mitigate first-request latency
        try:
            from app.services.llm import _get_ollama_client  # type: ignore
            client = _get_ollama_client()
            if client is not None:
                logger.info("Performing Ollama warm-up prompt")
                # Send a trivial prompt to force model load
                client.invoke(["Warm-up"])
                logger.info("Ollama warm-up complete")
        except Exception as e:
            logger.warning(f"Ollama warm-up skipped: {e}")
    except Exception as e:
        logger.error(f"Database init failed: {e}")


@app.get("/docs", include_in_schema=False)
def redirect_to_swagger():
    """Redirect /docs to the Swagger UI."""
    return RedirectResponse(url="/swagger")
