"""Text cleaning and chunking for the retrieval pipeline.

Chunks must be small enough to be embedded and retrieved as standalone
evidence units, but large enough to keep agricultural recommendations intact
(schedules, fertilizer doses with their units, irrigation intervals).

Strategy (deterministic, no randomness):
1. normalize whitespace (never touching digits/units),
2. split into sentences with a conservative regex that also recognizes the
   Devanagari (। ॥) and Kannada (।) danda sentence enders,
3. greedily pack whole sentences into chunks of at most ``chunk_size`` words,
   prefixing each chunk with the last ``chunk_overlap`` words of the previous
   chunk as context.

A sentence longer than ``chunk_size`` words is kept as its own chunk —
truncating it could cut off a fertilizer quantity mid-recommendation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.document_loader import Document

# Sentence boundary: end punctuation followed by whitespace + (optional)
# closing quote/bracket) + capital/Devanagari/Kannada letter or digit, or
# start of a lowercase word that begins a new sentence is NOT split (conservative:
# false merges are recoverable, lost boundaries change nothing).
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?।॥])\s+(?=[A-Z0-9\u0900-\u097F\u0C80-\u0CFF])")

_WHITESPACE = re.compile(r"[ \t\r\f\v]+")


@dataclass(frozen=True)
class Chunk:
    """A retrievable text unit with a pointer back to its source."""

    chunk_id: str          # e.g. "tnau_agriculture::p3::c2"
    doc_id: str
    page_number: int       # 1-based page of origin
    text: str
    index: int             # sequential chunk number within the document


def normalize_text(text: str) -> str:
    """Collapse exotic whitespace and blank lines without touching content."""
    text = text.replace("\u00a0", " ")
    text = _WHITESPACE.sub(" ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_sentences(text: str) -> list[str]:
    """Split normalized text into sentences; never returns empty strings."""
    text = normalize_text(text)
    if not text:
        return []
    return [
        sentence.strip()
        for sentence in _SENTENCE_SPLIT.split(text)
        if sentence.strip()
    ]


def _pack_page(
    sentences: list[str], chunk_size: int, overlap: int
) -> list[str]:
    """Greedily pack sentences into <= chunk_size word chunks.

    Each chunk is prefixed with the last ``overlap`` words of the previously
    emitted chunk (context overlap). Oversized sentences are emitted as
    standalone chunks (never truncated).
    """
    chunks: list[str] = []
    carry: list[str] = []
    current: list[str] = []

    def emit() -> None:
        nonlocal current, carry
        if not current:
            return
        words = carry + current
        chunks.append(" ".join(words))
        carry = words[-overlap:] if overlap else []
        current = []

    for sentence in sentences:
        words = sentence.split()
        if len(words) > chunk_size:
            emit()
            chunks.append(" ".join(carry + words))
            combined = carry + words
            carry = combined[-overlap:] if overlap else []
            continue
        if len(current) + len(words) > chunk_size:
            emit()
        current.extend(words)
    emit()
    return chunks


def chunk_document(
    document: Document,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> list[Chunk]:
    """Chunk one document (per page, so page numbers stay citable)."""
    if chunk_size <= 0:
        raise ValueError(f"chunk_size must be positive, got {chunk_size}")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError(
            f"chunk_overlap must be in [0, chunk_size), got {chunk_overlap}"
        )

    chunks: list[Chunk] = []
    index = 0
    for page in document.pages:
        for text in _pack_page(split_sentences(page.text), chunk_size, chunk_overlap):
            text = text.strip()
            if not text:
                continue
            chunks.append(
                Chunk(
                    chunk_id=f"{document.doc_id}::p{page.page_number}::c{index}",
                    doc_id=document.doc_id,
                    page_number=page.page_number,
                    text=text,
                    index=index,
                )
            )
            index += 1
    return chunks


def chunk_documents(
    documents: list[Document],
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> list[Chunk]:
    """Chunk many documents; order is stable (documents sorted by doc_id)."""
    all_chunks: list[Chunk] = []
    for document in sorted(documents, key=lambda d: d.doc_id):
        all_chunks.extend(chunk_document(document, chunk_size, chunk_overlap))
    return all_chunks
