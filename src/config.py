"""Central configuration for AgriGuide AI.

Reads settings from environment variables and an optional ``.env`` file via
``python-dotenv``. Defaults are deterministic and CPU-friendly so that the
retrieval pipeline behaves identically across machines.

Secrets such as ``HF_TOKEN`` are loaded here but must never be logged or
printed (``repr`` of this class intentionally masks them).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Load .env from the project root (no-op if the file does not exist yet).
load_dotenv(PROJECT_ROOT / ".env")


def _split_languages(raw: str) -> tuple[str, ...]:
    """Parse a comma-separated language list; fall back to English."""
    langs = tuple(lang.strip().lower() for lang in raw.split(",") if lang.strip())
    return langs or ("en",)


@dataclass(frozen=True)
class Settings:
    """Immutable application settings resolved from env + defaults."""

    # Paths ------------------------------------------------------------------
    project_root: Path = PROJECT_ROOT
    data_raw_dir: Path = field(
        default_factory=lambda: PROJECT_ROOT / "data" / "raw"
    )
    data_processed_dir: Path = field(
        default_factory=lambda: PROJECT_ROOT / "data" / "processed"
    )

    # Hugging Face -----------------------------------------------------------
    # Token is required only for the gated IndicTrans2 checkpoints.
    hf_token: str | None = field(
        default_factory=lambda: os.getenv("HF_TOKEN") or None
    )

    # Models -----------------------------------------------------------------
    embedding_model: str = field(
        default_factory=lambda: os.getenv(
            "EMBEDDING_MODEL", "intfloat/multilingual-e5-small"
        )
    )
    # NOTE (2026-11-01): AgriParam was evaluated and NOT integrated. llm_model,
    # llm_dtype and llm_max_new_tokens are read by no code path (they only
    # appear in masked()); the AgriParam default is a leftover placeholder.
    # llm_device IS used: src/build_index.py passes it as the embedding device,
    # so do not rename or remove it. Defaults are unchanged on purpose.
    llm_model: str = field(
        default_factory=lambda: os.getenv("LLM_MODEL", "bharatgenai/AgriParam")
    )
    llm_device: str = field(default_factory=lambda: os.getenv("LLM_DEVICE", "cpu"))
    llm_dtype: str = field(
        default_factory=lambda: os.getenv("LLM_DTYPE", "bfloat16")
    )
    llm_max_new_tokens: int = field(
        default_factory=lambda: int(os.getenv("LLM_MAX_NEW_TOKENS", "200"))
    )

    # Translation ------------------------------------------------------------
    indic_translator_backend: str = field(
        default_factory=lambda: os.getenv("INDIC_TRANSLATOR_BACKEND", "shim")
    )

    # Retrieval --------------------------------------------------------------
    faiss_index_path: Path = field(
        default_factory=lambda: PROJECT_ROOT
        / os.getenv("FAISS_INDEX_PATH", "data/processed/faiss_index.bin")
    )
    chunk_size: int = field(
        default_factory=lambda: int(os.getenv("CHUNK_SIZE", "512"))
    )
    chunk_overlap: int = field(
        default_factory=lambda: int(os.getenv("CHUNK_OVERLAP", "64"))
    )
    top_k: int = field(default_factory=lambda: int(os.getenv("TOP_K", "5")))
    # Minimum cosine similarity for a retrieval to count as evidence.
    # Provisional value; calibrate on real data before evaluation.
    min_score: float = field(
        default_factory=lambda: float(os.getenv("MIN_SCORE", "0.40"))
    )

    # App --------------------------------------------------------------------
    supported_languages: tuple[str, ...] = field(
        default_factory=lambda: _split_languages(
            os.getenv("SUPPORTED_LANGUAGES", "en,hi,kn")
        )
    )
    log_level: str = field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO")
    )
    seed: int = field(default_factory=lambda: int(os.getenv("SEED", "42")))

    def masked(self) -> dict[str, object]:
        """Return a log-safe dictionary view (token redacted)."""
        return {
            "project_root": str(self.project_root),
            "embedding_model": self.embedding_model,
            "llm_model": self.llm_model,
            "llm_device": self.llm_device,
            "llm_dtype": self.llm_dtype,
            "llm_max_new_tokens": self.llm_max_new_tokens,
            "indic_translator_backend": self.indic_translator_backend,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "top_k": self.top_k,
            "min_score": self.min_score,
            "supported_languages": self.supported_languages,
            "seed": self.seed,
            "hf_token": "***set***" if self.hf_token else "***missing***",
        }


# Module-level singleton used across the application.
settings = Settings()
