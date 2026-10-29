"""Embedding model wrapper for multilingual retrieval.

Uses ``intfloat/multilingual-e5-small`` (MIT license, 384 dimensions) with the
mandatory e5 input prefixes: documents are embedded as ``"passage: ..."``
and questions as ``"query: ..."``. Consistency between index-time and
query-time prefixes is essential — mixing them degrades retrieval quality.

All encoding runs on CPU by default (project constraint).
"""

from __future__ import annotations

import os
from pathlib import Path

# Keep the Hugging Face cache on the project drive BEFORE any HF library
# import, so model weights never land on C: by accident.
_DEFAULT_HF_HOME = Path(__file__).resolve().parents[1] / ".cache" / "huggingface"
os.environ.setdefault("HF_HOME", str(_DEFAULT_HF_HOME))

import numpy as np  # noqa: E402
from sentence_transformers import SentenceTransformer  # noqa: E402

E5_QUERY_PREFIX = "query: "
E5_PASSAGE_PREFIX = "passage: "


class Embedder:
    """CPU sentence-embedding wrapper with e5-style prefixes."""

    def __init__(self, model_name: str = "intfloat/multilingual-e5-small", device: str = "cpu"):
        self.model_name = model_name
        self.device = device
        self._model = SentenceTransformer(model_name, device=device)

    @property
    def dimension(self) -> int:
        # Name changed across sentence-transformers versions; support both.
        if hasattr(self._model, "get_embedding_dimension"):
            return int(self._model.get_embedding_dimension())
        return int(self._model.get_sentence_embedding_dimension())

    def encode_passages(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        """Embed documents/passages (float32, L2-normalized)."""
        if not texts:
            return np.zeros((0, self.dimension), dtype=np.float32)
        prefixed = [E5_PASSAGE_PREFIX + text for text in texts]
        embeddings = self._model.encode(
            prefixed,
            batch_size=batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return np.asarray(embeddings, dtype=np.float32)

    def encode_query(self, query: str) -> np.ndarray:
        """Embed a single search query (float32, L2-normalized)."""
        embedding = self._model.encode(
            [E5_QUERY_PREFIX + query],
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return np.asarray(embedding[0], dtype=np.float32)
