import os
import logging
from typing import List
from langchain.schema import Document
from app.ingestion.loaders import load_file, load_from_web, load_from_api


logger = logging.getLogger(__name__)

def ensure_documents(result) -> List[Document]:
    """Ensure all loaders return a list of valid LangChain Document objects."""
    if isinstance(result, Document):
        return [result]
    if isinstance(result, list) and all(isinstance(r, Document) for r in result):
        return result
    raise TypeError("Loader did not return valid Document objects.")

def load_any(source: str, **kwargs) -> List[Document]:
    """
    Universal data loader that converts any supported data source into LangChain Document objects.

    Supports:
        - Local files (PDF, TXT, DOCX, CSV, JSON, PHP)
        - Web URLs (HTML pages)
        - REST API endpoints (type='api')
    """
    logger.info(f"Loading source: {source}")

    if os.path.isfile(source):  # Local file path
        docs = load_file(source)
        return ensure_documents(docs)

    elif source.startswith(("http://", "https://")):
        if kwargs.get("type") == "api":
            docs = load_from_api(source, **kwargs)
        else:
            docs = load_from_web(source)
        return ensure_documents(docs)

    else:
        raise ValueError(f"Unsupported or invalid source: {source}")
