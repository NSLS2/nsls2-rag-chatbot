# app/ingestion/loaders/api_loader.py
import os
import json
import requests
from langchain.schema import Document
from typing import List, Optional, Dict, Any
from app.utils.logger import get_logger
from app.config import settings

logger = get_logger(__name__)

def load_from_api(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    timeout: float = 15.0,
    pick_fields: Optional[List[str]] = None,
) -> List[Document]:
    """Fetch data from a REST API endpoint and return it as Document objects.

    Args:
        url: Endpoint URL.
        headers: Optional custom headers; merged with default USER_AGENT.
        params: Query parameters.
        timeout: Request timeout in seconds (default 15s).
        pick_fields: If JSON objects contain these keys, join their string values for text.
    """
    # Merge headers with a default USER_AGENT to be a good citizen
    default_ua = os.getenv("USER_AGENT", getattr(settings, "USER_AGENT", "chatbot-backend/0.1.0"))
    merged_headers = {"User-Agent": default_ua}
    if headers:
        merged_headers.update(headers)

    try:
        logger.debug(f"GET {url} params={params}")
        response = requests.get(url, headers=merged_headers, params=params, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.error(f"API request failed: {url} - {exc}")
        raise RuntimeError(f"API request failed for {url}: {exc}") from exc

    content_type = response.headers.get("Content-Type", "")

    # Try JSON first
    data: Any
    try:
        data = response.json()
    except ValueError:
        # Not JSON -> return raw text
        text = response.text or ""
        return [
            Document(
                page_content=text,
                metadata={
                    "source": url,
                    "type": "api",
                    "http_status": response.status_code,
                    "content_type": content_type,
                },
            )
        ]

    def to_text(obj: Any) -> str:
        if isinstance(obj, dict):
            if pick_fields:
                parts = []
                for k in pick_fields:
                    v = obj.get(k)
                    if isinstance(v, (str, int, float)):
                        parts.append(f"{k}: {v}")
                if parts:
                    return " | ".join(parts)
            # Fallback to common text-like keys
            for k in ("text", "content", "body", "message", "description"):
                v = obj.get(k)
                if isinstance(v, str) and v.strip():
                    return v
        # Final fallback: compact JSON
        return json.dumps(obj, ensure_ascii=False)

    docs: List[Document] = []
    if isinstance(data, list):
        for item in data:
            docs.append(
                Document(
                    page_content=to_text(item),
                    metadata={
                        "source": url,
                        "type": "api",
                        "http_status": response.status_code,
                        "content_type": content_type,
                    },
                )
            )
    else:
        docs.append(
            Document(
                page_content=to_text(data),
                metadata={
                    "source": url,
                    "type": "api",
                    "http_status": response.status_code,
                    "content_type": content_type,
                },
            )
        )

    return docs
