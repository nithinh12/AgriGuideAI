"""Integration tests over the real knowledge base provenance registry.

These verify the spec requirement that every downloaded document has recorded
provenance (title, organization, URL, retrieval date) — and that no file sits
in data/raw/ untracked.
"""

from __future__ import annotations

import json

import pytest

from src.document_loader import ProvenanceError, load_all_documents, load_provenance
from tests.conftest import RAW_DIR, SOURCES_JSONL


pytestmark = pytest.mark.skipif(
    not SOURCES_JSONL.exists(),
    reason="data/raw/sources.jsonl not present",
)


def test_registry_has_at_least_three_credible_sources():
    registry = load_provenance(SOURCES_JSONL)
    assert len(registry) >= 3
    for doc_id, record in registry.items():
        assert record["title"].strip(), doc_id
        assert record["organization"].strip(), doc_id
        assert record["url"].startswith("http"), doc_id
        assert record["retrieved_date"], doc_id


def test_every_source_file_is_registered():
    """No document may sit in data/raw/ without provenance."""
    registered = set(load_provenance(SOURCES_JSONL))
    on_disk = {
        path.stem
        for path in RAW_DIR.iterdir()
        if path.suffix.lower() in {".pdf", ".txt"}
    }
    untracked = on_disk - registered
    assert not untracked, f"untracked source files: {sorted(untracked)}"


def test_sources_jsonl_is_committed_artifact():
    """The registry itself must be valid JSONL (git-friendly)."""
    for line_no, line in enumerate(
        SOURCES_JSONL.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        record = json.loads(line)
        assert isinstance(record["topics"], list), f"line {line_no}"


def test_full_kb_loads_end_to_end():
    documents = load_all_documents(RAW_DIR)
    assert len(documents) >= 3
    for document in documents:
        assert document.full_text.strip(), f"{document.doc_id} extracted no text"
        assert document.title and document.organization and document.url


def test_load_all_raises_on_untracked_file(tmp_path):
    (tmp_path / "sources.jsonl").write_text(
        json.dumps(
            {
                "doc_id": "known",
                "title": "T",
                "organization": "O",
                "url": "https://example.org/x.pdf",
                "language": "en",
                "retrieved_date": "2026-10-29",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "mystery_doc.txt").write_text("x", encoding="utf-8")
    with pytest.raises(ProvenanceError, match="mystery_doc"):
        load_all_documents(tmp_path)
