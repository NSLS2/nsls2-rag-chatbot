import os
from typing import List, Optional

from app.ingestion.vector_store import search_qdrant


class RAGSearchQdrant:
    """
    Simple RAG search helper over Qdrant.

    - Uses sentence-transformer embeddings (via vector_store helpers) to search
    - Optionally summarizes results using Groq (if langchain_groq is installed and GROQ_API_KEY is set)
    """

    def __init__(self, collection_name: str = "default_docs") -> None:
        self.collection = collection_name

        # Try to initialize Groq LLM lazily (optional)
        self._llm = None
        self._llm_name = None

    def _get_llm(self):
        if self._llm is not None:
            return self._llm
        groq_api_key = os.getenv("GROQ_API_KEY", "")
        llm_model = os.getenv("GROQ_MODEL", "gemma2-9b-it")
        if groq_api_key:
            try:
                from langchain_groq import ChatGroq

                self._llm = ChatGroq(groq_api_key=groq_api_key, model_name=llm_model)
                self._llm_name = llm_model
                print(f"[INFO] Groq LLM initialized: {llm_model}")
            except Exception as e:
                print(f"[WARN] Groq LLM not available: {e}")
                self._llm = None
        return self._llm

    def search(self, query: str, top_k: int = 5) -> List[dict]:
        """
        Return top_k Qdrant results as a list of dicts: {id, score, payload}
        """
        results = search_qdrant(
            query=query,
            collection_name=self.collection,
            top_k=top_k,
            with_payload=True,
            with_vectors=False,
        )
        return results

    def search_and_summarize(self, query: str, top_k: int = 5) -> str:
        results = self.search(query, top_k=top_k)
        texts = []
        for r in results:
            payload = r.get("payload") or {}
            text = payload.get("text")
            if text:
                texts.append(text)

        if not texts:
            return "No relevant documents found."

        # If LLM available, generate a short summary
        llm = self._get_llm()
        if llm:
            context = "\n\n".join(texts)
            prompt = (
                f"Summarize the following context for the query: '{query}'\n\n"
                f"Context:\n{context}\n\nSummary:"
            )
            try:
                response = llm.invoke([prompt])
                # langchain-groq returns a message; access .content
                return getattr(response, "content", str(response))
            except Exception as e:
                return f"[WARN] Summarization failed: {e}\n\nTop snippets:\n- " + "\n- ".join(t[:200] for t in texts)

        # Fallback: return top snippets
        return "Top snippets:\n- " + "\n- ".join(t[:200] for t in texts)


if __name__ == "__main__":
    # Minimal demo
    rag = RAGSearchQdrant(collection_name=os.getenv("QDRANT_COLLECTION", "default_docs"))
    q = os.getenv("QUERY", "What is RAG?")
    print("[DEMO] Query:", q)
    print("[DEMO] Results (ids, scores):")
    res = rag.search(q, top_k=3)
    for r in res:
        print(" -", r.get("id"), r.get("score"))
    print("\n[DEMO] Summary:")
    print(rag.search_and_summarize(q, top_k=3))
