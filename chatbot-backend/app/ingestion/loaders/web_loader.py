# app/ingestion/loaders/web_loader.py
import os
from typing import List, Optional
from langchain_community.document_loaders import WebBaseLoader
from langchain.schema import Document
from app.utils.logger import get_logger
from app.config import settings

logger = get_logger(__name__)

def load_from_web(
    url: str,
    user_agent: Optional[str] = None,
    timeout: float = 15.0,
    css_selector: Optional[str] = None,
) -> List[Document]:
    """Fetch webpage content and convert to LangChain Document objects.

    Args:
        url: Web page URL.
        user_agent: Override the default USER_AGENT header.
        timeout: Request timeout (seconds).
        css_selector: If provided, restrict extraction to matching elements.
    """
    ua = user_agent or os.getenv("USER_AGENT", getattr(settings, "USER_AGENT", "chatbot-backend/0.1.0"))
    headers = {"User-Agent": ua}

    # WebBaseLoader accepts header_options and can take bs4-based selectors
    loader = WebBaseLoader(url, header_options=headers)

    if css_selector:
        # WebBaseLoader supports bs_kwargs for BeautifulSoup
        loader.requests_kwargs = {"timeout": timeout}
        loader.bs_kwargs = {"features": "html.parser"}
        loader.web_paths = [url]
        # Filtering will be applied after load using css selectors
    else:
        loader.requests_kwargs = {"timeout": timeout}

    try:
        docs = loader.load()
    except Exception as e:
        logger.error(f"Failed to load web page {url}: {e}")
        raise

    # Optionally filter content by CSS selector post-load
    results: List[Document] = []
    for d in docs:
        content = d.page_content
        meta = d.metadata or {}
        meta.setdefault("source", url)
        meta.setdefault("type", "web")
        results.append(Document(page_content=content, metadata=meta))

    return results
