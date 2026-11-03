"""Tests for src.retriever (FAISS index, gating, persistence)."""

from __future__ import annotations

import numpy as np
import pytest

from src.retriever import FaissRetriever
from src.text_chunker import Chunk


def _chunk(doc_id: str = "doc_a", index: int = 0) -> Chunk:
    return Chunk(
        chunk_id=f"{doc_id}::p1::c{index}",
        doc_id=doc_id,
        page_number=1,
        text=f"text {index}",
        index=index,
    )


def _unit(dim: int, hot: int) -> np.ndarray:
    vector = np.zeros(dim, dtype=np.float32)
    vector[hot] = 1.0
    return vector


class TestConstruction:
    def test_add_shape_validation(self):
        retriever = FaissRetriever(dimension=4)
        with pytest.raises(ValueError, match="expected embeddings"):
            retriever.add(np.zeros((2, 5), dtype=np.float32), [_chunk()])

    def test_add_count_validation(self):
        retriever = FaissRetriever(dimension=4)
        with pytest.raises(ValueError, match="mismatch"):
            retriever.add(np.zeros((2, 4), dtype=np.float32), [_chunk()])

    def test_bad_dimension(self):
        with pytest.raises(ValueError, match="dimension"):
            FaissRetriever(dimension=0)


class TestSearch:
    def test_empty_index_returns_nothing(self):
        retriever = FaissRetriever(dimension=4)
        assert retriever.search(_unit(4, 0)) == []

    def test_ordering_by_similarity(self):
        retriever = FaissRetriever(dimension=4, min_score=0.0)
        embeddings = np.stack([_unit(4, 0), _unit(4, 1), _unit(4, 2)])
        chunks = [_chunk(index=i) for i in range(3)]
        retriever.add(embeddings, chunks)

        query = np.array([0.9, 0.1, 0.0, 0.0], dtype=np.float32)
        query /= np.linalg.norm(query)
        results = retriever.search(query, top_k=3)
        assert [r.chunk.index for r in results] == [0, 1, 2]
        assert results[0].score > results[1].score > results[2].score

    def test_min_score_gate_filters_irrelevant(self):
        retriever = FaissRetriever(dimension=4, min_score=0.40)
        embeddings = np.stack([_unit(4, 0), _unit(4, 1)])
        retriever.add(embeddings, [_chunk(index=0), _chunk(index=1)])

        results = retriever.search(_unit(4, 0), top_k=2)
        assert len(results) == 1, "orthogonal vector must be gated out"
        assert results[0].chunk.index == 0
        assert results[0].score == pytest.approx(1.0, abs=1e-5)

    def test_bad_top_k(self):
        retriever = FaissRetriever(dimension=4)
        with pytest.raises(ValueError, match="top_k"):
            retriever.search(_unit(4, 0), top_k=0)

    def test_bm25_lexical_search_finds_specific_evidence(self):
        retriever = FaissRetriever(dimension=4, min_score=0.0)
        chunks = [
            Chunk("generic::p1::c0", "generic", 1, "Modern crop production uses drones and inputs.", 0),
            Chunk("safety::p22::c0", "safety", 22, "Do not spray a drone near ponds, rivers, or canals; maintain a minimum distance of 100m.", 1),
        ]
        retriever.add(
            np.stack([_unit(4, 0), _unit(4, 1)]),
            chunks,
        )

        results = retriever.search_lexical(
            "minimum distance from ponds rivers canals during drone pesticide spraying",
            top_k=2,
        )

        assert results[0].chunk.doc_id == "safety"
        assert results[0].lexical_score > results[1].lexical_score
        assert "distance" in results[0].matched_terms

    def test_hybrid_rrf_uses_lexical_rank_and_preserves_dense_score(self):
        retriever = FaissRetriever(dimension=4, min_score=0.0)
        chunks = [
            Chunk("generic::p1::c0", "generic", 1, "Modern crop production uses drones and inputs.", 0),
            Chunk("safety::p22::c0", "safety", 22, "Do not spray a drone near ponds, rivers, or canals; maintain a minimum distance of 100m.", 1),
        ]
        retriever.add(
            np.stack([_unit(4, 0), _unit(4, 1)]),
            chunks,
        )

        results = retriever.search_hybrid(
            _unit(4, 0),
            "minimum distance from ponds rivers canals during drone pesticide spraying",
            top_k=2,
        )

        assert results[0].chunk.doc_id == "safety"
        assert results[0].score == pytest.approx(0.0, abs=1e-5)
        assert results[0].fused_score >= results[1].fused_score
        assert results[0].term_coverage > results[1].term_coverage

    def test_crop_anchor_normalizes_paddy_to_rice_and_rejects_wheat_maize_mix(self):
        from src.retriever import crop_anchors

        assert crop_anchors("paddy irrigation") == frozenset({"rice"})
        assert crop_anchors("wheat") == frozenset({"wheat"})
        assert crop_anchors("maize crop") == frozenset({"maize"})
        assert crop_anchors("betelvine irrigation") == frozenset()

    def test_specific_safety_query_rejects_generic_agricultural_intro(self):
        retriever = FaissRetriever(dimension=4, min_score=0.0)
        text = "Modern crop production uses drones and pesticide inputs."
        from src.retriever import RetrievedPassage

        passage = RetrievedPassage(
            chunk=Chunk("generic::p1::c0", "generic", 1, text, 0), score=0.81
        )

        accepted, reason = retriever.relevant_evidence(
            "What minimum distance should be maintained from ponds, rivers, and canals during drone pesticide spraying?",
            [passage],
        )

        assert accepted == []
        assert "key terms" in reason

    def test_table_of_contents_cannot_support_a_guidance_answer(self):
        from src.retriever import RetrievedPassage

        retriever = FaissRetriever(dimension=4, min_score=0.0)
        text = "CONTENTS 1. Preface 1 2. Safety requirements PAGE NO 11"
        passage = RetrievedPassage(
            chunk=Chunk("sop::p1::c0", "sop", 1, text, 0), score=0.9
        )

        accepted, reason = retriever.relevant_evidence(
            "What operational and safety measures does the drone pesticide SOP require?",
            [passage],
        )

        assert accepted == []
        assert reason is not None

    def test_context_qualifier_must_be_present_in_evidence(self):
        from src.retriever import RetrievedPassage

        retriever = FaissRetriever(dimension=4, min_score=0.0)
        text = "Transplanted hybrid rice nursery: basal DAP is 2 kg per cent."
        passage = RetrievedPassage(
            chunk=Chunk("rice::p40::c0", "rice", 40, text, 0), score=0.85
        )

        accepted, reason = retriever.relevant_evidence(
            "What basal DAP application is advised for less fertile rice nursery soil?",
            [passage],
        )

        assert accepted == []
        assert reason is not None

    def test_preplant_watering_query_rejects_rice_water_management_passage(self):
        from src.retriever import RetrievedPassage

        retriever = FaissRetriever(dimension=4, min_score=0.0)
        text = (
            "Field should be irrigated individually from a channel. "
            "Small bund may be formed parallel to the main bund. "
            "Maintain 2 cm of water up to seven days of transplanting."
        )
        passage = RetrievedPassage(
            chunk=Chunk("tnau_agriculture::p38::c34", "tnau_agriculture", 38, text, 0),
            score=0.8574,
        )

        accepted, reason = retriever.relevant_evidence(
            "y does farmer need to water ground before planting small plants",
            [passage],
        )

        assert accepted == []
        assert reason is not None

    def test_preplant_watering_requires_timing_and_action_in_same_clause(self):
        from src.retriever import RetrievedPassage

        retriever = FaissRetriever(dimension=4, min_score=0.0)
        text = (
            "One month before planting, select healthy turmeric rhizomes. "
            "Adopt need based irrigation with rose can or suitable sprinklers."
        )
        passage = RetrievedPassage(
            chunk=Chunk("horticulture::p185::c182", "horticulture", 185, text, 0),
            score=0.8105,
        )

        accepted, reason = retriever.relevant_evidence(
            "y does farmer need to water ground before planting small plants",
            [passage],
        )

        assert accepted == []
        assert reason is not None

    def test_preplant_watering_rejects_water_used_for_a_biofertilizer_slurry(self):
        from src.retriever import RetrievedPassage

        retriever = FaissRetriever(dimension=4, min_score=0.0)
        text = (
            "Before planting the sugarcane setts can be treated with biofertilizer "
            "prepared as slurry with 250 L of water."
        )
        passage = RetrievedPassage(
            chunk=Chunk("tnau_agriculture::p308::c311", "tnau_agriculture", 308, text, 0),
            score=0.8471,
        )

        accepted, reason = retriever.relevant_evidence(
            "y does farmer need to water ground before planting small plants",
            [passage],
        )

        assert accepted == []
        assert reason is not None


class TestPersistence:
    def test_save_load_roundtrip(self, tmp_path):
        retriever = FaissRetriever(dimension=4, min_score=0.3)
        retriever.add(np.stack([_unit(4, 0)]), [_chunk()])
        index_path = tmp_path / "index.bin"
        chunks_path = tmp_path / "chunks.jsonl"
        retriever.save(index_path, chunks_path)

        loaded = FaissRetriever.load(index_path, chunks_path, min_score=0.3)
        assert loaded.size == 1
        results = loaded.search(_unit(4, 0), top_k=1)
        assert results[0].chunk.chunk_id == "doc_a::p1::c0"
        assert results[0].score == pytest.approx(1.0, abs=1e-5)

    def test_missing_index_raises_with_guidance(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="Build it first"):
            FaissRetriever.load(tmp_path / "nope.bin", tmp_path / "nope.jsonl")

    def test_manifest_count_mismatch_raises(self, tmp_path):
        retriever = FaissRetriever(dimension=4)
        retriever.add(np.stack([_unit(4, 0), _unit(4, 1)]), [_chunk(index=0), _chunk(index=1)])
        index_path = tmp_path / "index.bin"
        chunks_path = tmp_path / "chunks.jsonl"
        retriever.save(index_path, chunks_path)
        # Truncate manifest to simulate corruption.
        lines = chunks_path.read_text(encoding="utf-8").splitlines()
        chunks_path.write_text(lines[0] + "\n", encoding="utf-8")
        with pytest.raises(ValueError, match="corrupt index/manifest"):
            FaissRetriever.load(index_path, chunks_path)


WHEAT_Q = [
    "At what stages is it recommended to irrigate the wheat?",
    "When should wheat be watered?",
    "At what stages does the wheat crop need irrigation?",
    "At which stages does the guide recommend watering wheat?",
    "What irrigation stages does the guide list for wheat?",
    "Under what conditions is it recommended to irrigate wheat?",
    "At which stages does the guide recommend irrigating wheat?",
]
TNAU_WHEAT = (
    "Wheat crop requires minimum of 5 irrigations at the following critical stages. "
    "I = Immediately after sowing II = Crown root initiation : 15-20 DAS "
    "III = Active tillering stage : 35-40 DAS IV = Flowering stage : 50-55 DAS "
    "V = Grain filling stage : 70-75 DAS."
)
DRONE_SOP = (
    "This latest Crop specific Standard Operational Procedures have been brought out for guidance "
    "on technical, operational and safety requirements during spraying of pesticides in 10 crops "
    "namely rice, maize and wheat, under the varying external climatic conditions such as "
    "temperature, humidity, wind speeds, crop conditions and stage."
)


def _passage(doc_id, page, text, score=0.83):
    from src.retriever import RetrievedPassage

    return RetrievedPassage(chunk=Chunk(f"{doc_id}::p{page}::c0", doc_id, page, text, 0), score=score)


class TestQuestionPhrasingNormalization:
    @pytest.mark.parametrize("question", WHEAT_Q)
    def test_question_phrasing_is_not_a_mandatory_evidence_term(self, question):
        from src.retriever import query_specific_terms

        incidental = {"recommended", "need", "needed", "list", "watered", "watering", "under"}
        assert not (query_specific_terms(question) & incidental)

    def test_watered_and_watering_map_to_irrigation_but_plain_water_does_not(self):
        from src.retriever import content_terms

        assert "irrigate" in content_terms("When should wheat be watered?")
        assert "irrigate" in content_terms("wheat watering stages")
        assert "irrigate" not in content_terms("keep a distance from water bodies")

    @pytest.mark.parametrize("question", WHEAT_Q)
    def test_correct_wheat_evidence_is_not_rejected_by_incidental_wording(self, question):
        retriever = FaissRetriever(dimension=4, min_score=0.0)

        accepted, reason = retriever.relevant_evidence(
            question, [_passage("tnau_agriculture", 136, TNAU_WHEAT)]
        )

        assert reason is None
        assert [p.chunk.page_number for p in accepted] == [136]

    def test_under_what_conditions_does_not_prefer_unrelated_drone_sop_text(self):
        from src.rag_pipeline import ExtractiveEvidenceGenerator

        retriever = FaissRetriever(dimension=4, min_score=0.0)
        question = "Under what conditions is it recommended to irrigate wheat?"
        passages = [
            _passage("tn_crop_sop_2023", 6, DRONE_SOP, score=0.84),
            _passage("tnau_agriculture", 136, TNAU_WHEAT, score=0.83),
        ]

        accepted, _ = retriever.relevant_evidence(question, passages)

        assert "tnau_agriculture" in {p.chunk.doc_id for p in accepted}
        answer = ExtractiveEvidenceGenerator().generate(question, accepted)
        assert "irrigations" in answer
        assert "pesticides" not in answer

    def test_a_concrete_condition_is_still_a_required_term(self):
        from src.retriever import query_specific_terms

        retriever = FaissRetriever(dimension=4, min_score=0.0)
        question = "Which fertilizer rate is advised under saline conditions for rice?"
        assert {"saline", "condition"} <= query_specific_terms(question)

        accepted, reason = retriever.relevant_evidence(
            question, [_passage("tnau_agriculture", 40, "Rice fertilizer rate is 100 kg N per hectare in normal soil.")]
        )

        assert accepted == []
        assert reason is not None

    def test_what_conditions_boilerplate_is_dropped_but_soil_conditions_is_kept(self):
        from src.retriever import query_specific_terms

        assert "condition" not in query_specific_terms("Under what conditions should wheat be irrigated?")
        assert "condition" in query_specific_terms("What soil conditions suit wheat?")

    def test_watering_wording_does_not_weaken_the_preplant_abstention(self):
        retriever = FaissRetriever(dimension=4, min_score=0.0)
        text = (
            "Field should be irrigated individually from a channel. "
            "Maintain 2 cm of water up to seven days of transplanting."
        )

        for question in (
            "y does farmer need to water ground before planting small plants",
            "Why does a farmer need watering the ground before planting small plants?",
        ):
            accepted, reason = retriever.relevant_evidence(
                question, [_passage("tnau_agriculture", 31, text)]
            )
            assert accepted == []
            assert reason is not None

    def test_required_stays_a_discriminating_term_so_drone_text_cannot_answer_an_irrigation_question(self):
        from src.rag_pipeline import ExtractiveEvidenceGenerator

        retriever = FaissRetriever(dimension=4, min_score=0.0)
        question = "How much irrigation is required in wheat and in what condition?"
        drone_passage = _passage(
            "tn_crop_sop_2023",
            14,
            "The drone has to fly near the crop canopy as much as possible to avoid drift during "
            "operation and to safeguard the wheat environment.",
            score=0.84,
        )

        accepted, _ = retriever.relevant_evidence(question, [drone_passage])

        assert accepted == []


class TestContextualWateringNormalization:
    @pytest.mark.parametrize(
        "question",
        [
            "When to water wheat?",
            "How to water wheat?",
            "Should I water the wheat daily?",
            "When should wheat be watered?",
            "wheat watering stages",
        ],
    )
    def test_watering_a_crop_is_treated_as_irrigation(self, question):
        from src.retriever import content_terms

        terms = content_terms(question)
        assert "irrigate" in terms and "wheat" in terms
        assert "water" not in terms

    @pytest.mark.parametrize(
        "question",
        [
            "What minimum distance from water bodies should be kept during drone spraying?",
            "How much water is used for spray volume per hectare of wheat?",
            "What does the guide say about water management in wheat?",
            "Why does a farmer need to water ground before planting small plants?",
        ],
    )
    def test_other_uses_of_water_do_not_become_irrigation(self, question):
        from src.retriever import content_terms

        terms = content_terms(question)
        assert "water" in terms
        assert "irrigate" not in terms

    def test_when_to_water_wheat_selects_the_irrigation_sentence_not_the_fertilizer_table(self, monkeypatch):
        import re

        import src.retriever as retriever_module
        from src.rag_pipeline import ExtractiveEvidenceGenerator

        text = (
            "124 Wheat - Plains Soil : Mixed black calcareous series FN = 8.83 T water soluble "
            "NPK targets for wheat yield 3.5 t ha " + " ".join(["SN SP SK FN FP2O5 FK2O 112 90 60"] * 8) + ". "
            "WATER MANAGEMENT The crop requires 4 - 6 irrigations depending on the soil type and rainfall. "
            "Wheat crop requires minimum of 5 irrigations at the following critical stages."
        )
        passages = [_passage("tnau_agriculture", 136, text)]
        question = "When to water wheat?"

        answer = ExtractiveEvidenceGenerator().generate(question, passages)
        assert "irrigations" in answer
        assert "calcareous" not in answer

        # Control: without the contextual rule the fertilizer sentence wins.
        monkeypatch.setattr(retriever_module, "_WATER_CROP_VERB_RE", re.compile(r"(?P<lead>(?!x)x)(?P<tail>)"))
        control = ExtractiveEvidenceGenerator().generate(question, passages)
        assert "calcareous" in control

    def test_watering_question_keeps_crop_and_required_term_protection(self):
        retriever = FaissRetriever(dimension=4, min_score=0.0)

        # A rice passage cannot answer a wheat watering question.
        accepted, reason = retriever.relevant_evidence(
            "When to water wheat?",
            [_passage("tnau_agriculture", 29, "Rice should be irrigated to keep 2 cm of water in the field.")],
        )
        assert accepted == []
        assert reason is not None

        # A concrete fertilizer-rate question is still not answered by irrigation text.
        accepted, _ = retriever.relevant_evidence(
            "Which fertilizer rate is advised under saline conditions for rice?",
            [_passage("tnau_agriculture", 29, "Rice should be irrigated to keep 2 cm of water in the field.")],
        )
        assert accepted == []
