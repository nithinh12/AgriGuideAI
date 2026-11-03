"""Load the saved, local RAG assets for the Streamlit application."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HF_HOME = PROJECT_ROOT / ".cache" / "huggingface"
HF_HUB_CACHE = HF_HOME / "hub"

# Keep cache resolution on the project drive before Hugging Face imports.
os.environ.setdefault("HF_HOME", str(HF_HOME))
os.environ.setdefault("HF_HUB_CACHE", str(HF_HUB_CACHE))

from huggingface_hub import snapshot_download  # noqa: E402

from src.build_index import load_documents_manifest  # noqa: E402
from src.config import settings  # noqa: E402
from src.embeddings import Embedder  # noqa: E402
from src.rag_pipeline import ExtractiveEvidenceGenerator, RAGPipeline  # noqa: E402
from src.retriever import FaissRetriever  # noqa: E402


class ApplicationBootstrapError(RuntimeError):
    """The saved knowledge base or local embedding model could not be loaded."""


def build_pipeline(
    settings_obj=settings,
    *,
    embedder_factory: Callable[..., Embedder] | None = None,
) -> RAGPipeline:
    """Construct the existing RAG pipeline without rebuilding or downloading.

    The FAISS index and its manifests must already exist. The embedding model
    is resolved from the project's local Hugging Face cache in offline mode,
    then loaded by path so model initialization cannot fetch remote files.
    """
    processed_dir = Path(settings_obj.data_processed_dir)
    index_path = Path(settings_obj.faiss_index_path)
    chunks_path = processed_dir / "chunks.jsonl"
    documents_path = processed_dir / "documents.jsonl"
    required_files = (index_path, chunks_path, documents_path)
    missing = [str(path) for path in required_files if not path.is_file()]
    if missing:
        raise ApplicationBootstrapError(
            "Saved RAG data is incomplete; missing: {}. Build the index with "
            "`python -m src.build_index` before starting the application.".format(
                ", ".join(missing)
            )
        )

    model_factory = embedder_factory or Embedder
    try:
        local_model_path = Path(
            snapshot_download(
                repo_id=settings_obj.embedding_model,
                cache_dir=str(HF_HUB_CACHE),
                local_files_only=True,
            )
        )
        if not local_model_path.is_dir():
            raise FileNotFoundError(
                "The cached embedding model directory is unavailable: {}".format(
                    local_model_path
                )
            )

        documents = load_documents_manifest(documents_path)
        if not documents:
            raise ValueError("The saved document manifest contains no documents.")

        embedder = model_factory(model_name=str(local_model_path), device="cpu")
        retriever = FaissRetriever.load(
            index_path=index_path,
            chunks_path=chunks_path,
            min_score=settings_obj.min_score,
        )
        if retriever.size == 0:
            raise ValueError("The saved FAISS index contains no chunks.")

        return RAGPipeline(
            retriever=retriever,
            embedder=embedder,
            documents_by_id=documents,
            generator=ExtractiveEvidenceGenerator(),
            top_k=settings_obj.top_k,
        )
    except ApplicationBootstrapError:
        raise
    except Exception as exc:
        raise ApplicationBootstrapError(
            "Could not initialize the local RAG application ({}). Confirm the "
            "saved index/manifests and cached embedding model are intact.".format(
                type(exc).__name__
            )
        ) from exc
