"""Build the FAISS index over the curated knowledge base.

Pipeline stage 1–6 of the RAG architecture (see docs/architecture.md):
load documents → extract text → chunk → embed (multilingual-e5-small,
"passage:" prefix) → store in FAISS → persist index + manifests.

Usage (from the project root):
    python -m src.build_index

Outputs (both gitignored, see .gitignore):
    data/processed/faiss_index.bin     FAISS IndexFlatIP vectors
    data/processed/chunks.jsonl        chunk manifest (id, doc, page, text)
    data/processed/documents.jsonl     document metadata for citations
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict
from pathlib import Path

from src.config import settings
from src.document_loader import load_all_documents
from src.embeddings import Embedder
from src.retriever import FaissRetriever
from src.text_chunker import chunk_documents

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("build_index")

CHUNKS_PATH = settings.data_processed_dir / "chunks.jsonl"
DOCUMENTS_PATH = settings.data_processed_dir / "documents.jsonl"


def save_documents_manifest(documents, path: Path) -> None:
    """Persist document metadata (for citation at answer time)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for document in documents:
            record = asdict(document)
            record.pop("pages", None)      # text lives in the chunk manifest
            record.pop("warnings", None)   # build-time diagnostics only
            record["source_path"] = str(record["source_path"])
            record["topics"] = list(record["topics"])
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_documents_manifest(path: Path) -> dict:
    """Load the document metadata written by :func:`save_documents_manifest`."""
    if not path.exists():
        raise FileNotFoundError(
            f"Document manifest not found: {path}. Run `python -m src.build_index` first."
        )
    documents = {}
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            from src.document_loader import Document  # local import

            documents[record["doc_id"]] = Document(
                doc_id=record["doc_id"],
                title=record["title"],
                organization=record["organization"],
                url=record["url"],
                language=record["language"],
                topics=tuple(record["topics"]),
                source_path=Path(record["source_path"]),
                published_date=record.get("published_date"),
                retrieved_date=record.get("retrieved_date"),
                license_notes=record.get("license_notes"),
            )
    return documents


def main() -> None:
    started = time.time()

    logger.info("loading documents from %s", settings.data_raw_dir)
    documents = load_all_documents(settings.data_raw_dir)
    logger.info("loaded %d documents", len(documents))

    chunks = chunk_documents(
        documents, chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap
    )
    logger.info(
        "chunked into %d chunks (chunk_size=%d words, overlap=%d)",
        len(chunks), settings.chunk_size, settings.chunk_overlap,
    )
    if not chunks:
        raise SystemExit("no chunks produced — check data/raw/ content")

    logger.info("embedding passages with %s (CPU)", settings.embedding_model)
    embedder = Embedder(model_name=settings.embedding_model, device=settings.llm_device)
    embeddings = embedder.encode_passages([chunk.text for chunk in chunks])
    logger.info("embedded matrix shape=%s", embeddings.shape)

    retriever = FaissRetriever(dimension=embedder.dimension, min_score=settings.min_score)
    retriever.add(embeddings, chunks)
    retriever.save(settings.faiss_index_path, CHUNKS_PATH)
    save_documents_manifest(documents, DOCUMENTS_PATH)

    elapsed = time.time() - started
    logger.info(
        "index built in %.1fs -> %s (+ %s, %s)",
        elapsed, settings.faiss_index_path, CHUNKS_PATH, DOCUMENTS_PATH,
    )


if __name__ == "__main__":
    main()
