"""Tests for src.rag_pipeline (grounding, abstention, citation invariants)."""

from __future__ import annotations

import numpy as np
import pytest

from src.rag_pipeline import (
    ABSTAIN_MESSAGE,
    ExtractiveEvidenceGenerator,
    RAGPipeline,
    LONG_SENTENCE_WORDS,
    collapse_repeated_blocks,
    summarize_buffer_zone_table,
    trim_at_table_caption,
)
from src.retriever import FaissRetriever
from src.text_chunker import Chunk
from tests.conftest import FakeEmbedder, make_document


def _pipeline(min_score: float = 0.4, top_k: int = 2, query_vector=None):
    """Build a pipeline over two synthetic chunks with a fixed query vector."""
    relevant_doc = make_document(
        "wheat_guide",
        "Wheat irrigation is required at tillering and flowering stages.",
        title="Wheat Production Guide",
        organization="Test Agricultural University",
        url="https://example.org/wheat.pdf",
    )
    other_doc = make_document(
        "bank_info",
        "Banks provide crop loans to farmers at subsidised interest.",
        title="Banking Circular",
        organization="Test Bank",
        url="https://example.org/bank.pdf",
    )
    retriever = FaissRetriever(dimension=3, min_score=min_score)
    embeddings = np.array(
        [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float32
    )
    retriever.add(
        embeddings,
        [
            Chunk("wheat_guide::p1::c0", "wheat_guide", 1, "Wheat irrigation is required at tillering and flowering stages.", 0),
            Chunk("bank_info::p1::c0", "bank_info", 1, "Banks provide crop loans to farmers at subsidised interest.", 0),
        ],
    )
    embedder = FakeEmbedder(
        np.array([1.0, 0.0, 0.0], dtype=np.float32)
        if query_vector is None
        else np.asarray(query_vector, dtype=np.float32)
    )
    pipeline = RAGPipeline(
        retriever=retriever,
        embedder=embedder,
        documents_by_id={"wheat_guide": relevant_doc, "bank_info": other_doc},
        generator=ExtractiveEvidenceGenerator(),
        top_k=top_k,
    )
    return pipeline


def _custom_pipeline(chunks, embeddings, documents, query_vector=None, top_k=5):
    retriever = FaissRetriever(dimension=3, min_score=0.4)
    retriever.add(np.asarray(embeddings, dtype=np.float32), chunks)
    return RAGPipeline(
        retriever=retriever,
        embedder=FakeEmbedder(
            np.asarray([1.0, 0.0, 0.0] if query_vector is None else query_vector, dtype=np.float32)
        ),
        documents_by_id={doc.doc_id: doc for doc in documents},
        generator=ExtractiveEvidenceGenerator(),
        top_k=top_k,
    )


class TestAnsweredPath:
    def test_answer_carries_sources_and_metadata(self):
        result = _pipeline().answer("When should wheat be irrigated?")
        assert result.mode == "answered"
        assert result.answer_kind == "extractive_evidence"
        assert len(result.sources) >= 1

        top = result.sources[0]
        assert top.doc_id == "wheat_guide"
        assert top.title == "Wheat Production Guide"
        assert top.organization == "Test Agricultural University"
        assert top.url == "https://example.org/wheat.pdf"
        assert top.page_number == 1
        assert "irrigation" in top.excerpt.lower()
        assert top.score >= 0.4

    def test_extractive_answer_quotes_evidence_only(self):
        result = _pipeline().answer("When should wheat be irrigated?")
        assert "tillering" in result.answer_text, (
            "extractive answer must contain the retrieved evidence sentence"
        )
        assert result.answer_kind == "extractive_evidence"
        assert any(result.answer_text in source.excerpt for source in result.sources)

    def test_answered_result_never_has_empty_sources(self):
        result = _pipeline().answer("irrigation of wheat")
        if result.mode == "answered":
            assert result.sources


class TestAbstention:
    def test_gate_triggers_abstention(self):
        # A query orthogonal to every stored chunk scores 0.0 against all of
        # them; with min_score=0.99 nothing passes the gate.
        result = _pipeline(min_score=0.99, query_vector=[0.0, 0.0, 1.0]).answer(
            "Quantum physics of black holes?"
        )
        assert result.mode == "abstained"
        assert result.answer_kind == "abstention"
        assert result.sources == ()
        assert result.answer_text == ABSTAIN_MESSAGE
        assert "consult" in result.answer_text.lower()

    def test_empty_question_abstains(self):
        result = _pipeline().answer("   ")
        assert result.mode == "abstained"
        assert result.answer_kind == "abstention"
        assert "empty question" in result.warnings

    def test_no_usable_evidence_abstains_instead_of_answering_with_placeholder(self):
        pipeline = _pipeline()
        pipeline.generator = ExtractiveEvidenceGenerator(min_words=100)

        result = pipeline.answer("When should wheat be irrigated?")

        assert result.mode == "abstained"
        assert result.answer_kind == "abstention"
        assert result.answer_text == ABSTAIN_MESSAGE
        assert result.sources == ()
        assert "no usable evidence sentences" in result.warnings[0]

    def test_high_cosine_irrelevant_passage_is_rejected(self):
        document = make_document("maize_guide", "Maize irrigation is described in this source.")
        pipeline = _custom_pipeline(
            [Chunk("maize_guide::p1::c0", "maize_guide", 1, "Maize irrigation is described in this source.", 0)],
            [[1.0, 0.0, 0.0]],
            [document],
        )

        result = pipeline.answer("How do black holes evaporate through Hawking radiation?")

        assert result.mode == "abstained"
        assert result.answer_kind == "abstention"
        assert result.sources == ()
        assert "outside the agricultural topics" in result.warnings[0]

    def test_crop_anchor_prevents_wheat_question_from_using_maize_passage(self):
        document = make_document("maize_guide", "Maize irrigation is required during flowering.")
        pipeline = _custom_pipeline(
            [Chunk("maize_guide::p1::c0", "maize_guide", 1, "Maize irrigation is required during flowering.", 0)],
            [[1.0, 0.0, 0.0]],
            [document],
        )

        result = pipeline.answer("When should wheat be irrigated?")

        assert result.mode == "abstained"
        assert result.sources == ()
        assert "requested crop" in result.warnings[0]

    def test_specific_drone_safety_query_selects_specific_passage_over_generic_intro(self):
        generic = make_document("drone_intro", "Modern crop production uses drones and pesticide inputs.")
        safety = make_document(
            "drone_safety",
            "Do not spray a drone near ponds, rivers, or canals; maintain a minimum distance of 100m from these bodies.",
            title="Drone Pesticide SOP",
            organization="Government of India",
            url="https://example.org/sop.pdf",
        )
        pipeline = _custom_pipeline(
            [
                Chunk("drone_intro::p13::c0", "drone_intro", 13, generic.full_text, 0),
                Chunk("drone_safety::p22::c0", "drone_safety", 22, safety.full_text, 0),
            ],
            [[1.0, 0.0, 0.0], [0.9, 0.43589, 0.0]],
            [generic, safety],
            top_k=2,
        )

        result = pipeline.answer(
            "What minimum distance should be maintained from ponds, rivers, and canals during drone pesticide spraying?"
        )

        assert result.mode == "answered"
        assert "100m" in result.answer_text
        assert result.sources
        assert all(source.doc_id == "drone_safety" for source in result.sources)

    def test_weaker_cross_document_keyword_match_is_not_appended_or_cited(self):
        wheat = make_document(
            "tnau_guide",
            "Wheat crop requires minimum of 5 irrigations at critical stages such as tillering and flowering.",
        )
        sop = make_document(
            "drone_sop",
            "Avoid spraying during flowering stage 1 Rice 4.5-5.0 Flat fan 250-350 2 Wheat 4.5-5.0 Flat fan 250-350 6 am 10am",
        )
        pipeline = _custom_pipeline(
            [
                Chunk("tnau_guide::p136::c0", "tnau_guide", 136, wheat.full_text, 0),
                Chunk("drone_sop::p14::c0", "drone_sop", 14, sop.full_text, 0),
            ],
            [[1.0, 0.0, 0.0], [0.9, 0.1, 0.0]],
            [wheat, sop],
        )

        result = pipeline.answer("At which stages does the guide recommend irrigating wheat?")

        assert result.mode == "answered"
        assert "5 irrigations" in result.answer_text
        assert "Flat fan" not in result.answer_text
        assert [source.doc_id for source in result.sources] == ["tnau_guide"]

    def test_equally_strong_matches_from_two_documents_are_both_kept(self):
        first = make_document("guide_a", "Wheat irrigation is required at tillering and flowering stages.")
        second = make_document("guide_b", "Wheat irrigation is also needed at crown root initiation stage.")
        pipeline = _custom_pipeline(
            [
                Chunk("guide_a::p1::c0", "guide_a", 1, first.full_text, 0),
                Chunk("guide_b::p1::c0", "guide_b", 1, second.full_text, 0),
            ],
            [[1.0, 0.0, 0.0], [0.95, 0.05, 0.0]],
            [first, second],
        )

        result = pipeline.answer("At which stages does the guide recommend irrigating wheat?")

        assert result.mode == "answered"
        assert {source.doc_id for source in result.sources} == {"guide_a", "guide_b"}

    def test_which_crops_question_abstains_when_text_names_only_one_crop(self):
        document = make_document("drone_sop", "The crop-specific SOP covers maize.")
        pipeline = _custom_pipeline(
            [Chunk("drone_sop::p1::c0", "drone_sop", 1, document.full_text, 0)],
            [[1.0, 0.0, 0.0]],
            [document],
        )

        result = pipeline.answer(
            "Which crops are covered by the crop-specific Kisan Drone pesticide SOP?"
        )

        assert result.mode == "abstained"
        assert result.answer_kind == "abstention"
        assert result.answer_text == ABSTAIN_MESSAGE

    def test_generic_safety_requirements_without_a_specific_measure_abstain(self):
        # "require" appears in the passage so the question has no term unknown to this
        # one-chunk index; the guard under test is the missing-specific-measure one.
        text = (
            "The crop-specific drone SOP lists safety measures and operational "
            "requirements that operators require."
        )
        document = make_document("drone_sop", text)
        pipeline = _custom_pipeline(
            [Chunk("drone_sop::p1::c0", "drone_sop", 1, text, 0)],
            [[1.0, 0.0, 0.0]],
            [document],
        )

        result = pipeline.answer(
            "What operational and safety measures does the drone pesticide SOP require?"
        )

        assert result.mode == "abstained"
        assert "gives no specific measure" in result.warnings[0]

    def test_abstention_never_exposes_citations_even_when_passages_were_retrieved(self):
        pipeline = _pipeline()

        class EmptyGenerator:
            kind = "extractive_evidence"

            def generate(self, _question, _passages):
                return ""

        pipeline.generator = EmptyGenerator()
        result = pipeline.answer("When should wheat be irrigated?")

        assert result.mode == "abstained"
        assert result.answer_kind == "abstention"
        assert result.answer_text == ABSTAIN_MESSAGE
        assert result.warnings == ("retrieved passages contained no usable evidence sentences",)
        assert result.sources == ()

    def test_current_and_local_request_abstains_with_specific_reason(self):
        result = _pipeline().answer("What is tomorrow's rainfall forecast for paddy in Coimbatore?")

        assert result.mode == "abstained"
        assert result.answer_kind == "abstention"
        assert "current or local information" in result.warnings[0]


class TestFailureHandling:
    def test_embedding_failure_returns_error_without_recommendation(self, monkeypatch):
        pipeline = _pipeline()

        def fail_encode(_question):
            raise RuntimeError("embedding unavailable")

        monkeypatch.setattr(pipeline.embedder, "encode_query", fail_encode)
        result = pipeline.answer("When should wheat be irrigated?")

        assert result.mode == "error"
        assert result.answer_kind == "error"
        assert "No agricultural recommendation" in result.answer_text
        assert result.sources == ()
        assert result.warnings == ("retrieval failed (RuntimeError)",)

    def test_generator_failure_returns_error_and_keeps_retrieved_citations(self):
        pipeline = _pipeline()

        class FailingGenerator:
            kind = "extractive_evidence"

            def generate(self, _question, _passages):
                raise RuntimeError("generator unavailable")

        pipeline.generator = FailingGenerator()
        result = pipeline.answer("When should wheat be irrigated?")

        assert result.mode == "error"
        assert result.answer_kind == "error"
        assert result.answer_text.startswith("This question could not be processed")
        assert result.sources
        assert result.warnings == ("answer generation failed (RuntimeError)",)

    def test_translation_fallback_is_explicit_and_preserves_sources(self):
        result = _pipeline().answer("When should wheat be irrigated?")

        fallback = result.with_translation_fallback(
            "Translation unavailable; showing the English evidence."
        )

        assert fallback.answer_kind == "translation_fallback"
        assert fallback.answer_text == result.answer_text
        assert fallback.sources == result.sources
        assert fallback.warnings[-1].startswith("Translation unavailable")


class TestInvariants:
    def test_unknown_document_reference_raises(self):
        pipeline = _pipeline()
        # Remove the cited document to force the phantom-source path.
        pipeline.documents_by_id.pop("wheat_guide")
        with pytest.raises(KeyError, match="unknown document 'wheat_guide'"):
            pipeline.answer("When should wheat be irrigated?")


class TestRepeatedTableTextAndDuplicateCitations:
    ROW = "< 35 (preferabl y) > 50 (preferabl y) < 3 Don not spray Do not operate Yes Yes 5 100"

    def test_block_repeated_ten_times_becomes_one_copy(self):
        text = "Length of buffer zone " + " ".join([self.ROW] * 10) + " end of table"

        assert collapse_repeated_blocks(text) == "Length of buffer zone " + self.ROW + " end of table"

    def test_non_adjacent_repetition_is_left_intact(self):
        text = f"{self.ROW} then a different sentence about spraying height {self.ROW}"

        assert collapse_repeated_blocks(text) == text

    def test_short_adjacent_repeat_below_four_tokens_is_left_intact(self):
        text = "Yes Yes 5 100 Yes Yes 5 100 done"

        assert collapse_repeated_blocks(text) == "Yes Yes 5 100 done"
        short = "go go go now"
        assert collapse_repeated_blocks(short) == short

    def test_identical_excerpts_from_different_pages_produce_one_citation(self):
        text = "Maintain a buffer of 100 m from water bodies during drone spraying."
        document = make_document("drone_sop", text)
        pipeline = _custom_pipeline(
            [
                Chunk("drone_sop::p16::c0", "drone_sop", 16, text, 0),
                Chunk("drone_sop::p17::c1", "drone_sop", 17, text, 0),
            ],
            [[1.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
            [document],
        )

        citations = pipeline._cite(
            pipeline.retriever.search(np.array([1.0, 0.0, 0.0], dtype=np.float32), top_k=2)
        )

        assert len(citations) == 1
        assert citations[0].page_number in {16, 17}

    def test_different_excerpts_from_same_document_stay_separately_citable(self):
        document = make_document("drone_sop", "unused")
        pipeline = _custom_pipeline(
            [
                Chunk("drone_sop::p1::c0", "drone_sop", 1, "Maintain a buffer of 100 m from water bodies.", 0),
                Chunk("drone_sop::p2::c1", "drone_sop", 2, "Do not spray when wind speed exceeds 3 m/s.", 0),
            ],
            [[1.0, 0.0, 0.0], [0.9, 0.1, 0.0]],
            [document],
        )

        citations = pipeline._cite(
            pipeline.retriever.search(np.array([1.0, 0.0, 0.0], dtype=np.float32), top_k=2)
        )

        assert [c.page_number for c in citations] == [1, 2]

    def test_repeated_table_answer_is_collapsed_and_still_cited_once(self):
        table = "Length of buffer zone (m) to avoid non targets crops Water bodies " + " ".join(
            [self.ROW] * 10
        )
        document = make_document("drone_sop", table)
        pipeline = _custom_pipeline(
            [
                Chunk("drone_sop::p16::c0", "drone_sop", 16, table, 0),
                Chunk("drone_sop::p17::c1", "drone_sop", 17, table, 0),
            ],
            [[1.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
            [document],
        )

        result = pipeline.answer(
            "What buffer zone lengths does the drone SOP list for water bodies?"
        )

        assert result.mode == "answered"
        assert result.answer_text.count(self.ROW) == 1
        assert len(result.sources) == 1

    def test_case_only_variation_in_repeated_block_collapses_keeping_first_spelling(self):
        lower = self.ROW.replace("Yes Yes", "yes yes")
        text = f"Buffer {self.ROW} {self.ROW} {lower} end"

        assert collapse_repeated_blocks(text) == f"Buffer {self.ROW} end"

    def test_non_adjacent_repeat_differing_only_in_case_is_left_intact(self):
        lower = self.ROW.replace("Yes Yes", "yes yes")
        text = f"{self.ROW} then a different sentence about height {lower}"

        assert collapse_repeated_blocks(text) == text

    def test_table_caption_after_matching_evidence_is_excluded_but_answer_stays_citable(self):
        table = (
            "Length of buffer zone (m) to avoid non targets crops Water bodies etc. "
            + " ".join([self.ROW] * 3)
            + " 6 Table-2: The crop wise list of pesticide molecules tested for phytotoxicity; "
            "Crop Insecticides Rice Chlorantraniliprole 18.5SC Wheat Pyraclostrobin 133 g/l"
        )
        document = make_document("drone_sop", table)
        pipeline = _custom_pipeline(
            [Chunk("drone_sop::p16::c0", "drone_sop", 16, table, 0)],
            [[1.0, 0.0, 0.0]],
            [document],
        )

        result = pipeline.answer(
            "What zone lengths to avoid non targets crops and water bodies does the drone SOP list?"
        )

        assert result.mode == "answered"
        assert "Table-2" not in result.answer_text
        assert "Chlorantraniliprole" not in result.answer_text
        assert not result.answer_text.rstrip().endswith(" 6")
        assert result.answer_text.count(self.ROW) == 1
        assert len(result.sources) == 1
        assert "Table-2" in result.sources[0].excerpt

    def test_table_caption_is_kept_when_the_question_asks_about_the_table(self):
        text = "Pesticide molecules are tested here today. 6 Table-2: crop wise list of pesticide molecules"

        assert trim_at_table_caption(text, "What does Table-2 list for pesticide molecules?") == text
        assert trim_at_table_caption(text, "Which pesticide molecules are tested?") == "Pesticide molecules are tested here today."

    def test_table_caption_is_kept_when_evidence_precedes_no_question_term(self):
        text = "Unrelated heading words only here. 6 Table-2: buffer zone lengths for water bodies"

        assert trim_at_table_caption(text, "What buffer zone lengths apply to water bodies?") == text


class TestBufferZoneTableAnswer:
    LABEL = "8. Length of buffer zone (m) to avoid non targets crops Water bodies etc. "
    COLUMN = "< 35 (preferabl y) > 50 (preferabl y) < 3 Don not spray Do not operate Yes Yes {a} {b}"
    QUESTION = "What buffer-zone lengths does the drone SOP list for non-target crops and water bodies?"

    def _table(self, columns=10, a="5", b="100"):
        return self.LABEL + " ".join([self.COLUMN.format(a=a, b=b)] * columns)

    def test_maps_five_to_non_target_crops_and_hundred_to_water_bodies(self):
        summary = summarize_buffer_zone_table(self.QUESTION, self._table())

        assert summary == (
            "The SOP table lists a buffer zone of 5 m to avoid non-target crops "
            "and 100 m to avoid water bodies, with the same values in all 10 crop columns."
        )

    def test_values_are_read_from_the_text_not_assumed(self):
        summary = summarize_buffer_zone_table(self.QUESTION, self._table(columns=3, a="7", b="250"))

        assert "7 m to avoid non-target crops" in summary
        assert "250 m to avoid water bodies" in summary
        assert "all 3 crop columns" in summary

    def test_columns_that_disagree_keep_the_verbatim_answer(self):
        text = self.LABEL + self.COLUMN.format(a="5", b="100") + " " + self.COLUMN.format(a="5", b="50")

        assert summarize_buffer_zone_table(self.QUESTION, text) is None

    def test_other_questions_and_other_text_are_not_rewritten(self):
        assert summarize_buffer_zone_table("What nozzle type is used?", self._table()) is None
        assert summarize_buffer_zone_table(self.QUESTION, "Maintain a buffer of 100 m from ponds.") is None

    def test_pipeline_answer_is_natural_language_cited_and_excludes_table_2(self):
        chunk_text = (
            self._table()
            + " 6 Table-2: The crop wise list of pesticide molecules tested for phytotoxicity; "
            "Crop Insecticides Rice Chlorantraniliprole 18.5SC Wheat Pyraclostrobin 133 g/l"
        )
        document = make_document("tn_crop_sop_2023", chunk_text)
        pipeline = _custom_pipeline(
            [Chunk("tn_crop_sop_2023::p16::c0", "tn_crop_sop_2023", 16, chunk_text, 0)],
            [[1.0, 0.0, 0.0]],
            [document],
        )

        result = pipeline.answer(self.QUESTION)

        assert result.mode == "answered"
        assert result.answer_text.startswith("The SOP table lists a buffer zone of 5 m")
        assert "100 m to avoid water bodies" in result.answer_text
        assert "Table-2" not in result.answer_text
        assert "Chlorantraniliprole" not in result.answer_text
        assert "preferabl" not in result.answer_text
        assert [(c.doc_id, c.page_number) for c in result.sources] == [("tn_crop_sop_2023", 16)]
        assert self.LABEL.strip() in result.sources[0].excerpt


class TestLongSentenceSafeguard:
    QUESTION = "How much nursery area is selected for raising rice seedlings for one hectare?"
    BEST = "Rice wet nursery Nursery area Select 20 cents (800 m2) of land area near to water source for raising seedlings for one hectare."
    BLOB = (
        "Pests Management strategies Thrips Sampling: Wet your palm with water and pass over the "
        "foliage in 12 places at random in the nursery and count the number of thrips • ETYL: If "
        "thrips population exceeds 60 numbers or if rolling of half of leaf area of first and 2nd "
        "leaves in 10% of seedlings is noticed • Spray any one of the following insecticides"
    )

    def _answer(self, question, text):
        document = make_document("tnau", "unused")
        pipeline = _custom_pipeline(
            [Chunk("tnau::p29::c0", "tnau", 29, text, 0)], [[1.0, 0.0, 0.0]], [document]
        )
        return pipeline.answer(question)

    def test_long_blob_with_incidental_overlap_is_not_appended_and_not_cited(self):
        assert len(self.BLOB.split()) >= LONG_SENTENCE_WORDS

        result = self._answer(self.QUESTION, self.BEST + " " + self.BLOB)

        assert result.mode == "answered"
        assert result.answer_text == self.BEST
        assert [(c.doc_id, c.page_number) for c in result.sources] == [("tnau", 29)]

    def test_long_sentence_that_is_the_best_match_is_kept(self):
        filler = " ".join(["field operations"] * 40)
        long_best = (
            "Rice wet nursery area select 20 cents (800 m2) of land for raising seedlings for one "
            "hectare " + filler
        )
        assert len(long_best.split()) >= LONG_SENTENCE_WORDS

        result = self._answer(self.QUESTION, long_best + ".")

        assert result.mode == "answered"
        assert "20 cents (800 m2)" in result.answer_text

    def test_long_sentence_with_strong_overlap_is_retained(self):
        filler = " ".join(["field operations"] * 40)
        strong_long = (
            "Rice nursery area for raising seedlings is selected for one hectare " + filler + "."
        )
        assert len(strong_long.split()) >= LONG_SENTENCE_WORDS

        result = self._answer(self.QUESTION, self.BEST + " " + strong_long)

        assert "Rice nursery area for raising seedlings is selected for one hectare" in result.answer_text

    def test_short_weaker_sentences_are_never_filtered_by_relative_overlap(self):
        strong = "Wheat irrigation is required at tillering and flowering stages."
        weak = "Wheat growth stages differ across varieties and seasons."

        result = self._answer(
            "At which stages does the guide recommend irrigating wheat?", strong + " " + weak
        )

        assert strong in result.answer_text
        assert weak in result.answer_text

    def test_equally_strong_relevant_sentences_are_retained(self):
        first = "Wheat irrigation is required at tillering and flowering stages."
        second = "Wheat irrigation is also needed at crown root initiation stage."

        result = self._answer(
            "At which stages does the guide recommend irrigating wheat?", first + " " + second
        )

        assert first in result.answer_text
        assert second in result.answer_text


class TestSupportingSentenceLocality:
    WHEAT_Q = "At which stages does the guide recommend irrigating wheat?"
    HEADING = "Wheat crop requires minimum of 5 irrigations at the following critical stages."
    STAGES = (
        "I = Immediately after sowing II = Crown root initiation : 15-20 DAS III = Active "
        "tillering stage : 35-40 DAS IV = Flowering stage : 50-55 DAS."
    )
    FILLER = " Keep the field free of weeds. Level the land well. Avoid water logging."
    TOP_DRESSING = "TOP DRESSING Apply remaining half of N at crown root initiation stage (15-20 DAS)."

    def _pipeline(self, chunk_texts, doc_id="guide"):
        document = make_document(doc_id, "unused")
        chunks = [
            Chunk(f"{doc_id}::p{i + 1}::c{i}", doc_id, i + 1, text, 0)
            for i, text in enumerate(chunk_texts)
        ]
        embeddings = [[1.0 - 0.01 * i, 0.01 * i, 0.0] for i in range(len(chunk_texts))]
        return _custom_pipeline(chunks, embeddings, [document])

    def test_adjacent_list_sentence_is_kept_and_distant_sentence_in_chunk_is_dropped(self):
        text = self.HEADING + " " + self.STAGES + self.FILLER + " " + self.TOP_DRESSING
        result = self._pipeline([text]).answer(self.WHEAT_Q)

        assert result.mode == "answered"
        assert self.HEADING in result.answer_text
        for stage in ("Immediately after sowing", "Crown root initiation", "Active tillering", "Flowering stage : 50-55"):
            assert stage in result.answer_text
        assert "TOP DRESSING" not in result.answer_text

    def test_sentence_two_positions_away_in_same_chunk_is_kept(self):
        near = "Wheat needs a final irrigation at the grain filling stage : 70-75 DAS."
        text = self.HEADING + " Keep the field free of weeds. " + near
        result = self._pipeline([text]).answer(self.WHEAT_Q)

        assert near in result.answer_text

    def test_distant_weaker_sentence_from_another_chunk_is_dropped_and_not_cited(self, monkeypatch):
        import src.rag_pipeline as rag

        best = "Wheat crop requires minimum of 5 irrigations at the following critical stages."
        distant = "Wheat seedlings are given a stage specific light water spray in nurseries."
        pipeline = self._pipeline([best, distant])

        result = pipeline.answer(self.WHEAT_Q)
        assert result.mode == "answered"
        assert result.answer_text == best
        assert [c.page_number for c in result.sources] == [1]

        # Control: with the locality/overlap filter disabled the sentence returns.
        monkeypatch.setattr(rag, "SUPPORT_MAX_SENTENCE_GAP", -1)
        monkeypatch.setattr(rag, "SUPPORT_MIN_RELATIVE_OVERLAP", 0.0)
        control = pipeline.answer(self.WHEAT_Q)
        assert distant in control.answer_text

    def test_equally_strong_sentence_from_another_chunk_is_kept(self):
        first = "Wheat irrigation is required at tillering and flowering stages."
        second = "Wheat irrigation is also needed at crown root initiation stage."
        result = self._pipeline([first, second]).answer(self.WHEAT_Q)

        assert first in result.answer_text
        assert second in result.answer_text
        assert {c.page_number for c in result.sources} == {1, 2}

    def test_crop_list_question_is_exempt_from_the_locality_and_overlap_filter(self):
        from src.retriever import content_terms

        question = "Which crops are covered by the crop-specific Kisan Drone pesticide SOP?"
        strong = "However the crop-specific Kisan Drone pesticide SOP is covered for rice and maize."
        listing = "Drone pesticide SOP covers crops namely paddy, maize, cotton, groundnut, pigeon pea, safflower, sesame, soybean, sugarcane and wheat."
        question_terms = set(content_terms(question))
        strong_overlap = len(question_terms & set(content_terms(strong)))
        list_overlap = len(question_terms & set(content_terms(listing)))
        assert list_overlap < 0.75 * strong_overlap  # would be filtered if not exempt

        result = self._pipeline([strong, listing]).answer(question)

        assert result.mode == "answered"
        assert "sugarcane and wheat" in result.answer_text
