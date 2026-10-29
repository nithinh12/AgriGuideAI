"""Tests for src.text_chunker."""

from __future__ import annotations

import pytest

from src.text_chunker import (
    Chunk,
    chunk_document,
    chunk_documents,
    normalize_text,
    split_sentences,
)
from tests.conftest import make_document


class TestNormalize:
    def test_collapses_whitespace_and_blank_lines(self):
        assert normalize_text("a \t b\n\n\n\nc") == "a b\n\nc"

    def test_handles_nbsp(self):
        assert normalize_text("urea\u00a0dap") == "urea dap"


class TestSentences:
    def test_splits_english(self):
        sentences = split_sentences("Wheat needs water. Maize needs less. Rice needs more.")
        assert sentences == ["Wheat needs water.", "Maize needs less.", "Rice needs more."]

    def test_empty_input(self):
        assert split_sentences("   ") == []


class TestChunking:
    def test_single_short_page_becomes_one_chunk(self):
        document = make_document(text="Urea contains 46 percent nitrogen.")
        chunks = chunk_document(document, chunk_size=512, chunk_overlap=64)
        assert len(chunks) == 1
        assert chunks[0].text == "Urea contains 46 percent nitrogen."
        assert chunks[0].page_number == 1
        assert chunks[0].doc_id == "test_doc"
        assert chunks[0].chunk_id == "test_doc::p1::c0"

    def test_word_windows_with_overlap(self):
        text = " ".join(
            f"S{i} w{i} x{i} y{i} z{i}." for i in range(4)
        )  # 4 sentences x 5 words = 20 words (capitalized: sentence-split
        # regex is intentionally conservative and only splits before
        # uppercase/digit/Indic starts)
        document = make_document(text=text)
        chunks = chunk_document(document, chunk_size=10, chunk_overlap=3)
        words = [c.text.split() for c in chunks]
        assert len(chunks) == 2, f"expected 2 chunks, got {len(words)}"
        assert len(words[0]) == 10
        # Window 2 starts 3 words before window 1 ended (overlap = 3).
        assert words[1][:3] == words[0][-3:]
        assert words[1][3:6] != words[0][-3:]  # progress was made
        # All original words are covered somewhere.
        covered = " ".join(c.text for c in chunks)
        for i in range(4):
            assert f"S{i}" in covered

    def test_every_sentence_appears_in_some_chunk(self):
        document = make_document(
            text="First sentence here. Second one follows. Third closes it."
        )
        chunks = chunk_document(document, chunk_size=4, chunk_overlap=1)
        joined = " ".join(c.text for c in chunks)
        for sentence in ("First sentence here.", "Second one follows.", "Third closes it."):
            assert sentence in joined

    def test_oversized_sentence_kept_whole(self):
        long_sentence = " ".join(["word"] * 30) + "."
        document = make_document(text=long_sentence)
        chunks = chunk_document(document, chunk_size=10, chunk_overlap=2)
        assert len(chunks) == 1
        assert chunks[0].text == long_sentence, "must not truncate a long sentence"

    def test_validation(self):
        document = make_document()
        with pytest.raises(ValueError, match="chunk_size"):
            chunk_document(document, chunk_size=0, chunk_overlap=0)
        with pytest.raises(ValueError, match="chunk_overlap"):
            chunk_document(document, chunk_size=10, chunk_overlap=10)

    def test_deterministic(self):
        document = make_document(text="Alpha beta gamma. Delta epsilon zeta.")
        first = chunk_document(document, chunk_size=4, chunk_overlap=1)
        second = chunk_document(document, chunk_size=4, chunk_overlap=1)
        assert first == second

    def test_chunk_documents_sorts_by_doc_id(self):
        docs = [make_document("bbb"), make_document("aaa")]
        chunks = chunk_documents(docs)
        assert [c.doc_id for c in chunks] == ["aaa", "bbb"]
        assert all(isinstance(c, Chunk) for c in chunks)
