import os
from typing import List, Optional
from app.config import settings
import time


def _post_filter_answer(answer: str, context_text: str) -> str:
    """Conservatively sanitize the model's answer to only include facts present in context.

    If the answer contains sensitive qualifiers that are not present in the context (e.g.,
    'currently', 'expected', 'certified', 'gpa'), we return a neutral fallback.
    """
    a = (answer or "").strip()
    if not a:
        return a
    low_answer = a.lower()
    low_ctx = (context_text or "").lower()

    # Tokens that commonly indicate inference beyond records
    sensitive_tokens = [
        "currently",
        "expected",
        "certified",
        "certificate",
        "aws",
        "gpa",
        "completion",
    ]
    for tok in sensitive_tokens:
        if tok in low_answer and tok not in low_ctx:
            return "I don't have that information."

    # Prevent meta phrasing if it slips through
    if ("context" in low_answer and ("does not" in low_answer or "not mention" in low_answer)):
        return "I don't have that information."

    return a


# Removed Groq remote model support for a lean local-only setup.


def _get_chat_ollama_cls():
    """Return ChatOllama class from the preferred package if available.

    Tries langchain_ollama first (no deprecation), then falls back to
    langchain_community.chat_models.ChatOllama if needed.
    """
    try:
        from langchain_ollama import ChatOllama  # type: ignore

        return ChatOllama
    except Exception:
        try:
            from langchain_community.chat_models import ChatOllama  # type: ignore

            return ChatOllama
        except Exception:
            return None

# Cached Ollama client (reused across requests to avoid per-call init overhead)
_ollama_client = None
_ollama_model_name_cached = None

def _get_ollama_client():
    """Return a cached ChatOllama instance, initializing once if available.

    Applies model kwargs for performance: low temperature and limited num_predict.
    Uses env overrides OLLAMA_NUM_PREDICT / OLLAMA_TEMPERATURE if set.
    """
    global _ollama_client
    global _ollama_model_name_cached
    current_model = settings.OLLAMA_MODEL
    if _ollama_client is not None and _ollama_model_name_cached == current_model:
        return _ollama_client
    ChatOllama = _get_chat_ollama_cls()
    if ChatOllama is None:
        return None
    num_predict = getattr(settings, "OLLAMA_NUM_PREDICT", 128)
    temperature = getattr(settings, "OLLAMA_TEMPERATURE", 0.0)
    init_start = time.perf_counter()
    try:
        _ollama_client = ChatOllama(
            base_url=settings.OLLAMA_HOST,
            model=settings.OLLAMA_MODEL,
            model_kwargs={"num_predict": num_predict, "temperature": temperature},
        )
        _ollama_model_name_cached = current_model
        init_ms = (time.perf_counter() - init_start) * 1000.0
        try:
            from app.utils.logger import get_logger  # type: ignore
            get_logger(__name__).info(
                f"[llm] Ollama client initialized once init_ms={init_ms:.2f} num_predict={num_predict} temperature={temperature}"
            )
        except Exception:
            pass
    except Exception:
        _ollama_client = None
    return _ollama_client


def generate_answer(question: str, snippets: List[str], max_snippets: int = 5) -> str:
    """
    Generate an answer using available LLMs; fallback to a simple concatenation if none.
    """
    # Trim snippets to reasonable size
    use_snippets = []
    limit = getattr(settings, "SNIPPET_MAX_CHARS", 800)
    for s in snippets[:max_snippets]:
        if isinstance(s, str):
            trimmed = s[:limit]
            use_snippets.append(trimmed)
        else:
            use_snippets.append(s)

    # Log start of generation (best-effort, avoids hard dependency if logger import fails)
    try:
        from app.utils.logger import get_logger  # type: ignore
        get_logger(__name__).info(
            f"[llm] start generate_answer question_len={len(question)} snippets={len(use_snippets)} max_snippets={max_snippets}"
        )
    except Exception:
        pass

    # Updated guardrails: natural, human-like, grounded, and exact answers from records
    system_instructions = (
        "You are a knowledgeable and friendly assistant. "
        "Answer using ONLY the exact facts found in the provided records. Do not rephrase dates or statuses. "
        "Do not assume anything. "
        "Write in clear, human-readable language using short sentences. "
        "If you don’t find the answer, say: 'I don't have that information.' "
        "Do not mention 'records' or explain your process; respond with a short, direct answer only."
    )

    # Attempt local Ollama first if configured
    if use_snippets and getattr(settings, "OLLAMA_HOST", None):
        try:
            ollama = _get_ollama_client()
            if ollama is not None:
                context = "\n\n".join(use_snippets)
                try:
                    from langchain.schema import SystemMessage, HumanMessage  # type: ignore
                    messages = [
                        SystemMessage(content=system_instructions),
                        HumanMessage(content=f"Question: {question}\n\nRecords:\n{context}\n\nAnswer:"),
                    ]
                except Exception:
                    messages = [
                        f"{system_instructions}\n\nQuestion: {question}\n\nRecords:\n{context}\n\nAnswer:",
                    ]
                infer_start = time.perf_counter()
                timeout_ms = getattr(settings, "GENERATION_TIMEOUT_MS", 15000)
                msg = None
                try:
                    msg = ollama.invoke(messages)  # type: ignore[attr-defined]
                except Exception:
                    msg = None
                infer_ms = (time.perf_counter() - infer_start) * 1000.0
                # If inference exceeded timeout, abort with fallback snippet answer
                if infer_ms > timeout_ms and getattr(settings, "GENERATION_ENFORCE_TIMEOUT", True):
                    try:
                        from app.utils.logger import get_logger  # type: ignore
                        get_logger(__name__).warning(
                            f"[llm] Inference exceeded timeout ({infer_ms:.2f} ms > {timeout_ms} ms); enforcing fallback"
                        )
                    except Exception:
                        pass
                    if use_snippets:
                        best = use_snippets[0].strip()
                        return (best[:500] + ("…" if len(best) > 500 else "")) or "I don't have that information."
                elif infer_ms > timeout_ms:
                    # Soft timeout only: log but still return model output
                    try:
                        from app.utils.logger import get_logger  # type: ignore
                        get_logger(__name__).warning(
                            f"[llm] Inference exceeded timeout ({infer_ms:.2f} ms > {timeout_ms} ms) but ENFORCE disabled; returning model output"
                        )
                    except Exception:
                        pass
                try:
                    from app.utils.logger import get_logger  # type: ignore
                    get_logger(__name__).info(
                        f"[llm] Ollama inference_ms={infer_ms:.2f} model={settings.OLLAMA_MODEL}"
                    )
                except Exception:
                    pass
                if msg is not None:
                    content = getattr(msg, "content", None)
                    if isinstance(content, str) and content.strip():
                        text = _post_filter_answer(content.strip(), context)
                        return text
        except Exception:
            pass

    # Remote Groq path removed; fallback logic will trigger if local model not available.

    # Fallback: return the most relevant snippet
    if use_snippets:
        best = use_snippets[0].strip()
        summary = (best[:500] + ("…" if len(best) > 500 else ""))
        return summary or "I don't have that information."
    return "I don't have that information."


def stream_answer(question: str, snippets: List[str], max_snippets: int = 5):
    """Yield answer tokens/chunks incrementally.

    Falls back to single-shot generation if streaming not supported.
    Yields plain text chunks suitable for wrapping in SSE or a raw streaming response.
    """
    # Prepare trimmed snippets similar to generate_answer
    use_snippets = []
    limit = getattr(settings, "SNIPPET_MAX_CHARS", 800)
    for s in snippets[:max_snippets]:
        if isinstance(s, str):
            use_snippets.append(s[:limit])
        else:
            use_snippets.append(s)

    system_instructions = (
        "You are a knowledgeable and friendly assistant. "
        "Answer using ONLY the exact facts found in the provided records. Do not assume. "
        "Short, direct sentences. If unknown, say: 'I don't have that information.' "
        "Do not mention records or process."
    )

    if use_snippets and getattr(settings, "OLLAMA_HOST", None):
        ollama = _get_ollama_client()
        if ollama is not None:
            context = "\n\n".join(use_snippets)
            try:
                from langchain.schema import SystemMessage, HumanMessage  # type: ignore
                messages = [
                    SystemMessage(content=system_instructions),
                    HumanMessage(content=f"Question: {question}\n\nRecords:\n{context}\n\nAnswer:"),
                ]
            except Exception:
                messages = [
                    f"{system_instructions}\n\nQuestion: {question}\n\nRecords:\n{context}\n\nAnswer:",
                ]
            # Streaming path
            if hasattr(ollama, "stream"):
                infer_start = time.perf_counter()
                try:
                    for chunk in ollama.stream(messages):  # type: ignore[attr-defined]
                        # Extract text safely from different possible chunk object shapes
                        token = None
                        if isinstance(chunk, str):
                            token = chunk
                        else:
                            token = getattr(chunk, "content", None) or getattr(chunk, "text", None)
                        if token:
                            yield token
                    infer_ms = (time.perf_counter() - infer_start) * 1000.0
                    try:
                        from app.utils.logger import get_logger  # type: ignore
                        get_logger(__name__).info(
                            f"[llm-stream] Completed streaming inference_ms={infer_ms:.2f} model={settings.OLLAMA_MODEL}"
                        )
                    except Exception:
                        pass
                    return
                except Exception:
                    # Fall through to non-streaming single shot
                    pass
            # Non-streaming fallback
            try:
                msg = ollama.invoke(messages)  # type: ignore[attr-defined]
                content = getattr(msg, "content", None)
                if isinstance(content, str) and content.strip():
                    filtered = _post_filter_answer(content.strip(), context)
                    yield filtered
                    return
            except Exception:
                pass

    # Final fallback: yield first snippet summary
    if use_snippets:
        best = use_snippets[0].strip()
        yield (best[:500] + ("…" if len(best) > 500 else "")) or "I don't have that information."
    else:
        yield "I don't have that information."