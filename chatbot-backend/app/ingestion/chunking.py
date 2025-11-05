# app/ingestion/chunking.py
from typing import List
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

def chunk_documents(
    docs: List[Document],
    chunk_size: int = 800,
    chunk_overlap: int = 100
) -> List[Document]:
    """
    Split long documents into smaller, overlapping chunks suitable for embedding.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", "!", "?", " "]
    )
    return splitter.split_documents(docs)
