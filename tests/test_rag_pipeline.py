"""Tests for src.rag_pipeline (grounding, abstention, citation invariants)."""

from __future__ import annotations

import numpy as np
import pytest

from src.rag_pipeline import (
    ABSTAIN_MESSAGE,
    ExtractiveEvidenceGenerator,
    RAGPipeline,
)
from src.retriever import FaissRetriever
from src.text_chunker import Chunk
from tests.conftest import FakeEmbedder, make_document


def _pipeline(min_score: float = 0.4, top_k: int = 2, query_vector=None):
    """Build a pipeline over two synthetic chunks with a fixed query vector."""
    relevant_doc = make_document(
        "wheat_guide",
        "Wheat irrigation is required at tillering and flowering stages.",
        title="Wheat Production Guide",
        organization="Test Agricultural University",
        url="https://example.org/wheat.pdf",
    )
    other_doc = make_document(
        "bank_info",
        "Banks provide crop loans to farmers at subsidised interest.",
        title="Banking Circular",
        organization="Test Bank",
        url="https://example.org/bank.pdf",
    )
    retriever = FaissRetriever(dimension=3, min_score=min_score)
    embeddings = np.array(
        [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float32
    )
    retriever.add(
        embeddings,
        [
            Chunk("wheat_guide::p1::c0", "wheat_guide", 1, "Wheat irrigation is required at tillering and flowering stages.", 0),
            Chunk("bank_info::p1::c0", "bank_info", 1, "Banks provide crop loans to farmers at subsidised interest.", 0),
        ],
    )
    embedder = FakeEmbedder(
        np.array([1.0, 0.0, 0.0], dtype=np.float32)
        if query_vector is None
        else np.asarray(query_vector, dtype=np.float32)
    )
    pipeline = RAGPipeline(
        retriever=retriever,
        embedder=embedder,
        documents_by_id={"wheat_guide": relevant_doc, "bank_info": other_doc},
        generator=ExtractiveEvidenceGenerator(),
        top_k=top_k,
    )
    return pipeline


class TestAnsweredPath:
    def test_answer_carries_sources_and_metadata(self):
        result = _pipeline().answer("When should wheat be irrigated?")
        assert result.mode == "answered"
        assert result.answer_kind == "extractive_evidence"
        assert len(result.sources) >= 1

        top = result.sources[0]
        assert top.doc_id == "wheat_guide"
        assert top.title == "Wheat Production Guide"
        assert top.organization == "Test Agricultural University"
        assert top.url == "https://example.org/wheat.pdf"
        assert top.page_number == 1
        assert "irrigation" in top.excerpt.lower()
        assert top.score >= 0.4

    def test_extractive_answer_quotes_evidence_only(self):
        result = _pipeline().answer("When should wheat be irrigated?")
        assert "tillering" in result.answer_text, (
            "extractive answer must contain the retrieved evidence sentence"
        )

    def test_answered_result_never_has_empty_sources(self):
        result = _pipeline().answer("irrigation of wheat")
        if result.mode == "answered":
            assert result.sources


class TestAbstention:
    def test_gate_triggers_abstention(self):
        # A query orthogonal to every stored chunk scores 0.0 against all of
        # them; with min_score=0.99 nothing passes the gate.
        result = _pipeline(min_score=0.99, query_vector=[0.0, 0.0, 1.0]).answer(
            "Quantum physics of black holes?"
        )
        assert result.mode == "abstained"
        assert result.sources == ()
        assert result.answer_text == ABSTAIN_MESSAGE
        assert "consult" in result.answer_text.lower()

    def test_empty_question_abstains(self):
        result = _pipeline().answer("   ")
        assert result.mode == "abstained"
        assert "empty question" in result.warnings


class TestInvariants:
    def test_unknown_document_reference_raises(self):
        pipeline = _pipeline()
        # Remove the cited document to force the phantom-source path.
        pipeline.documents_by_id.pop("wheat_guide")
        with pytest.raises(KeyError, match="unknown document 'wheat_guide'"):
            pipeline.answer("When should wheat be irrigated?")
