"""Tests for the English Streamlit bootstrap and result presentation."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app import bootstrap
from app.streamlit_app import render_result, submit_question
from src.rag_pipeline import AnswerResult


class FakeUI:
    def __init__(self):
        self.messages = []

    def __getattr__(self, name):
        def record(*args, **kwargs):
            self.messages.append((name, args, kwargs))

        return record


def _citation():
    return SimpleNamespace(
        title="Crop Production Guide — Agriculture 2020",
        organization="Tamil Nadu Agricultural University",
        page_number=17,
        excerpt="Wheat irrigation is required at tillering and flowering stages.",
        url="https://example.org/agriculture.pdf",
    )


def _settings(tmp_path):
    processed = tmp_path / "data" / "processed"
    processed.mkdir(parents=True)
    index_path = processed / "faiss_index.bin"
    chunks_path = processed / "chunks.jsonl"
    documents_path = processed / "documents.jsonl"
    for path in (index_path, chunks_path, documents_path):
        path.write_text("present", encoding="utf-8")
    return SimpleNamespace(
        data_processed_dir=processed,
        faiss_index_path=index_path,
        embedding_model="intfloat/multilingual-e5-small",
        min_score=0.41,
        top_k=4,
    )


def test_bootstrap_constructs_existing_rag_pipeline_with_local_model(
    tmp_path, monkeypatch
):
    settings = _settings(tmp_path)
    local_model = tmp_path / "cached-e5"
    local_model.mkdir()
    monkeypatch.setattr(bootstrap, "snapshot_download", Mock(return_value=str(local_model)))
    document = object()
    monkeypatch.setattr(
        bootstrap, "load_documents_manifest", Mock(return_value={"doc": document})
    )
    retriever = SimpleNamespace(size=1)
    load_retriever = Mock(return_value=retriever)
    monkeypatch.setattr(bootstrap.FaissRetriever, "load", load_retriever)
    embedder = object()
    embedder_factory = Mock(return_value=embedder)

    pipeline = bootstrap.build_pipeline(
        settings, embedder_factory=embedder_factory
    )

    bootstrap.snapshot_download.assert_called_once_with(
        repo_id="intfloat/multilingual-e5-small",
        cache_dir=str(bootstrap.HF_HUB_CACHE),
        local_files_only=True,
    )
    embedder_factory.assert_called_once_with(model_name=str(local_model), device="cpu")
    load_retriever.assert_called_once_with(
        index_path=settings.faiss_index_path,
        chunks_path=settings.data_processed_dir / "chunks.jsonl",
        min_score=settings.min_score,
    )
    assert pipeline.retriever is retriever
    assert pipeline.embedder is embedder
    assert pipeline.documents_by_id == {"doc": document}
    assert pipeline.top_k == settings.top_k


def test_bootstrap_reports_missing_index_assets_before_loading_model(tmp_path):
    settings = SimpleNamespace(
        data_processed_dir=tmp_path,
        faiss_index_path=tmp_path / "missing-index.bin",
        embedding_model="intfloat/multilingual-e5-small",
        min_score=0.4,
        top_k=5,
    )
    model_factory = Mock()

    with pytest.raises(bootstrap.ApplicationBootstrapError, match="missing-index.bin"):
        bootstrap.build_pipeline(settings, embedder_factory=model_factory)

    model_factory.assert_not_called()


def test_bootstrap_reports_local_model_initialization_failure(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    monkeypatch.setattr(
        bootstrap,
        "snapshot_download",
        Mock(side_effect=OSError("offline cache unavailable")),
    )

    with pytest.raises(bootstrap.ApplicationBootstrapError, match="OSError"):
        bootstrap.build_pipeline(settings, embedder_factory=Mock())


def test_successful_question_submission_calls_rag_pipeline_once():
    expected = AnswerResult(
        question="When should wheat be irrigated?",
        mode="answered",
        answer_kind="extractive_evidence",
        answer_text="Wheat irrigation is required at tillering and flowering stages.",
    )
    pipeline = Mock()
    pipeline.answer.return_value = expected

    result = submit_question(pipeline, expected.question)

    assert result is expected
    pipeline.answer.assert_called_once_with(expected.question)


def test_extractively_grounded_result_and_source_provenance_are_displayed():
    ui = FakeUI()
    result = AnswerResult(
        question="When should wheat be irrigated?",
        mode="answered",
        answer_kind="extractive_evidence",
        answer_text="Wheat irrigation is required at tillering and flowering stages.",
        sources=(_citation(),),
    )

    render_result(ui, result)

    assert ("success", ("Extracted evidence",), {}) in ui.messages
    assert any("not an LLM-generated answer" in str(message) for message in ui.messages)
    assert any("Crop Production Guide" in str(message) for message in ui.messages)
    assert any("Tamil Nadu Agricultural University" in str(message) for message in ui.messages)
    assert any("Page 17" in str(message) for message in ui.messages)
    assert any("tillering and flowering" in str(message) for message in ui.messages)
    assert any("https://example.org/agriculture.pdf" in str(message) for message in ui.messages)


def test_abstention_and_error_are_labeled_clearly():
    abstention_ui = FakeUI()
    render_result(
        abstention_ui,
        AnswerResult(
            question="Who won the World Cup?",
            mode="abstained",
            answer_kind="abstention",
            answer_text="Insufficient agricultural evidence.",
            warnings=("No retrieved passage supports the requested crop.",),
        ),
    )
    assert ("warning", ("Insufficient evidence",), {}) in abstention_ui.messages
    assert any("Reason: No retrieved passage" in str(message) for message in abstention_ui.messages)

    error_ui = FakeUI()
    result = submit_question(Mock(answer=Mock(side_effect=RuntimeError("failure"))), "test")
    render_result(error_ui, result)
    assert result.answer_kind == "error"
    assert ("error", ("Error",), {}) in error_ui.messages


def test_sources_are_also_displayed_with_an_abstention_when_available():
    ui = FakeUI()
    render_result(
        ui,
        AnswerResult(
            question="Question",
            mode="abstained",
            answer_kind="abstention",
            answer_text="Insufficient agricultural evidence.",
            sources=(_citation(),),
        ),
    )
    assert any("Crop Production Guide" in str(message) for message in ui.messages)
