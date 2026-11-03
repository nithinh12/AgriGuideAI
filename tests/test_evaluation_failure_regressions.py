"""Regression tests for failures found in the 2026-11-01 48-case evaluation.

Each group names the recorded failure it pins down. The tests use small
synthetic indexes (no embedding model) except where noted.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.rag_pipeline import ExtractiveEvidenceGenerator, RAGPipeline
from src.retriever import (
    FaissRetriever,
    RetrievedPassage,
    content_terms,
    crop_anchors,
    query_specific_terms,
)
from src.text_chunker import Chunk
from tests.conftest import FakeEmbedder, make_document

FILLER = (
    "Seed treatment with a fungicide protects seedlings. Weeds are removed by hand "
    "twice. Pods are dried in the sun and stored in gunny bags."
)


def _retriever(chunks):
    retriever = FaissRetriever(dimension=3, min_score=0.0)
    retriever.add(np.tile(np.array([[1.0, 0.0, 0.0]], dtype=np.float32), (len(chunks), 1)), chunks)
    return retriever


def _chunk(doc, page, text, index):
    return Chunk(f"{doc}::p{page}::c{index}", doc, page, text, index)


def _passages(retriever, score=0.8):
    return [RetrievedPassage(chunk=c, score=score) for c in retriever._chunks]


def _pipeline(chunks, top_k=5):
    retriever = _retriever(chunks)
    docs = {c.doc_id: make_document(c.doc_id) for c in chunks}
    return RAGPipeline(
        retriever=retriever,
        embedder=FakeEmbedder(np.array([1.0, 0.0, 0.0], dtype=np.float32)),
        documents_by_id=docs,
        generator=ExtractiveEvidenceGenerator(),
        top_k=top_k,
    )


# --- crop identity is carried by the preceding chunk (en_irrig_01, en_fert_01, ...) ---------


class TestCropContextInheritance:
    HEAD = "GROUNDNUT crop management. Sowing and seed treatment are described here. " + FILLER
    BODY = (
        "WATER MANAGEMENT Regulate irrigation as per the growth phase of the crop. "
        "Pegging, flowering and pod development phases are critical for irrigation "
        "during which period adequate soil moisture is essential."
    )
    QUESTION = "Which growth stages of groundnut are critical for irrigation?"

    def test_chunk_without_a_crop_name_inherits_it_from_the_previous_page(self):
        retriever = _retriever(
            [_chunk("guide", 10, self.HEAD, 0), _chunk("guide", 11, self.BODY, 1)]
        )
        assert crop_anchors(self.BODY) == frozenset()
        accepted, reason = retriever.relevant_evidence(self.QUESTION, _passages(retriever)[1:])
        assert reason is None
        assert [p.chunk.page_number for p in accepted] == [11]
        assert accepted[0].crop_context_inherited is True

    def test_inheritance_stops_after_one_hop(self):
        middle = "Plants are lifted carefully after the soil is loosened. " + FILLER
        retriever = _retriever(
            [
                _chunk("guide", 10, self.HEAD, 0),
                _chunk("guide", 10, middle, 1),
                _chunk("guide", 11, self.BODY, 2),
            ]
        )
        accepted, _ = retriever.relevant_evidence(self.QUESTION, _passages(retriever)[2:])
        assert accepted == []

    def test_inheritance_does_not_cross_documents_or_skip_pages(self):
        other_doc = _retriever([_chunk("a", 10, self.HEAD, 0), _chunk("b", 11, self.BODY, 0)])
        assert other_doc.relevant_evidence(self.QUESTION, _passages(other_doc)[1:])[0] == []
        skipped = _retriever([_chunk("a", 10, self.HEAD, 0), _chunk("a", 12, self.BODY, 1)])
        assert skipped.relevant_evidence(self.QUESTION, _passages(skipped)[1:])[0] == []

    def test_a_chunk_that_names_another_crop_keeps_its_own_crop(self):
        wheat_body = self.BODY + " Wheat is irrigated at tillering."
        retriever = _retriever(
            [_chunk("guide", 10, self.HEAD, 0), _chunk("guide", 11, wheat_body, 1)]
        )
        accepted, _ = retriever.relevant_evidence(self.QUESTION, _passages(retriever)[1:])
        assert accepted == []

    def test_inherited_crop_is_reported_on_the_answer(self):
        pipeline = _pipeline([_chunk("guide", 10, self.HEAD, 0), _chunk("guide", 11, self.BODY, 1)])
        result = pipeline.answer(self.QUESTION)
        assert result.mode == "answered"
        assert "Pegging, flowering and pod development" in result.answer_text
        assert result.warnings and "page 11" in result.warnings[0]


# --- term variants that broke the overlap checks ---------------------------------------------


class TestTermVariants:
    @pytest.mark.parametrize(
        "left, right",
        [
            ("peanut", "groundnut"),  # kn/hi machine translations say "peanut"
            ("phases", "stage"),  # "growth stages" vs "growth phases"
            ("applied", "apply"),  # "should be applied" vs "Apply gypsum"
            ("stagnation", "stagnates"),
            ("soyabean", "soybean"),
            ("cutting", "cut"),  # "main crop is cut" vs "after cutting"
            ("ratooning", "ratoon"),
            ("hectare", "ha"),  # "per hectare" vs "kg/ha"
        ],
    )
    def test_variants_normalise_to_one_term(self, left, right):
        assert content_terms(left) == content_terms(right)

    def test_kg_per_ha_keeps_the_unit_term(self):
        assert "ha" in content_terms("Apply gypsum @ 400 kg/ha")

    def test_quantity_and_degree_phrasing_is_not_a_discriminating_term(self):
        assert query_specific_terms("How much gypsum should be applied to groundnut?") == {
            "apply",
            "gypsum",
        }
        assert "most" not in content_terms("When does groundnut need soil moisture the most?")

    def test_standing_water_is_not_confused_with_crop_stand(self):
        """A general -ing stemmer made "standing water" match "the field stand" (plant population)."""
        assert content_terms("standing") != content_terms("stand")

    def test_plant_spacing_is_not_confused_with_buffer_distance(self):
        assert "distance" in content_terms("minimum distance from ponds")
        assert content_terms("distance") != content_terms("spacing")

    def test_sorghum_is_an_enforced_crop(self):
        assert crop_anchors("seed rate for sorghum") == frozenset({"sorghum"})

    def test_sorghum_question_is_not_answered_from_another_crops_sowing_text(self):
        """en_crop_03: another crop's 'Seed rate ... Spacing' sentences answered a sorghum question."""
        retriever = _retriever(
            [
                _chunk("guide", 5, "PEARL MILLET SOWING Seed rate 10 kg/ha. Spacing 45 x 15 cm. " + FILLER, 0),
                _chunk("guide", 6, "SORGHUM SOWING In pure crop maintain the seed rate at 10 kg/ha. " + FILLER, 1),
            ]
        )
        accepted, _ = retriever.relevant_evidence(
            "What seed rate does the guide recommend for a pure crop of sorghum?",
            _passages(retriever),
        )
        assert [p.chunk.page_number for p in accepted] == [6]


# --- a term the knowledge base never mentions (en_unsup_absent_01, hi/kn adjacent) ----------


class TestUnknownTerms:
    CHUNKS = [
        _chunk("guide", 1, "PIGEON PEA Spacing 30 x 10 cm is adopted for growing the crop. Plant protection follows.", 0),
        _chunk("guide", 2, "COTTON Plant spacing 90 x 60 cm is adopted for growing cotton in irrigated fields.", 1),
        _chunk("guide", 3, "MAIZE Plant spacing 60 x 25 cm is adopted for growing maize hybrids.", 2),
    ]

    def test_unknown_subject_cannot_be_replaced_by_common_words(self):
        retriever = _retriever(self.CHUNKS)
        accepted, reason = retriever.relevant_evidence(
            "What plant spacing is recommended for growing saffron?", _passages(retriever)
        )
        assert accepted == []
        assert "saffron" in reason and "nowhere in the knowledge base" in reason

    def test_same_question_shape_for_a_known_crop_is_still_answered(self):
        retriever = _retriever(self.CHUNKS)
        accepted, reason = retriever.relevant_evidence(
            "What plant spacing is recommended for growing maize?", _passages(retriever)
        )
        assert reason is None
        assert accepted[0].chunk.page_number == 3

    def test_pipeline_abstains_with_no_citation(self):
        result = _pipeline(self.CHUNKS).answer("What plant spacing is recommended for growing saffron?")
        assert result.mode == "abstained"
        assert result.sources == ()

    def test_misspelled_molecule_in_a_translated_question_abstains(self):
        """hi_unsup_adjacent_01: 'Chlorentraniliprol' is unknown, so days/harvest/rice wording cannot answer it."""
        chunks = [
            _chunk("guide", 1, "RICE Harvest the paddy crop when 90 percent of the panicles turn golden yellow. Rice is drained 10 days before harvest.", 0),
            _chunk("guide", 2, "Chlorantraniliprole is listed for stem borer. Drone spraying on rice uses 10 litres per hectare.", 1),
        ]
        result = _pipeline(chunks).answer(
            "After spraying Chlorentraniliprol on paddy from a drone, how many days of waiting "
            "period should be kept before harvesting?"
        )
        assert result.mode == "abstained"
        assert result.sources == ()

    def test_maize_waiting_period_is_never_a_rice_answer(self):
        chunks = [
            _chunk("sop", 1, "MAIZE Waiting period after spraying chlorantraniliprole on maize is 15 days before harvest of the maize crop.", 0),
            _chunk("sop", 2, "RICE Drone spraying on rice uses a flying height of 2 metres above the rice canopy.", 1),
        ]
        result = _pipeline(chunks).answer(
            "What is the waiting period before harvest after spraying chlorantraniliprole on rice with a drone?"
        )
        assert result.mode == "abstained"
        assert result.sources == ()


# --- accepted passages are ordered by how well they cover the question (en_crop_01) --------


class TestAcceptedPassageOrder:
    def test_passage_covering_every_discriminating_term_is_listed_first(self):
        partial = (
            "MAIZE HYBRID seed rate depends on the seed size; sow 6 rows in plot 1 of the "
            "hybrid trial. " + FILLER
        )
        full = "MAIZE SEED RATE Adopt the seed rate of 20 kg/ha for the hybrid CO 6 and 25 kg/ha for COBC 1 maize."
        retriever = _retriever([_chunk("guide", 1, partial, 0), _chunk("guide", 2, full, 1)])
        accepted, _ = retriever.relevant_evidence(
            "What seed rate is recommended for the maize hybrid CO 6 and COBC 1?", _passages(retriever)
        )
        assert [p.chunk.page_number for p in accepted][0] == 2

    def test_ties_keep_the_fused_order(self):
        same = "MAIZE Adopt the seed rate of 20 kg/ha for maize. "
        retriever = _retriever([_chunk("guide", 1, same, 0), _chunk("guide", 2, same + "Extra words here.", 1)])
        accepted, _ = retriever.relevant_evidence("What seed rate for maize?", _passages(retriever))
        assert [p.chunk.page_number for p in accepted] == [1, 2]


# --- list continuation in extraction (en_irrig_02, hi/kn_crop_02) ---------------------------


class TestListContinuation:
    WATER = (
        "4. WATER MANAGEMENT i. Irrigate immediately after cutting the main crop. "
        "ii. Irrigation should not be delayed for more than 24 hours after cutting. "
        "iii. Irrigate on 3rd or 4th day after cutting. "
        "iv. Subsequently irrigate once in 7 - 10 days. "
        "v. Stop irrigation on 70 - 80 days after ratooning. "
        "5. HARVEST Harvest the crop when the grains turn yellow."
    )
    QUESTION = "How should a ratoon sorghum crop be irrigated after the main crop is cut?"

    def _generate(self, text, question=None):
        passage = RetrievedPassage(chunk=Chunk("g::p1::c0", "g", 1, text, 0), score=0.8)
        return ExtractiveEvidenceGenerator().generate(question or self.QUESTION, [passage])

    def test_every_item_of_the_irrigation_list_is_quoted(self):
        answer = self._generate("RATOON SORGHUM CROP 1. " + self.WATER)
        for point in ("immediately after cutting", "3rd or 4th day", "7 - 10 days", "70 - 80 days"):
            assert point in answer

    def test_continuation_is_verbatim_and_in_source_order(self):
        answer = self._generate("RATOON SORGHUM CROP 1. " + self.WATER)
        assert answer.index("immediately") < answer.index("3rd or 4th") < answer.index("7 - 10") < answer.index("70 - 80")

    def test_continuation_never_starts_an_answer(self):
        """Neighbours share 'irrigation' but nothing selects a first sentence, so there is no answer."""
        text = "Soil is prepared well. Irrigation should be given at sowing. Irrigation is repeated weekly."
        assert self._generate(text, "How should a ratoon sorghum crop be irrigated after the main crop is cut?") == ""

    def test_continuation_respects_the_word_budget(self):
        long_items = " ".join(
            "Irrigate once more after {} with {} litres of water per plot.".format(day, 10 + day)
            for day in range(1, 30)
        )
        answer = self._generate("Irrigate immediately after cutting the main crop. " + long_items)
        assert len(answer.split()) <= 125


# --- hi_hort_01 / kn_hort_01: a 100+-word run-on timed out the answer translation -------------


class TestTranslationUnits:
    RUN_ON = (
        "Spacing PKM 1, Paiyur 1, COTH 2, TNAU Tomato Hybrid CO 3 : 60 x 45 cm CO 3 : 45 x 30 cm "
        "Mulching Mulch with black LDPE sheets of 25 micron thickness and bury both the ends into "
        "the soil to a depth of 10 cm Weed control Apply Pendimethalin 1.0 kg a.i./ha or "
        "Fluchloralin 1.0 kg a.i / ha as pre -emergence herbicide, followed by hand weeding once "
        "at 30 days after planting."
    )

    def test_short_sentences_are_left_alone(self):
        from src.multilingual_flow import split_for_translation

        sentence = "Apply gypsum @ 400 kg/ha on the 40th to 45th day of sowing."
        assert split_for_translation(sentence) == [sentence]

    def test_long_run_on_is_split_into_bounded_units_without_losing_a_word(self):
        from src.multilingual_flow import MAX_TRANSLATION_WORDS, split_for_translation

        units = split_for_translation(self.RUN_ON)
        assert len(units) > 1
        assert all(len(unit.split()) <= MAX_TRANSLATION_WORDS for unit in units)
        assert " ".join(units).split() == self.RUN_ON.split()

    def test_numbers_units_and_dimensions_are_never_cut(self):
        from src.multilingual_flow import split_for_translation

        text = " ".join(["Row spacing 60 x 45 cm and plant spacing 30 x 15 cm are adopted for the hybrid."] * 6)
        for unit in split_for_translation(text):
            assert not unit.endswith(("60", "x", "45", "30", "15"))
            assert not unit.startswith(("x ", "cm", "kg"))
        assert " ".join(split_for_translation(text)).split() == text.split()

    def test_answer_translation_sends_the_units_not_the_run_on(self):
        from src.multilingual_flow import MAX_TRANSLATION_WORDS, _translate_answer

        received = []

        class Recorder:
            def translate_batch(self, texts, source, target):
                received.extend(texts)
                return ["हिन्दी पाठ"] * len(texts)

        _translate_answer(Recorder(), self.RUN_ON, "hi")
        assert received and all(len(text.split()) <= MAX_TRANSLATION_WORDS for text in received)
