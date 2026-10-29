"""FAISS-backed retrieval with an abstention gate.

Uses ``faiss.IndexFlatIP`` (exact inner-product search) over L2-normalized
embeddings, which equals cosine similarity. Exact search is affordable at
this project's scale (hundreds to low thousands of chunks) and is fully
deterministic — no ANN recall randomness in evaluation.

The ``min_score`` gate is what enables honest abstention: when no candidate
passes the threshold, the pipeline reports insufficient evidence instead of
forcing a top-k answer from unrelated text.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import faiss
import numpy as np

from src.text_chunker import Chunk


@dataclass(frozen=True)
class RetrievedPassage:
    """One retrieved chunk with its cosine similarity score."""

    chunk: Chunk
    score: float


class FaissRetriever:
    """Exact cosine-similarity retriever with a minimum-score gate."""

    def __init__(self, dimension: int, min_score: float = 0.40):
        if dimension <= 0:
            raise ValueError(f"dimension must be positive, got {dimension}")
        self.dimension = dimension
        self.min_score = min_score
        self._index = faiss.IndexFlatIP(dimension)
        self._chunks: list[Chunk] = []

    @property
    def size(self) -> int:
        return len(self._chunks)

    def add(self, embeddings: np.ndarray, chunks: list[Chunk]) -> None:
        """Add embeddings (float32, L2-normalized) paired with their chunks."""
        if embeddings.ndim != 2 or embeddings.shape[1] != self.dimension:
            raise ValueError(
                f"expected embeddings of shape (n, {self.dimension}), "
                f"got {embeddings.shape}"
            )
        if embeddings.shape[0] != len(chunks):
            raise ValueError(
                f"embedding/chunk count mismatch: {embeddings.shape[0]} vs {len(chunks)}"
            )
        if embeddings.shape[0] == 0:
            return
        self._index.add(np.asarray(embeddings, dtype=np.float32))
        self._chunks.extend(chunks)

    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> list[RetrievedPassage]:
        """Return top-k passages with score >= min_score, best first."""
        if top_k <= 0:
            raise ValueError(f"top_k must be positive, got {top_k}")
        if self.size == 0:
            return []

        query = np.asarray(query_embedding, dtype=np.float32).reshape(1, -1)
        scores, indices = self._index.search(query, min(top_k, self.size))
        results: list[RetrievedPassage] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:  # faiss pads with -1 when fewer candidates exist
                continue
            value = float(score)
            if value < self.min_score:
                continue
            results.append(RetrievedPassage(chunk=self._chunks[int(idx)], score=value))
        return results

    def save(self, index_path: Path, chunks_path: Path) -> None:
        """Persist the index and the chunk manifest (JSONL)."""
        index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(index_path))
        with chunks_path.open("w", encoding="utf-8") as fh:
            for chunk in self._chunks:
                fh.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")

    @classmethod
    def load(cls, index_path: Path, chunks_path: Path, min_score: float = 0.40) -> "FaissRetriever":
        """Load a saved index + chunk manifest."""
        if not index_path.exists():
            raise FileNotFoundError(
                f"FAISS index not found: {index_path}. Build it first "
                "(see README — index build step)."
            )
        if not chunks_path.exists():
            raise FileNotFoundError(f"Chunk manifest not found: {chunks_path}")

        index = faiss.read_index(str(index_path))
        retriever = cls(dimension=index.d, min_score=min_score)
        retriever._index = index
        with chunks_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                retriever._chunks.append(
                    Chunk(
                        chunk_id=record["chunk_id"],
                        doc_id=record["doc_id"],
                        page_number=int(record["page_number"]),
                        text=record["text"],
                        index=int(record["index"]),
                    )
                )
        if index.ntotal != len(retriever._chunks):
            raise ValueError(
                f"corrupt index/manifest: index has {index.ntotal} vectors "
                f"but manifest has {len(retriever._chunks)} chunks"
            )
        return retriever
