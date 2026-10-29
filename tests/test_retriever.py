"""Tests for src.retriever (FAISS index, gating, persistence)."""

from __future__ import annotations

import numpy as np
import pytest

from src.retriever import FaissRetriever
from src.text_chunker import Chunk


def _chunk(doc_id: str = "doc_a", index: int = 0) -> Chunk:
    return Chunk(
        chunk_id=f"{doc_id}::p1::c{index}",
        doc_id=doc_id,
        page_number=1,
        text=f"text {index}",
        index=index,
    )


def _unit(dim: int, hot: int) -> np.ndarray:
    vector = np.zeros(dim, dtype=np.float32)
    vector[hot] = 1.0
    return vector


class TestConstruction:
    def test_add_shape_validation(self):
        retriever = FaissRetriever(dimension=4)
        with pytest.raises(ValueError, match="expected embeddings"):
            retriever.add(np.zeros((2, 5), dtype=np.float32), [_chunk()])

    def test_add_count_validation(self):
        retriever = FaissRetriever(dimension=4)
        with pytest.raises(ValueError, match="mismatch"):
            retriever.add(np.zeros((2, 4), dtype=np.float32), [_chunk()])

    def test_bad_dimension(self):
        with pytest.raises(ValueError, match="dimension"):
            FaissRetriever(dimension=0)


class TestSearch:
    def test_empty_index_returns_nothing(self):
        retriever = FaissRetriever(dimension=4)
        assert retriever.search(_unit(4, 0)) == []

    def test_ordering_by_similarity(self):
        retriever = FaissRetriever(dimension=4, min_score=0.0)
        embeddings = np.stack([_unit(4, 0), _unit(4, 1), _unit(4, 2)])
        chunks = [_chunk(index=i) for i in range(3)]
        retriever.add(embeddings, chunks)

        query = np.array([0.9, 0.1, 0.0, 0.0], dtype=np.float32)
        query /= np.linalg.norm(query)
        results = retriever.search(query, top_k=3)
        assert [r.chunk.index for r in results] == [0, 1, 2]
        assert results[0].score > results[1].score > results[2].score

    def test_min_score_gate_filters_irrelevant(self):
        retriever = FaissRetriever(dimension=4, min_score=0.40)
        embeddings = np.stack([_unit(4, 0), _unit(4, 1)])
        retriever.add(embeddings, [_chunk(index=0), _chunk(index=1)])

        results = retriever.search(_unit(4, 0), top_k=2)
        assert len(results) == 1, "orthogonal vector must be gated out"
        assert results[0].chunk.index == 0
        assert results[0].score == pytest.approx(1.0, abs=1e-5)

    def test_bad_top_k(self):
        retriever = FaissRetriever(dimension=4)
        with pytest.raises(ValueError, match="top_k"):
            retriever.search(_unit(4, 0), top_k=0)


class TestPersistence:
    def test_save_load_roundtrip(self, tmp_path):
        retriever = FaissRetriever(dimension=4, min_score=0.3)
        retriever.add(np.stack([_unit(4, 0)]), [_chunk()])
        index_path = tmp_path / "index.bin"
        chunks_path = tmp_path / "chunks.jsonl"
        retriever.save(index_path, chunks_path)

        loaded = FaissRetriever.load(index_path, chunks_path, min_score=0.3)
        assert loaded.size == 1
        results = loaded.search(_unit(4, 0), top_k=1)
        assert results[0].chunk.chunk_id == "doc_a::p1::c0"
        assert results[0].score == pytest.approx(1.0, abs=1e-5)

    def test_missing_index_raises_with_guidance(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="Build it first"):
            FaissRetriever.load(tmp_path / "nope.bin", tmp_path / "nope.jsonl")

    def test_manifest_count_mismatch_raises(self, tmp_path):
        retriever = FaissRetriever(dimension=4)
        retriever.add(np.stack([_unit(4, 0), _unit(4, 1)]), [_chunk(index=0), _chunk(index=1)])
        index_path = tmp_path / "index.bin"
        chunks_path = tmp_path / "chunks.jsonl"
        retriever.save(index_path, chunks_path)
        # Truncate manifest to simulate corruption.
        lines = chunks_path.read_text(encoding="utf-8").splitlines()
        chunks_path.write_text(lines[0] + "\n", encoding="utf-8")
        with pytest.raises(ValueError, match="corrupt index/manifest"):
            FaissRetriever.load(index_path, chunks_path)
