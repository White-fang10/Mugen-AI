"""
bot/rag/retriever.py
─────────────────────────────────────────────────────────────────────────────
MUGEN AI — ChromaDB Vector Store & Retriever
══════════════════════════════════════════════════════════════════════════════
Uses sentence-transformers (all-MiniLM-L6-v2) as the embedding model — fully
local, no API cost, fast on CPU.

Provides:
  get_vectorstore()   — singleton Chroma client
  retrieve_policy()   — top-k similarity search returning (text, source) pairs
"""

from __future__ import annotations

import functools
from typing import List, Tuple

import structlog
from chromadb import Settings as ChromaSettings
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

from bot.config import get_settings

log = structlog.get_logger(__name__)
settings = get_settings()

_EMBED_MODEL = "all-MiniLM-L6-v2"
_COLLECTION  = "mugen_rulebook"


@functools.lru_cache(maxsize=1)
def _get_embeddings() -> HuggingFaceEmbeddings:
    """Lazy-load the embedding model (downloads on first call)."""
    log.info("loading_embeddings", model=_EMBED_MODEL)
    return HuggingFaceEmbeddings(
        model_name=_EMBED_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


@functools.lru_cache(maxsize=1)
def get_vectorstore() -> Chroma:
    """Return the singleton ChromaDB-backed vector store."""
    return Chroma(
        collection_name=_COLLECTION,
        embedding_function=_get_embeddings(),
        persist_directory=str(settings.chroma_persist_dir),
        client_settings=ChromaSettings(anonymized_telemetry=False),
    )


async def retrieve_policy(query: str, k: int | None = None) -> List[Tuple[str, str]]:
    """
    Retrieve the top-k most relevant policy chunks for a query.

    Returns a list of (text, source_filename) tuples.
    """
    top_k = k or settings.rag_top_k
    vs = get_vectorstore()

    try:
        results = vs.similarity_search(query, k=top_k)
        return [(doc.page_content, doc.metadata.get("source", "unknown")) for doc in results]
    except Exception as exc:
        log.warning("rag_retrieval_failed", error=str(exc))
        return []
