"""RAG orchestration for AgriGuide AI.

Wires retrieval and answer generation together and enforces two safety
properties from the project spec:

1. **No answer without sources.** Every ``mode="answered"`` result carries at
   least one :class:`SourceCitation`.
2. **Honest abstention.** When retrieval returns nothing above the score
   gate, the result is ``mode="abstained"`` with an explicit
   insufficient-evidence message and an expert-referral — never a guess.

The generator is pluggable. The current submission uses deterministic
extractive evidence only; it does not use a generative language model.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Literal, Protocol

from src.document_loader import Document
from src.embeddings import Embedder
from src.retriever import (
    FaissRetriever,
    RetrievedPassage,
    content_terms,
    crop_anchors,
    query_specific_terms,
)

ABSTAIN_MESSAGE = (
    "The knowledge base does not contain enough evidence to answer this "
    "question reliably. No recommendation is given rather than a guessed one. "
    "Please consult a qualified agricultural expert or your local Krishi "
    "Vigyan Kendra (KVK) for guidance specific to your crop, soil, and region."
)
PROCESSING_ERROR_MESSAGE = (
    "This question could not be processed safely. Please try again. "
    "No agricultural recommendation is being made."
)

AnswerKind = Literal[
    "extractive_evidence",
    "abstention",
    "translation_fallback",
    "error",
]
AnswerMode = Literal["answered", "abstained", "error"]

logger = logging.getLogger(__name__)


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
    mode: AnswerMode
    answer_kind: AnswerKind
    answer_text: str
    sources: tuple[SourceCitation, ...] = ()
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def with_translation_fallback(self, warning: str) -> "AnswerResult":
        """Label an answered result whose response could not be translated."""
        if self.mode != "answered":
            return self
        return AnswerResult(
            question=self.question,
            mode=self.mode,
            answer_kind="translation_fallback",
            answer_text=self.answer_text,
            sources=self.sources,
            warnings=self.warnings + (warning,),
        )


class AnswerGenerator(Protocol):
    """Anything that can turn retrieved passages into answer text."""

    kind: str

    def generate(self, question: str, passages: list[RetrievedPassage]) -> str: ...


def collapse_repeated_blocks(text: str, min_tokens: int = 4) -> str:
    """Collapse consecutive exact repeats of a token block into one copy.

    PDF tables are extracted cell by cell, so a table with identical columns
    appears as the same run of tokens many times in a row. Only a block of at
    least ``min_tokens`` tokens that repeats immediately, token for token
    (ignoring letter case), is collapsed to its first occurrence as written;
    repeats separated by other text are left untouched.
    """
    tokens = text.split()
    folded = [token.casefold() for token in tokens]
    count = len(tokens)
    output: list[str] = []
    changed = False
    index = 0
    while index < count:
        for length in range(min_tokens, (count - index) // 2 + 1):
            if folded[index] != folded[index + length]:
                continue
            block = folded[index : index + length]
            if folded[index + length : index + 2 * length] != block:
                continue
            end = index + 2 * length
            while folded[end : end + length] == block:
                end += length
            output.extend(tokens[index : index + length])
            index = end
            changed = True
            break
        else:
            output.append(tokens[index])
            index += 1
    return " ".join(output) if changed else text


# PDF extraction runs a table's last row into the next table's caption, e.g.
# "... 5 100 6 Table-2: The crop wise list ...". The optional leading number is
# the page/item marker that precedes the caption.
_TABLE_CAPTION = re.compile(r"(?:\s+\d{1,2})?\s+Table[-\s]?\d+\s*:", re.IGNORECASE)


def trim_at_table_caption(sentence: str, question: str) -> str:
    """Cut a sentence at an embedded table caption the question did not ask for.

    Only cuts when the text before the caption already shares a content term
    with the question; otherwise the evidence may lie after the caption and
    the sentence is returned unchanged.
    """
    if re.search(r"\btables?\b", question, re.IGNORECASE):
        return sentence
    match = _TABLE_CAPTION.search(sentence)
    if match is None:
        return sentence
    head = sentence[: match.start()].rstrip()
    if len(head.split()) < 4 or not (
        set(content_terms(question)) & set(content_terms(head))
    ):
        return sentence
    return head


_BUFFER_ROW_LABEL = re.compile(
    r"Length of buffer zone \(m\) to avoid\s+non[\s-]?targets?\s+crops?\s+Water bodies etc\.?",
    re.IGNORECASE,
)
# One table column read top to bottom ends with its two buffer cells, the
# second of the two preceded by the "Site specific" Yes/yes cells.
_BUFFER_COLUMN_CELLS = re.compile(
    r"\byes\s+yes\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\b", re.IGNORECASE
)


def summarize_buffer_zone_table(question: str, passage_text: str) -> str | None:
    """Read the SOP buffer-zone table rows out of flattened PDF table text.

    The PDF table has the row label "Length of buffer zone (m) to avoid" with
    two sub-rows, "non targets crops" then "Water bodies etc.", and one column
    per crop. Extraction emits the labels once, then each column top to bottom,
    so a column's last two numbers are its non-target-crop and water-body
    values, in label order (checked against the rendered page). The values
    are read from ``passage_text``; nothing is assumed. Returns ``None`` unless
    the question is about a buffer zone, the label is present, and every
    column agrees, so any other text keeps its verbatim answer.
    """
    if not re.search(r"\bbuffer\b", question, re.IGNORECASE):
        return None
    label = _BUFFER_ROW_LABEL.search(passage_text)
    if label is None:
        return None
    table = passage_text[label.end() :]
    caption = _TABLE_CAPTION.search(table)
    if caption is not None:
        table = table[: caption.start()]
    columns = _BUFFER_COLUMN_CELLS.findall(table)
    if not columns or len(set(columns)) != 1:
        return None
    crops_m, water_m = columns[0]
    return (
        f"The SOP table lists a buffer zone of {crops_m} m to avoid non-target crops "
        f"and {water_m} m to avoid water bodies, with the same values in all "
        f"{len(columns)} crop columns."
    )


# PDF bullet lists and tables extract as one very long "sentence" that can hit
# a few question words by chance. Such a candidate (LONG_SENTENCE_WORDS or
# more) is only kept if it matches at least LONG_MIN_RELATIVE_OVERLAP of the
# question terms matched by the best-ranked sentence. Shorter sentences are
# never filtered this way, and the best-ranked sentence always passes.
LONG_SENTENCE_WORDS = 60
LONG_MIN_RELATIVE_OVERLAP = 0.75
# A supporting sentence must either sit in the same chunk within
# SUPPORT_MAX_SENTENCE_GAP sentences of the best-ranked one (a continuation:
# the list items, figures or explanation that follow a heading sentence), or
# match at least SUPPORT_MIN_RELATIVE_OVERLAP of the question terms the best
# sentence matched. This drops distant sentences that only share a few words.
# "Which crops are covered" questions are exempt: their evidence is a list of
# crop names, for which term-overlap strength is not meaningful.
SUPPORT_MAX_SENTENCE_GAP = 2
SUPPORT_MIN_RELATIVE_OVERLAP = 0.75
# Guide steps are often a short list ("Irrigate immediately after cutting. ...
# Irrigate on the 3rd or 4th day. ... Irrigate once in 7 - 10 days."). Only the
# first item names every question term; the rest share one or two. A sentence
# directly next to an already selected one in the same chunk, sharing at least
# one question term and not itself a long PDF run-on, is kept as a continuation
# of that list, while the answer stays within MAX_CONTINUED_SENTENCES sentences
# and MAX_CONTINUED_WORDS words (the budget also bounds translation time).
# Continuations never start an answer: with no sentence selected on its own
# merits the pipeline abstains.
MAX_CONTINUED_SENTENCES = 8
MAX_CONTINUED_WORDS = 120


class ExtractiveEvidenceGenerator:
    """Milestone-1 generator: quotes the best-matching retrieved sentences.

    This is not an LLM and makes no recommendations of its own — it only
    surfaces verbatim evidence sentences from the knowledge base.
    """

    kind = "extractive_evidence"

    def __init__(self, max_sentences: int = 3, min_words: int = 4):
        self.max_sentences = max_sentences
        self.min_words = min_words

    def generate(self, question: str, passages: list[RetrievedPassage]) -> str:
        from src.text_chunker import split_sentences  # local import (light)

        query_terms = set(content_terms(question))
        specific_terms = set(query_specific_terms(question))
        wants_crop_list = bool(
            re.search(r"\bwhich\b.{0,50}\bcrops?\b", question, re.IGNORECASE)
        )
        candidates: list[tuple[int, int, float, int, str, str, str]] = []
        # (source_order, chunk_id, sentence, matched query terms) of every
        # sentence long enough to quote, whether or not it was a candidate.
        pool: list[tuple[int, str, str, frozenset[str]]] = []
        source_order = 0
        seen_sentences: set[str] = set()
        for passage in passages:
            for sentence in split_sentences(passage.chunk.text):
                words = sentence.split()
                if len(words) < self.min_words:
                    source_order += 1
                    continue
                normalized_sentence = sentence.casefold()
                overlap = query_terms & set(content_terms(sentence))
                specific_overlap = specific_terms & set(content_terms(sentence))
                pool.append((source_order, passage.chunk.chunk_id, sentence, frozenset(overlap)))
                if (
                    overlap
                    and normalized_sentence not in seen_sentences
                    and (not specific_terms or specific_overlap)
                    and (len(specific_terms) < 2 or len(specific_overlap) >= 2)
                    and (not wants_crop_list or crop_anchors(sentence))
                ):
                    candidates.append(
                        (
                            len(specific_overlap),
                            len(overlap),
                            passage.score,
                            source_order,
                            sentence,
                            passage.chunk.doc_id,
                            passage.chunk.chunk_id,
                        )
                    )
                    seen_sentences.add(normalized_sentence)
                source_order += 1

        # Prefer sentences that share question concepts, then use retrieval
        # score; output remains verbatim and in source order.
        candidates.sort(key=lambda item: (-item[0], -item[1], -item[2], item[3]))
        if candidates:
            # A weaker match from a different document than the best sentence
            # is incidental keyword overlap (e.g. a spray table that mentions
            # a growth stage), not supporting evidence, so it is not appended.
            best = candidates[0]
            candidates = [
                item
                for item in candidates
                if item[5] == best[5] or (item[0], item[1]) == (best[0], best[1])
            ]
            candidates = [
                item
                for item in candidates
                if len(item[4].split()) < LONG_SENTENCE_WORDS
                or item[1] >= LONG_MIN_RELATIVE_OVERLAP * best[1]
            ]
            if not wants_crop_list:
                candidates = [
                    item
                    for item in candidates
                    if item is best
                    or (
                        item[6] == best[6]
                        and abs(item[3] - best[3]) <= SUPPORT_MAX_SENTENCE_GAP
                    )
                    or item[1] >= SUPPORT_MIN_RELATIVE_OVERLAP * best[1]
                ]
        selected_items = sorted(candidates[: self.max_sentences], key=lambda item: item[3])
        selected = [
            trim_at_table_caption(collapse_repeated_blocks(item[4]), question)
            for item in selected_items
        ]
        if selected_items and not wants_crop_list:
            # Grow the list that contains the best-ranked sentence: neighbours
            # of that sentence, then neighbours of those, within the budget.
            best = candidates[0]
            texts = {item[3]: selected[index] for index, item in enumerate(selected_items)}
            chain = {best[3]}
            grew = True
            while grew:
                grew = False
                for order, chunk_id, sentence, overlap in pool:
                    if order in texts or not overlap or chunk_id != best[6]:
                        continue
                    if len(sentence.split()) >= LONG_SENTENCE_WORDS:
                        continue
                    if not any(abs(order - member) <= SUPPORT_MAX_SENTENCE_GAP for member in chain):
                        continue
                    if len(texts) >= MAX_CONTINUED_SENTENCES or sum(
                        len(text.split()) for text in texts.values()
                    ) + len(sentence.split()) > MAX_CONTINUED_WORDS:
                        continue
                    if sentence.casefold() in {text.casefold() for text in texts.values()}:
                        continue
                    chain.add(order)
                    texts[order] = trim_at_table_caption(collapse_repeated_blocks(sentence), question)
                    grew = True
            selected = [texts[order] for order in sorted(texts)]
        if not selected:
            # Empty text signals that the pipeline must abstain. Explanatory
            # prose here would be incorrectly presented as an answer.
            return ""
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
        cited_excerpts: set[tuple[str, str]] = set()
        for passage in passages:
            # The source PDF can repeat a page's text on the next page; citing
            # the same excerpt twice adds no provenance.
            excerpt_key = (passage.chunk.doc_id, passage.chunk.text)
            if excerpt_key in cited_excerpts:
                continue
            cited_excerpts.add(excerpt_key)
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
                answer_kind="abstention",
                answer_text="Please enter a question.",
                warnings=("empty question",),
            )

        try:
            query_embedding = self.embedder.encode_query(question)
            passages = self.retriever.search(
                # Retrieve a wider read-only candidate set so lexical/topic
                # filtering can reject generic dense hits without hiding a
                # specific evidence passage just below the top-five ranking.
                query_embedding, top_k=self.top_k * 20, query_text=question
            )
        except Exception as exc:
            logger.exception("RAG retrieval failed (%s)", type(exc).__name__)
            return AnswerResult(
                question=question,
                mode="error",
                answer_kind="error",
                answer_text=PROCESSING_ERROR_MESSAGE,
                warnings=("retrieval failed ({})".format(type(exc).__name__),),
            )

        if not passages:
            return AnswerResult(
                question=question,
                mode="abstained",
                answer_kind="abstention",
                answer_text=ABSTAIN_MESSAGE,
                warnings=(
                    "no evidence above min_score gate "
                    f"({self.retriever.min_score:.2f})",
                ),
            )

        passages, relevance_reason = self.retriever.relevant_evidence(question, passages)
        if not passages:
            return AnswerResult(
                question=question,
                mode="abstained",
                answer_kind="abstention",
                answer_text=ABSTAIN_MESSAGE,
                warnings=(relevance_reason or "retrieved evidence did not support the question",),
            )
        passages = passages[: self.top_k]

        citations = self._cite(passages)
        try:
            answer_text = self.generator.generate(question, passages)
        except Exception as exc:
            logger.exception("Answer generation failed (%s)", type(exc).__name__)
            return AnswerResult(
                question=question,
                mode="error",
                answer_kind="error",
                answer_text=PROCESSING_ERROR_MESSAGE,
                sources=citations,
                warnings=("answer generation failed ({})".format(type(exc).__name__),),
            )

        if not isinstance(answer_text, str):
            logger.error(
                "Answer generator returned %s instead of str", type(answer_text).__name__
            )
            return AnswerResult(
                question=question,
                mode="error",
                answer_kind="error",
                answer_text=PROCESSING_ERROR_MESSAGE,
                sources=citations,
                warnings=("answer generator returned an invalid result",),
            )

        if not answer_text.strip():
            return AnswerResult(
                question=question,
                mode="abstained",
                answer_kind="abstention",
                answer_text=ABSTAIN_MESSAGE,
                warnings=("retrieved passages contained no usable evidence sentences",),
            )
        if re.search(r"\b(measures?|precautions?)\b", question, re.IGNORECASE) and not re.search(
            r"\b(do not|must|should|need to|maintain|check|avoid|stop|operate)\b",
            answer_text,
            re.IGNORECASE,
        ):
            return AnswerResult(
                question=question,
                mode="abstained",
                answer_kind="abstention",
                answer_text=ABSTAIN_MESSAGE,
                warnings=("retrieved text names requirements but gives no specific measure",),
            )
        if re.search(r"\bwhich\b.{0,50}\bcrops?\b", question, re.IGNORECASE) and len(
            crop_anchors(answer_text)
        ) < 2:
            return AnswerResult(
                question=question,
                mode="abstained",
                answer_kind="abstention",
                answer_text=ABSTAIN_MESSAGE,
                warnings=("retrieved text did not identify the crops requested",),
            )
        from src.text_chunker import split_sentences

        answer_sentences = split_sentences(answer_text)
        answer_passages = [
            passage
            for passage in passages
            if any(
                sentence in passage.chunk.text
                or sentence in collapse_repeated_blocks(passage.chunk.text)
                for sentence in answer_sentences
            )
        ]
        citations = self._cite(answer_passages)
        if not citations:
            return AnswerResult(
                question=question,
                mode="abstained",
                answer_kind="abstention",
                answer_text=ABSTAIN_MESSAGE,
                warnings=("selected evidence could not be matched to a source excerpt",),
            )
        # Invariant from the spec: an answered result always has sources.
        assert citations, "answered result must carry at least one source"
        # Restate a verbatim table answer in words; the cited excerpts above
        # remain the unmodified evidence.
        for passage in answer_passages:
            summary = summarize_buffer_zone_table(question, passage.chunk.text)
            if summary is not None:
                answer_text = summary
                break
        inherited_pages = sorted(
            {p.chunk.page_number for p in answer_passages if p.crop_context_inherited}
        )
        warnings = ()
        if inherited_pages:
            warnings = (
                "The crop named in the question is not repeated in the cited excerpt "
                "on page {}; it was taken from the directly preceding passage of the "
                "same document.".format(", ".join(str(page) for page in inherited_pages)),
            )
        return AnswerResult(
            question=question,
            mode="answered",
            answer_kind="extractive_evidence",
            answer_text=answer_text,
            sources=citations,
            warnings=warnings,
        )
