# app/ingestion/loaders/file_loader.py
import os
import json
import subprocess
import pandas as pd
from typing import List
from langchain.schema import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredWordDocumentLoader,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

# -------------------- Format-Specific Loader Functions --------------------

def load_pdf(path: str) -> List[Document]:
    loader = PyPDFLoader(path)
    return loader.load()

def load_text(path: str) -> List[Document]:
    # Autodetect encoding to avoid UnicodeDecodeError on mixed encodings
    loader = TextLoader(path, autodetect_encoding=True)
    return loader.load()

def load_word(path: str) -> List[Document]:
    loader = UnstructuredWordDocumentLoader(path)
    return loader.load()

def load_csv(path: str) -> List[Document]:
    # Read as strings to avoid NaN/float coercion; skip bad lines to keep going
    df = pd.read_csv(
        path,
        dtype=str,
        keep_default_na=False,
        na_filter=False,
        low_memory=False,
        # on_bad_lines='skip'  # uncomment for pandas>=1.3 if needed
    )
    documents = []
    for _, row in df.iterrows():
        content = " | ".join(f"{col}: {row[col]}" for col in df.columns)
        documents.append(
            Document(
                page_content=content,
                metadata={"source": path, "type": "csv"},
            )
        )
    return documents

def load_json(path: str) -> List[Document]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    def pick_text(obj):
        if isinstance(obj, dict):
            # Prefer common text fields; fallback to compact JSON
            for key in ("text", "content", "body", "message"):
                if key in obj and isinstance(obj[key], str):
                    return obj[key]
        return json.dumps(obj, ensure_ascii=False)

    docs: List[Document] = []
    if isinstance(data, list):
        for entry in data:
            docs.append(Document(page_content=pick_text(entry), metadata={"source": path, "type": "json"}))
    else:
        docs.append(Document(page_content=pick_text(data), metadata={"source": path, "type": "json"}))
    return docs

def load_php(path: str) -> List[Document]:
    """Execute PHP file and capture its output (guarded)."""
    allow = os.getenv("ALLOW_PHP_EXEC", "false").lower() == "true"
    if not allow:
        raise RuntimeError("PHP execution disabled. Set ALLOW_PHP_EXEC=true to enable (use with caution).")
    try:
        output = subprocess.check_output(
            ["php", path],
            stderr=subprocess.STDOUT,
            text=True,
            timeout=10,
        )
        return [
            Document(
                page_content=output.strip(),
                metadata={"source": path, "type": "php", "executed": True},
            )
        ]
    except FileNotFoundError:
        raise RuntimeError("PHP runtime not found. Install PHP or disable PHP execution.")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"PHP execution timed out for: {path}")
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"PHP execution failed for {path}: {exc.output.strip()}")

# -------------------- Dispatcher Function --------------------

def load_file(path: str) -> List[Document]:
    """Dispatch file loading based on file extension."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")

    extension = os.path.splitext(path)[1].lower()
    loaders = {
        ".pdf": load_pdf,
        ".txt": load_text,
        ".md": load_text,
        ".doc": load_word,
        ".docx": load_word,
        ".csv": load_csv,
        ".json": load_json,
        ".php": load_php,
    }

    if extension not in loaders:
        raise ValueError(f"Unsupported file type: {extension}")

    try:
        documents = loaders[extension](path)
    except Exception as e:
        logger.error(f"Failed to load {path}: {e}")
        raise

    # Standardize metadata
    filename = os.path.basename(path)
    for doc in documents:
        doc.metadata.setdefault("source", path)
        doc.metadata.setdefault("type", extension)
        doc.metadata.setdefault("filename", filename)
        doc.metadata.setdefault("extension", extension)

    return documents
