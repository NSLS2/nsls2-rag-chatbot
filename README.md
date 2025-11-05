# RAG-based Chat Application

A full-stack application for building multi-tenant, document-aware chatbots with Retrieval-Augmented Generation (RAG). Features a FastAPI backend with local LLM support and a React frontend with real-time streaming.

## Project Structure

```
.
├── chatbot-backend/          # FastAPI RAG backend
│   ├── app/
│   │   ├── routes/          # API endpoints
│   │   ├── services/        # LLM, RAG implementation
│   │   ├── models/          # Database models
│   │   └── ingestion/       # Document processing
│   └── README.md            # Backend documentation
│
├── chatbot-frontend/         # React/TypeScript frontend
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── store/          # State management
│   │   └── lib/            # Utilities
│   └── README.md            # Frontend documentation
│
└── docker-compose.yml       # Development environment
```

## Features

### Backend
- Multi-tenant support with isolated document collections
- Document ingestion and vectorization
- Local LLM integration (Ollama)
- Real-time response streaming
- Chat history and feedback persistence
- Analytics and document management

### Frontend
- Clean, responsive UI
- Real-time chat with typing indicators
- Document upload and management
- Application switching
- Analytics dashboard
- User feedback collection

## Tech Stack

- Backend:
  - FastAPI (Python)
  - PostgreSQL (persistence)
  - Qdrant (vector store)
  - Ollama (local LLM)
  - SentenceTransformers

- Frontend:
  - React 18
  - TypeScript
  - Tailwind CSS
  - Zustand (state)
  - Vite

## Quick Start (Local Dev)

### 0. Prerequisites

Install or have available:

- Docker Desktop
- Node.js 18+ and npm
- Pixi (Python environment manager) – install via:
  - PowerShell: `iwr -UseBasicParsing https://pixi.sh/install.ps1 | iex`
- (Optional) Ollama for local LLM: <https://ollama.ai>

### 1. Clone & Infra

From the project root start only infrastructure services (Postgres + Qdrant):

```powershell
docker compose up -d
```

### 2. Backend Environment

Create / adjust backend `.env` (or rely on pixi task inline env). Place this file at the root of the backend service:

```text
chatbot-backend/.env
```

**💡 Tip:** Check `chatbot-backend/.env.local.example` for a comprehensive list of all available environment variables with example values.

Guidelines:

1. Path must be exactly `chatbot-backend/.env` (same directory as `pixi.toml`).
2. Loading is automatic because `[tool.pixi.environment]` has `dotenv = true`.
3. Do not commit secrets (add to `.gitignore` if you add tokens later).
4. You can override variables temporarily per command using `pixi run dev` with task-defined env.
5. If values change, restart the backend process (FastAPI won't reload changed env automatically for already-imported settings objects).

```env
DATABASE_URL=postgresql+psycopg://raguser:ragpass@localhost:5433/ragdb
QDRANT_HOST=localhost
QDRANT_PORT=6333
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=phi3:3.8b
```

Install dependencies & start API (auto-reload):

```powershell
cd chatbot-backend
pixi install
pixi run dev      # or: pixi run serve (no reload)
```

### 3. Folder Structure

Project layout (mirrors current repository):

```text
chatbot-backend/
  app/
    routes/        # FastAPI endpoints
    services/      # RAG + LLM orchestration
    models/        # SQLAlchemy models
    ingestion/     # (Optional) document loaders & preprocessing
  pixi.toml        # Python env + tasks
chatbot-frontend/
  src/
    components/    # UI components
    store/         # Zustand state
    lib/           # Utilities / helpers
docker-compose.yml # Postgres + Qdrant infra only
```

### 4. Database Setup

Start containers (Postgres on 5433 host port, Qdrant on 6333/6334):

```powershell
docker compose up -d
```

Default connection string used by backend tasks:

```text
postgresql+psycopg://raguser:ragpass@localhost:5433/ragdb
```

### 5. Ollama Setup (Local LLM)

The application uses Ollama to run local LLMs. Follow these steps to set up Ollama:

#### Install Ollama

1. **Download and install Ollama** from <https://ollama.ai>
2. **Start Ollama service** (usually starts automatically after installation)
3. **Verify installation**:
   ```powershell
   ollama --version
   ```

#### Pull a Model

Download a recommended model for the chatbot. The `phi3:3.8b` model provides a good balance of performance and resource usage:

```powershell
ollama pull phi3:3.8b
```

**Alternative models** (choose based on your hardware):
- `phi3:3.8b` - Recommended for most systems
- `llama3.2:1b` - Lighter model for low-resource systems
- `llama3.2:3b` - Balanced performance
- `mistral:7b` - High-quality model with good performance
- `gemma2:9b` - Higher quality but requires more resources

#### Verify Ollama is Running

Check that Ollama is accessible:

```powershell
curl http://localhost:11434/api/tags
```

You should see your downloaded models listed.

#### Environment Configuration

In your `.env` file, configure Ollama settings:

```env
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=phi3:3.8b
OLLAMA_TEMPERATURE=0.2
OLLAMA_NUM_PREDICT=128
```

### 6. Backend Setup

Install environment and run API (reload for development):

```powershell
cd chatbot-backend
pixi install
pixi run serve
```

Confirm API: <http://localhost:8000/docs>

### 7. Frontend Setup

```powershell
cd ../chatbot-frontend
npm install
npm run dev
```

Open UI: <http://localhost:5173>

### 8. Shutdown

```powershell
docker compose down -v
```

> NOTE: Backend & frontend are now run directly on the host (not in Docker). Only data & vector services use containers.

## Development

### Backend Development

The backend uses FastAPI with SQLAlchemy and runs on port 8000:

```bash
cd chatbot-backend
pixi run uvicorn app.main:app --reload --port 8000
```

API documentation: [http://localhost:8000/docs](http://localhost:8000/docs)

### Frontend Development

The frontend uses Vite and runs on port 5173:

```bash
cd chatbot-frontend
npm run dev
```

## Configuration

### Backend (.env example)

```env
APP_NAME=RAG Chatbot Backend
PORT=8000

# Connection string used by tasks (mirrors docker-compose mapped port 5433)
DATABASE_URL=postgresql+psycopg://raguser:ragpass@localhost:5433/ragdb

# Vector store
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Local LLM (optional)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=phi3:3.8b
```

### Environment Tips (Windows + OneDrive)

- If Pixi install reports DLL lock errors, relocate its cache:

  ```powershell
  $env:PIXI_HOME="C:\dev\pixi"; New-Item -ItemType Directory -Force C:\dev\pixi | Out-Null
  pixi install
  ```

- Pause OneDrive sync during initial `pixi install` to avoid file locking.
- HuggingFace & SentenceTransformers are version-pinned in `pixi.toml` to prevent API incompatibilities.

### Frontend (.env)

```env
VITE_API_URL=http://localhost:8000
```

---
**Brookhaven National Laboratory - NSLS2**  
*National Synchrotron Light Source II*

# nsls2-template

This is a minimal template for new NSLS-II repositories.  It contains the approved BSD-3-Clause license together with additional text that should be included (LICENSE_README).  This text can appear at the bottom of the README.md if so desired.