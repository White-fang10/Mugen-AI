"""
bot/rag/retriever.py
─────────────────────────────────────────────────────────────────────────────
MUGEN AI — Stage 3: Upgraded ChromaDB Retriever
══════════════════════════════════════════════════════════════════════════════

What changed from Stage 2
──────────────────────────
  • retrieve_for_request() — new primary API replacing retrieve_policy().
    Takes asset_name + justification, builds a graded compound query,
    fetches top-3 chunks with scores, and returns a RagContext object.

  • Relevance grading — each chunk gets a letter grade (A–D) based on
    cosine similarity distance so the decision engine knows how much to
    trust the context:
        A  distance ≤ 0.35  — highly relevant
        B  distance ≤ 0.50  — relevant
        C  distance ≤ 0.65  — marginally relevant
        D  distance  > 0.65  — low relevance (still included, but flagged)

  • has_rulebook() — lightweight check; returns False when ChromaDB is
    empty so the decision engine can warn users instead of silently
    using stale/absent context.

  • retrieve_policy() kept as a compatibility shim.

  • Singleton vectorstore + embeddings remain LRU-cached for efficiency.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import structlog
from chromadb import Settings as ChromaSettings
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

from bot.config import get_settings

log = structlog.get_logger(__name__)
settings = get_settings()

_EMBED_MODEL   = "all-MiniLM-L6-v2"
_COLLECTION    = "mugen_rulebook"
_DEFAULT_TOP_K = 3   # Stage 3 spec: fetch top-3 chunks

# ─────────────────────────────────────────────────────────────────────────────
# Relevance grading thresholds (cosine distance — lower is better)
# ─────────────────────────────────────────────────────────────────────────────

_GRADE_THRESHOLDS: list[tuple[float, str]] = [
    (0.35, "A"),
    (0.50, "B"),
    (0.65, "C"),
]


def _grade(distance: float) -> str:
    for threshold, letter in _GRADE_THRESHOLDS:
        if distance <= threshold:
            return letter
    return "D"


# ─────────────────────────────────────────────────────────────────────────────
# Result models
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PolicyChunk:
    """A single retrieved policy chunk with relevance metadata."""
    text:     str
    source:   str          # filename
    page:     int          # page number (1-indexed)
    distance: float        # cosine distance (0 = identical, 2 = opposite)
    grade:    str          # A / B / C / D
    chunk_idx: int = 0

    def format_for_llm(self) -> str:
        """Render as a block the decision-engine LLM can reference."""
        return (
            f"[Relevance: {self.grade} | Source: {self.source}, p.{self.page}]\n"
            f"{self.text}"
        )

    def format_for_user(self) -> str:
        """Short citation for Telegram messages."""
        return f"_{self.source}_ p.{self.page} (Grade {self.grade})"


@dataclass
class RagContext:
    """
    Aggregated RAG retrieval result for a single asset request.

    Passed directly into the decision engine.
    """
    query:   str
    chunks:  List[PolicyChunk] = field(default_factory=list)
    empty:   bool = False       # True when no rulebooks are indexed yet

    @property
    def has_strong_signal(self) -> bool:
        """True if at least one Grade-A or Grade-B chunk was retrieved."""
        return any(c.grade in ("A", "B") for c in self.chunks)

    def to_llm_context(self) -> str:
        """
        Format the retrieved chunks into a block ready for LLM injection.
        Includes a provenance summary so the LLM can cite sources properly.
        """
        if self.empty or not self.chunks:
            return (
                "⚠️ No policy rulebooks have been indexed yet.\n"
                "Decision must be based on static policy rules only."
            )

        header = (
            f"Retrieved {len(self.chunks)} policy chunk(s) for query: \"{self.query}\"\n"
            f"Signal strength: {'STRONG' if self.has_strong_signal else 'WEAK'}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        )
        body = "\n\n".join(c.format_for_llm() for c in self.chunks)
        return header + body

    def source_citations(self) -> List[str]:
        """Return de-duplicated list of source citations."""
        seen: set[str] = set()
        citations: List[str] = []
        for c in self.chunks:
            key = f"{c.source}:p{c.page}"
            if key not in seen:
                seen.add(key)
                citations.append(c.format_for_user())
        return citations


# ─────────────────────────────────────────────────────────────────────────────
# Singleton accessors
# ─────────────────────────────────────────────────────────────────────────────

@functools.lru_cache(maxsize=1)
def _get_embeddings() -> HuggingFaceEmbeddings:
    """Lazy-load the embedding model (downloads once on first call)."""
    log.info("loading_embeddings_model", model=_EMBED_MODEL)
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


# ─────────────────────────────────────────────────────────────────────────────
# Collection introspection
# ─────────────────────────────────────────────────────────────────────────────

def has_rulebook() -> bool:
    """Return True if at least one chunk has been indexed."""
    try:
        vs = get_vectorstore()
        col = vs._collection
        return col.count() > 0
    except Exception:
        return False


def get_indexed_sources() -> List[str]:
    """Return a de-duplicated list of indexed source filenames."""
    try:
        vs = get_vectorstore()
        col = vs._collection
        meta = col.get(include=["metadatas"])
        sources = {m.get("source", "unknown") for m in meta.get("metadatas", [])}
        return sorted(sources)
    except Exception:
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Primary retrieval API (Stage 3)
# ─────────────────────────────────────────────────────────────────────────────

async def retrieve_for_request(
    asset_name: str,
    justification: str = "",
    k: int = _DEFAULT_TOP_K,
) -> RagContext:
    """
    Retrieve the top-k most relevant policy chunks for an asset request.

    Constructs a compound query from asset name + justification to maximise
    semantic recall. Each chunk is graded A–D based on cosine distance.

    Parameters
    ----------
    asset_name : str
        The requested asset (e.g. "MacBook Pro 14").
    justification : str
        Business justification (e.g. "video editing workflow").
    k : int
        Number of chunks to retrieve (default 3 per Stage 3 spec).

    Returns
    -------
    RagContext
        Rich object with formatted chunks, grades, and source citations.
    """
    # Guard: return empty context if no rulebooks indexed
    if not has_rulebook():
        log.info("rag_no_rulebooks_indexed")
        return RagContext(
            query=asset_name,
            empty=True,
        )

    # Build a compound semantic query
    query_parts = [asset_name]
    if justification:
        query_parts.append(justification)
    # Also include policy-relevant terms for better recall
    query_parts.append("procurement policy approval budget limit")
    query = " ".join(filter(None, query_parts))

    try:
        vs = get_vectorstore()

        # similarity_search_with_relevance_scores returns (doc, score) where
        # score is cosine similarity (0–1, higher = more relevant).
        # We convert to distance = 1 - similarity for grading consistency.
        results = vs.similarity_search_with_relevance_scores(query, k=k)

        chunks: List[PolicyChunk] = []
        for doc, sim_score in results:
            distance = max(0.0, 1.0 - sim_score)
            chunks.append(PolicyChunk(
                text=doc.page_content,
                source=doc.metadata.get("source", "unknown"),
                page=int(doc.metadata.get("page", 0)),
                distance=round(distance, 4),
                grade=_grade(distance),
                chunk_idx=int(doc.metadata.get("chunk_index", 0)),
            ))

        # Sort by grade (A first)
        grade_order = {"A": 0, "B": 1, "C": 2, "D": 3}
        chunks.sort(key=lambda c: grade_order.get(c.grade, 4))

        log.info(
            "rag_retrieved",
            query=query[:80],
            chunks=len(chunks),
            grades=[c.grade for c in chunks],
        )

        return RagContext(query=asset_name, chunks=chunks)

    except Exception as exc:
        log.warning("rag_retrieval_failed", error=str(exc))
        return RagContext(query=asset_name, empty=True)


# ─────────────────────────────────────────────────────────────────────────────
# Compatibility shim (Stage 1/2 callers)
# ─────────────────────────────────────────────────────────────────────────────

async def retrieve_policy(
    query: str,
    k: Optional[int] = None,
) -> List[Tuple[str, str]]:
    """
    Legacy API. Returns List[(text, source)] tuples.
    New code should use retrieve_for_request() instead.
    """
    top_k = k or settings.rag_top_k
    ctx = await retrieve_for_request(asset_name=query, k=top_k)
    return [(c.text, c.source) for c in ctx.chunks]
