"""RAG orchestration for AgriGuide AI.

Wires retrieval and answer generation together and enforces two safety
properties from the project spec:

1. **No answer without sources.** Every ``mode="answered"`` result carries at
   least one :class:`SourceCitation`.
2. **Honest abstention.** When retrieval returns nothing above the score
   gate, the result is ``mode="abstained"`` with an explicit
   insufficient-evidence message and an expert-referral — never a guess.

The generator is pluggable: Phase 1 uses an extractive evidence summarizer
clearly labeled as such; Phase 6 swaps in BharatGen AgriParam via
``src.llm_service`` without changing this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from src.document_loader import Document
from src.embeddings import Embedder
from src.retriever import FaissRetriever, RetrievedPassage

ABSTAIN_MESSAGE = (
    "The knowledge base does not contain enough evidence to answer this "
    "question reliably. No recommendation is given rather than a guessed one. "
    "Please consult a qualified agricultural expert or your local Krishi "
    "Vigyan Kendra (KVK) for guidance specific to your crop, soil, and region."
)


@dataclass(frozen=True)
class SourceCitation:
    """A source shown alongside an answer (spec: source transparency)."""

    doc_id: str
    title: str
    organization: str
    url: str
    page_number: int
    excerpt: str
    score: float


@dataclass(frozen=True)
class AnswerResult:
    """Structured pipeline output for one question."""

    question: str
    mode: str                    # "answered" | "abstained"
    answer_kind: str             # e.g. "extractive_evidence", later "agriparam"
    answer_text: str
    sources: tuple[SourceCitation, ...] = ()
    warnings: tuple[str, ...] = field(default_factory=tuple)


class AnswerGenerator(Protocol):
    """Anything that can turn retrieved passages into answer text."""

    kind: str

    def generate(self, question: str, passages: list[RetrievedPassage]) -> str: ...


class ExtractiveEvidenceGenerator:
    """Milestone-1 generator: quotes the best-matching retrieved sentences.

    This is NOT an LLM and makes no recommendations of its own — it only
    surfaces evidence sentences from the knowledge base, so the pipeline can
    be demonstrated end-to-end before AgriParam is integrated (Phase 6).
    """

    kind = "extractive_evidence"

    def __init__(self, max_sentences: int = 3, min_words: int = 4):
        self.max_sentences = max_sentences
        self.min_words = min_words

    def generate(self, question: str, passages: list[RetrievedPassage]) -> str:
        from src.text_chunker import split_sentences  # local import (light)

        candidates: list[tuple[float, str]] = []
        for passage in passages:
            for sentence in split_sentences(passage.chunk.text):
                words = sentence.split()
                if len(words) < self.min_words:
                    continue
                candidates.append((passage.score, sentence))

        # Keep the sentences from the highest-scoring passages, in source order.
        candidates.sort(key=lambda item: -item[0])
        selected = [sentence for _, sentence in candidates[: self.max_sentences]]
        if not selected:
            return "No usable evidence sentences were found in the retrieved passages."
        return " ".join(selected)


class RAGPipeline:
    """Retrieve → gate → generate → cite."""

    def __init__(
        self,
        retriever: FaissRetriever,
        embedder: Embedder,
        documents_by_id: dict[str, Document],
        generator: AnswerGenerator,
        top_k: int = 5,
    ):
        self.retriever = retriever
        self.embedder = embedder
        self.documents_by_id = documents_by_id
        self.generator = generator
        self.top_k = top_k

    def _cite(self, passages: list[RetrievedPassage]) -> tuple[SourceCitation, ...]:
        citations: list[SourceCitation] = []
        for passage in passages:
            document = self.documents_by_id.get(passage.chunk.doc_id)
            if document is None:
                # Should not happen if the index was built from known docs;
                # surface it loudly rather than citing a phantom source.
                raise KeyError(
                    f"retrieved chunk '{passage.chunk.chunk_id}' references "
                    f"unknown document '{passage.chunk.doc_id}'"
                )
            citations.append(
                SourceCitation(
                    doc_id=document.doc_id,
                    title=document.title,
                    organization=document.organization,
                    url=document.url,
                    page_number=passage.chunk.page_number,
                    excerpt=passage.chunk.text,
                    score=passage.score,
                )
            )
        return tuple(citations)

    def answer(self, question: str) -> AnswerResult:
        """Answer one question, grounded in retrieved evidence or abstaining."""
        question = question.strip()
        if not question:
            return AnswerResult(
                question=question,
                mode="abstained",
                answer_kind=self.generator.kind,
                answer_text="Please enter a question.",
                warnings=("empty question",),
            )

        query_embedding = self.embedder.encode_query(question)
        passages = self.retriever.search(query_embedding, top_k=self.top_k)

        if not passages:
            return AnswerResult(
                question=question,
                mode="abstained",
                answer_kind=self.generator.kind,
                answer_text=ABSTAIN_MESSAGE,
                warnings=(
                    "no evidence above min_score gate "
                    f"({self.retriever.min_score:.2f})",
                ),
            )

        answer_text = self.generator.generate(question, passages)
        citations = self._cite(passages)
        # Invariant from the spec: an answered result always has sources.
        assert citations, "answered result must carry at least one source"
        return AnswerResult(
            question=question,
            mode="answered",
            answer_kind=self.generator.kind,
            answer_text=answer_text,
            sources=citations,
        )
