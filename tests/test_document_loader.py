"""Tests for src.document_loader (provenance + extraction)."""

from __future__ import annotations

import json

import pytest

from src.document_loader import (
    ProvenanceError,
    load_all_documents,
    load_document,
    load_provenance,
)
from tests.conftest import RAW_DIR, SOURCES_JSONL, requires_real_pdf


def _write_sources(tmp_path, records):
    path = tmp_path / "sources.jsonl"
    path.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8"
    )
    return path


def _base_record(doc_id="sample_doc"):
    return {
        "doc_id": doc_id,
        "title": "Sample Title",
        "organization": "Sample Org",
        "url": "https://example.org/sample.pdf",
        "language": "en",
        "topics": ["irrigation"],
        "retrieved_date": "2026-10-29",
    }


class TestProvenance:
    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(ProvenanceError, match="not found"):
            load_provenance(tmp_path / "sources.jsonl")

    def test_missing_required_fields_raises(self, tmp_path):
        record = _base_record()
        del record["url"]
        path = _write_sources(tmp_path, [record])
        with pytest.raises(ProvenanceError, match="missing required fields"):
            load_provenance(path)

    def test_duplicate_doc_id_raises(self, tmp_path):
        path = _write_sources(tmp_path, [_base_record(), _base_record()])
        with pytest.raises(ProvenanceError, match="duplicate doc_id"):
            load_provenance(path)

    def test_invalid_json_raises(self, tmp_path):
        path = tmp_path / "sources.jsonl"
        path.write_text("{not json\n", encoding="utf-8")
        with pytest.raises(ProvenanceError, match="invalid JSON"):
            load_provenance(path)


class TestTextLoading:
    def test_txt_document_loads_with_provenance(self, tmp_path):
        (tmp_path / "sample_doc.txt").write_text(
            "Irrigation intervals depend on soil type.\n", encoding="utf-8"
        )
        registry = load_provenance(_write_sources(tmp_path, [_base_record()]))
        document = load_document(tmp_path / "sample_doc.txt", registry)
        assert document.doc_id == "sample_doc"
        assert document.title == "Sample Title"
        assert document.organization == "Sample Org"
        assert document.url == "https://example.org/sample.pdf"
        assert "Irrigation intervals" in document.full_text

    def test_file_without_provenance_raises(self, tmp_path):
        (tmp_path / "untracked.txt").write_text("text", encoding="utf-8")
        registry = load_provenance(_write_sources(tmp_path, [_base_record()]))
        with pytest.raises(ProvenanceError, match="No provenance record for 'untracked'"):
            load_document(tmp_path / "untracked.txt", registry)

    def test_unsupported_suffix_raises(self, tmp_path):
        path = tmp_path / "sample_doc.csv"
        path.write_text("a,b\n", encoding="utf-8")
        registry = load_provenance(_write_sources(tmp_path, [_base_record()]))
        with pytest.raises(ValueError, match="Unsupported file type"):
            load_document(path, registry)


@requires_real_pdf
class TestRealPdfExtraction:
    def test_extracted_text_is_substantial(self):
        registry = load_provenance(SOURCES_JSONL)
        document = load_document(RAW_DIR / "tnau_agriculture.pdf", registry)
        assert len(document.pages) > 100, "expected a long extension guide"
        assert len(document.full_text) > 50_000, "pypdf should extract real text"
        assert document.title == "Crop Production Guide — Agriculture 2020"
        assert "Directorate of Agriculture" in document.organization

    def test_irrigation_content_actually_present(self):
        registry = load_provenance(SOURCES_JSONL)
        document = load_document(RAW_DIR / "tnau_agriculture.pdf", registry)
        assert "irrigation" in document.full_text.lower(), (
            "the crop production guide should mention irrigation"
        )


class TestLoadAll:
    def test_unregistered_file_fails_the_batch(self, tmp_path):
        (tmp_path / "stray_file.txt").write_text("x", encoding="utf-8")
        _write_sources(tmp_path, [_base_record()])  # registers a different doc
        with pytest.raises(ProvenanceError, match="stray_file"):
            load_all_documents(tmp_path)
