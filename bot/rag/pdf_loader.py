"""
bot/rag/pdf_loader.py
─────────────────────────────────────────────────────────────────────────────
MUGEN AI — PDF Ingestion Pipeline
══════════════════════════════════════════════════════════════════════════════
Workflow:
  1. Parse PDF with PyMuPDF (fitz) — extracts clean text block by block
  2. Chunk with RecursiveCharacterTextSplitter (512 tokens, 64 overlap)
  3. Embed with sentence-transformers all-MiniLM-L6-v2 (local, no API cost)
  4. Upsert into ChromaDB with source metadata
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import List

import fitz  # PyMuPDF
import structlog
from langchain.schema import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from bot.config import get_settings
from bot.rag.retriever import get_vectorstore

log = structlog.get_logger(__name__)
settings = get_settings()

_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=64,
    length_function=len,
    separators=["\n\n", "\n", ". ", " ", ""],
)


def _extract_text(pdf_path: Path) -> str:
    """Extract all text from a PDF using PyMuPDF."""
    text_parts: List[str] = []
    with fitz.open(str(pdf_path)) as doc:
        for page in doc:
            text_parts.append(page.get_text("text"))
    return "\n\n".join(text_parts)


async def ingest_pdf(pdf_path: Path) -> int:
    """
    Ingest a PDF rulebook into ChromaDB.

    Returns the number of chunks stored.
    """
    log.info("ingesting_pdf", path=str(pdf_path))

    raw_text = _extract_text(pdf_path)
    if not raw_text.strip():
        raise ValueError(f"No extractable text in {pdf_path.name}")

    # Split into chunks
    chunks = _SPLITTER.split_text(raw_text)

    # Build LangChain Document objects with metadata
    file_hash = hashlib.md5(pdf_path.read_bytes()).hexdigest()
    docs = [
        Document(
            page_content=chunk,
            metadata={
                "source": pdf_path.name,
                "file_hash": file_hash,
                "chunk_index": i,
            },
        )
        for i, chunk in enumerate(chunks)
    ]

    # Upsert into Chroma
    vs = get_vectorstore()
    vs.add_documents(docs)

    log.info("pdf_ingested", file=pdf_path.name, chunks=len(docs))
    return len(docs)
