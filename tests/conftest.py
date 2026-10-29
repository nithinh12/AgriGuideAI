"""Shared pytest fixtures and test helpers for AgriGuide AI."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

# Make the project root importable regardless of how pytest is invoked.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.document_loader import Document, PageText  # noqa: E402

RAW_DIR = PROJECT_ROOT / "data" / "raw"
REAL_PDF = RAW_DIR / "tnau_agriculture.pdf"
SOURCES_JSONL = RAW_DIR / "sources.jsonl"


def make_document(
    doc_id: str = "test_doc",
    text: str = "Wheat requires irrigation at the tillering stage.",
    *,
    title: str = "Test Document",
    organization: str = "Test Organization",
    url: str = "https://example.org/test.pdf",
    page_number: int = 1,
) -> Document:
    """Build an in-memory Document for tests (no files involved)."""
    return Document(
        doc_id=doc_id,
        title=title,
        organization=organization,
        url=url,
        language="en",
        topics=("testing",),
        source_path=Path(f"{doc_id}.pdf"),
        pages=(PageText(page_number=page_number, text=text),),
        retrieved_date="2026-10-29",
    )


class FakeEmbedder:
    """Deterministic stand-in for src.embeddings.Embedder.

    Returns a fixed query vector so retriever/pipeline behaviour can be
    tested without downloading or running a real model.
    """

    def __init__(self, query_vector: np.ndarray):
        self._query_vector = np.asarray(query_vector, dtype=np.float32)
        self.dimension = int(self._query_vector.shape[0])

    def encode_query(self, query: str) -> np.ndarray:
        return self._query_vector


requires_real_pdf = pytest.mark.skipif(
    not REAL_PDF.exists(),
    reason="real knowledge-base PDF not present (data/raw/tnau_agriculture.pdf)",
)
