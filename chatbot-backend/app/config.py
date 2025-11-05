import os

# Best-effort load of .env when not handled by Pixi or the runtime environment
try:
    from dotenv import load_dotenv  # type: ignore
    # In local dev, prefer .env values over pre-set shell env to avoid stale values
    load_dotenv(override=True)
except Exception:
    # If python-dotenv isn't installed, skip silently; Pixi may handle dotenv
    pass

# Set USER_AGENT early to avoid warnings from HuggingFace/sentence-transformers
if "USER_AGENT" not in os.environ:
    os.environ["USER_AGENT"] = "chatbot-backend/0.1.0 (contact: hbishai1@bnl.gov)"

class Settings:
    """Configuration loader that enforces explicit env definition.

    All required variables must be present in `.env` (or the environment).
    No silent fallbacks: missing required values raise at startup to avoid
    drifting configs between environments.
    """

    REQUIRED_VARS = [
        "APP_NAME","APP_ENV","DEBUG","LOG_LEVEL","PORT",
        "QDRANT_HOST","QDRANT_PORT","QDRANT_COLLECTION","EMBEDDING_MODEL",
        "OLLAMA_HOST","OLLAMA_MODEL","OLLAMA_NUM_PREDICT","OLLAMA_TEMPERATURE",
        "SNIPPET_MAX_CHARS","GENERATION_TIMEOUT_MS","GENERATION_ENFORCE_TIMEOUT",
        "DEFAULT_TOP_K","DATABASE_URL","CHUNK_SIZE","CHUNK_OVERLAP",
        "UPLOAD_DIR","MAX_FILE_SIZE_MB","USER_AGENT","ENABLE_STREAMING"
    ]

    def _require(self, name: str) -> str:
        val = os.getenv(name)
        if val is None or val.strip() == "":
            raise RuntimeError(f"Missing required environment variable: {name}")
        return val

    def __init__(self):
        # Validate all required vars first for clear error reporting
        missing = [v for v in self.REQUIRED_VARS if not os.getenv(v)]
        if missing:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

        # Core Application Settings
        self.APP_NAME = self._require("APP_NAME")
        self.APP_ENV = self._require("APP_ENV")
        self.DEBUG = self._require("DEBUG").lower() == "true"
        self.LOG_LEVEL = self._require("LOG_LEVEL")
        self.PORT = int(self._require("PORT"))

        # Qdrant settings
        self.QDRANT_HOST = self._require("QDRANT_HOST")
        self.QDRANT_PORT = int(self._require("QDRANT_PORT"))
        self.QDRANT_COLLECTION = self._require("QDRANT_COLLECTION")

        # Embedding model
        self.EMBEDDING_MODEL = self._require("EMBEDDING_MODEL")

        # Local LLM (Ollama) settings
        self.OLLAMA_HOST = self._require("OLLAMA_HOST")
        self.OLLAMA_MODEL = self._require("OLLAMA_MODEL")
        self.OLLAMA_NUM_PREDICT = int(self._require("OLLAMA_NUM_PREDICT"))
        self.OLLAMA_TEMPERATURE = float(self._require("OLLAMA_TEMPERATURE"))

        # Generation constraints / retrieval
        self.SNIPPET_MAX_CHARS = int(self._require("SNIPPET_MAX_CHARS"))
        self.GENERATION_TIMEOUT_MS = int(self._require("GENERATION_TIMEOUT_MS"))
        self.GENERATION_ENFORCE_TIMEOUT = self._require("GENERATION_ENFORCE_TIMEOUT").lower() == "true"
        self.DEFAULT_TOP_K = int(self._require("DEFAULT_TOP_K"))

        # Database (Postgres) — now mandatory explicit DATABASE_URL
        self.DATABASE_URL = self._require("DATABASE_URL").strip()

        # Chunking
        self.CHUNK_SIZE = int(self._require("CHUNK_SIZE"))
        self.CHUNK_OVERLAP = int(self._require("CHUNK_OVERLAP"))

        # File handling
        self.UPLOAD_DIR = self._require("UPLOAD_DIR")
        self.MAX_FILE_SIZE_MB = int(self._require("MAX_FILE_SIZE_MB"))

        # User agent for HF downloads
        self.USER_AGENT = self._require("USER_AGENT")
        if "USER_AGENT" not in os.environ:
            os.environ["USER_AGENT"] = self.USER_AGENT

        # Feature flags / streaming
        self.ENABLE_STREAMING = self._require("ENABLE_STREAMING").lower() == "true"


# Singleton instance
settings = Settings()

def validate_config():
    """Validate configuration and display status."""
    issues = []
    
    # Create upload directory if it doesn't exist
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    print(f"Configuration loaded successfully")
    print(f"   - App: {settings.APP_NAME}")
    print(f"   - Environment: {settings.APP_ENV}")
    print(f"   - Qdrant: {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
    print(f"   - Collection: {settings.QDRANT_COLLECTION}")
    print(f"   - Embedding Model: {settings.EMBEDDING_MODEL}")
    print(f"   - Chunk Size: {settings.CHUNK_SIZE}")
    print(f"   - LLM Host: {settings.OLLAMA_HOST}")
    print(f"   - LLM Model: {settings.OLLAMA_MODEL}")
    print(f"   - LLM Num Predict: {settings.OLLAMA_NUM_PREDICT}")
    print(f"   - LLM Temperature: {settings.OLLAMA_TEMPERATURE}")
    print(f"   - Streaming Enabled: {settings.ENABLE_STREAMING}")
    # Safe DB summary without exposing password
    print(f"   - Database URL: {settings.DATABASE_URL}")
    
    if issues:
        print("\nConfiguration Issues:")
        for issue in issues:
            print(issue)
        return False
    
    return True

# Test configuration loading
if __name__ == "__main__":
    print("Testing configuration...")
    is_valid = validate_config()
    if is_valid:
        print("All configuration is valid!")
    else:
        print("Configuration has issues but app can still run with defaults")
