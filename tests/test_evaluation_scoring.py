"""Tests for the evaluation scoring rules and the 48-case runner plumbing.

No model is loaded: the runner is exercised with a stand-in pipeline and
translator, and the dataset is checked against the saved chunk index text.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluation import run_evaluation, scoring
from src.rag_pipeline import AnswerResult, SourceCitation

ROOT = Path(__file__).resolve().parents[1]
CASES = run_evaluation.load_cases()
BY_ID = {c["id"]: c for c in CASES}
RELATED = scoring.load_related_evidence(run_evaluation.RELATED_PATH)


# ---------------------------------------------------------------- normalisation
@pytest.mark.parametrize(
    "haystack,needle",
    [
        ("irrigate once in 7 - 10 days", "7-10 days"),
        ("irrigate once in 7–10 days", "7 - 10 days"),  # en dash
        ("seed rate at 10kg/ha", "10 kg/ha"),
        ("seed rate is 10 kg/ha", "10kg/ha"),
        ("Apply GYPSUM @ 400 KG / HA", "gypsum @ 400 kg/ha"),
        ("about 1,000 kg", "1000 kg"),
        ("rate 10.0 kg/ha", "10 kg/ha"),
        ("१० किलो", "10"),  # Devanagari digits
        ("heavy rains are forecast", "heavy rain"),
    ],
)
def test_harmless_formatting_differences_match(haystack, needle):
    assert scoring.contains(haystack, needle)


@pytest.mark.parametrize(
    "haystack,needle",
    [
        ("apply 400 kg/ha", "40 kg/ha"),  # dosage must not shrink to a prefix
        ("apply 40 kg/ha", "400 kg/ha"),
        ("apply 140 kg/ha", "40 kg/ha"),
        ("apply 2.5 kg/ha", "5 kg/ha"),
        ("seed rate 10 g/ha", "10 kg/ha"),  # unit differs
        ("once in 7-10 days", "7-12 days"),
        ("irrigate on 4th day", "3rd or 4th day"),
        ("stop irrigation 70-80 days after ratooning", "7-10 days"),
        ("maize seed rate", "sorghum seed rate"),  # crop differs
        ("40th to 45th day", "30th to 45th day"),  # timing differs
    ],
)
def test_substantive_differences_do_not_match(haystack, needle):
    assert not scoring.contains(haystack, needle)


def test_empty_needle_never_matches():
    assert not scoring.contains("anything", "")


# ------------------------------------------------------------------- dataset
def test_dataset_shape_and_approved_questions():
    assert len(CASES) == 48
    for language in ("en", "hi", "kn"):
        assert sum(1 for c in CASES if c["language"] == language) == 16
    assert "en_fert_03" not in BY_ID
    assert BY_ID["en_crop_01"]["question"] == "What seed rate is recommended for TNAU Maize Hybrid CO 6 and for COBC 1?"
    assert BY_ID["en_crop_02"]["question"] == "What seed rate and row spacing are recommended for line sowing of finger millet?"


def test_irrig_02_and_fert_02_require_the_complete_recommendation():
    for lang in ("en", "hi", "kn"):
        assert BY_ID["%s_irrig_02" % lang]["required_points"] == [
            "immediately after cutting", "3rd or 4th day", "7 - 10 days", "70 - 80 days"]
        assert BY_ID["%s_fert_02" % lang]["required_points"] == [
            "20 kg N", "80 kg P", "40 kg K", "40 kg of S", "220 kg/ha"]


def test_translated_cases_share_gold_data_with_their_english_twin():
    gold_fields = ("expected_behavior", "reference_answer", "gold_terms", "required_points",
                   "must_preserve", "gold_doc_id", "gold_pages", "gold_chunk_ids", "evidence_quotes")
    for case in CASES:
        if case["language"] == "en":
            continue
        twin = BY_ID["en_" + case["id"][3:]]
        for field in gold_fields:
            assert case[field] == twin[field], (case["id"], field)


def test_gold_evidence_is_present_in_the_indexed_chunks():
    chunks = {}
    for line in (ROOT / "data" / "processed" / "chunks.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        chunks[row["chunk_id"]] = row
    for case in CASES:
        if case["language"] != "en" or case["expected_behavior"] != "answer":
            continue
        text = " ".join(chunks[cid]["text"] for cid in case["gold_chunk_ids"])
        for cid in case["gold_chunk_ids"]:
            assert chunks[cid]["doc_id"] == case["gold_doc_id"]
            assert chunks[cid]["page_number"] in case["gold_pages"]
        for term in case["gold_terms"] + case["required_points"]:
            assert scoring.contains(text, term), (case["id"], term)
        for quote in case["evidence_quotes"]:
            assert scoring.contains(text, quote), (case["id"], quote)


# ------------------------------------------------------------------- scoring
def _flow(case, mode="answered", answer="", sources=(), status=None, translated=None, error=None):
    return {
        "status": status or ("english" if case["language"] == "en" else "translated"),
        "english_question": case["english_reference_question"],
        "mode": mode,
        "answer_text": answer,
        "translated_answer": translated,
        "sources": list(sources),
        "error": error,
    }


def _src(case, page=None, excerpt=None, doc=None):
    return {
        "doc_id": doc or case["gold_doc_id"],
        "page_number": page if page is not None else case["gold_pages"][0],
        "excerpt": excerpt if excerpt is not None else " ".join(case["gold_terms"]),
    }


def _good_answer(case):
    return " ".join(case["required_points"])


def test_complete_answer_with_gold_citation_passes():
    case = BY_ID["en_irrig_02"]
    result = scoring.score_case(case, _flow(case, answer=_good_answer(case), sources=[_src(case)]))
    assert result["passed"] and result["failure_reasons"] == []
    assert result["citation_exact"] is True


def test_missing_required_point_fails_with_the_point_named():
    case = BY_ID["en_irrig_02"]
    answer = "Irrigate immediately after cutting. Irrigate on 3rd or 4th day after cutting. Irrigate once in 7 - 10 days."
    result = scoring.score_case(case, _flow(case, answer=answer, sources=[_src(case)]))
    assert not result["passed"]
    assert result["required_points"]["missing"] == ["70 - 80 days"]
    assert result["failure_reasons"][0]["code"] == "required_points_missing"


def test_fert_02_partial_dose_fails_and_wrong_dose_fails():
    case = BY_ID["en_fert_02"]
    partial = "Apply 20 kg N and 80 kg P2O5 and 40 kg K2O per ha."
    assert "40 kg of S" in scoring.score_case(case, _flow(case, answer=partial, sources=[_src(case)]))["required_points"]["missing"]
    wrong = "Apply 20 kg N and 80 kg P and 4 kg K, 40 kg of S as gypsum (220 kg/ha)."
    assert "40 kg K" in scoring.score_case(case, _flow(case, answer=wrong, sources=[_src(case)]))["required_points"]["missing"]


def test_gypsum_400_does_not_satisfy_40():
    case = BY_ID["en_fert_01"]
    result = scoring.score_case(case, _flow(case, answer="Apply gypsum at 40 kg/ha on the 40th to 45th day.", sources=[_src(case)]))
    assert result["required_points"]["missing"] == ["400 kg/ha"]


def test_answer_without_citation_never_passes():
    case = BY_ID["en_irrig_01"]
    result = scoring.score_case(case, _flow(case, answer=_good_answer(case), sources=[]))
    assert not result["passed"]
    assert "no_citation" in {r["code"] for r in result["failure_reasons"]}


def test_wrong_page_same_document_is_not_exact():
    case = BY_ID["en_irrig_01"]
    result = scoring.score_case(case, _flow(case, answer=_good_answer(case), sources=[_src(case, page=204)]))
    assert not result["passed"]
    assert result["citations"][0]["classification"] == scoring.DOCUMENT_ONLY


def test_gold_page_without_gold_terms_is_not_exact():
    case = BY_ID["en_irrig_01"]
    result = scoring.score_case(case, _flow(case, answer=_good_answer(case), sources=[_src(case, excerpt="unrelated text")]))
    assert result["citations"][0]["classification"] == scoring.GOLD_PAGE_TERMS_MISSING
    assert not result["passed"]


def test_related_pages_are_recorded_but_not_exact_and_not_merged():
    case = BY_ID["en_fert_01"]
    related = RELATED["fert_01"]
    result = scoring.score_case(case, _flow(case, answer=_good_answer(case), sources=[_src(case, page=208, excerpt="Apply gypsum @ 400 kg / ha at peg formation stage")]), related)
    assert result["citations"][0]["classification"] == scoring.RELATED_DOCUMENTED
    assert not result["passed"]
    soy = BY_ID["en_irrig_03"]
    p185 = scoring.score_case(soy, _flow(soy, answer=_good_answer(soy), sources=[_src(soy, page=185)]), RELATED["irrig_03"])
    assert p185["citations"][0]["classification"] == scoring.RELATED_DOCUMENTED and not p185["passed"]


def test_every_listed_gold_page_is_accepted_for_the_drone_case():
    case = BY_ID["en_drone_01"]
    assert case["gold_pages"] == [18, 19]
    for page in (18, 19):
        result = scoring.score_case(case, _flow(case, answer=_good_answer(case), sources=[_src(case, page=page)]), RELATED["drone_01"])
        assert result["passed"], page
    note = scoring.score_case(case, _flow(case, answer=_good_answer(case), sources=[_src(case, page=19)]), RELATED["drone_01"])["citations"][0]["note"]
    assert note and "duplicate" in note.lower()


def test_over_abstention_and_flow_failures_are_failures():
    case = BY_ID["en_irrig_01"]
    assert scoring.score_case(case, _flow(case, mode="abstained"))["failure_reasons"][0]["code"] == "over_abstention"
    errored = scoring.score_case(case, _flow(case, mode="error", status="error", error="boom"))
    assert not errored["passed"] and errored["failure_reasons"][0]["code"] == "flow_error"
    hi = BY_ID["hi_irrig_01"]
    qfail = scoring.score_case(hi, _flow(hi, mode=None, status="translation_failed", error="down"))
    assert not qfail["passed"] and qfail["failure_reasons"][0]["code"] == "question_translation_failed"
    afail = scoring.score_case(hi, _flow(hi, answer=_good_answer(hi), sources=[_src(hi)], status="translation_failed", error="down"))
    assert not afail["passed"] and "answer_translation_failed" in {r["code"] for r in afail["failure_reasons"]}


def test_unsupported_case_passes_only_with_abstention_and_no_citation():
    case = BY_ID["en_unsup_ood_01"]
    assert scoring.score_case(case, _flow(case, mode="abstained"))["passed"]
    assert not scoring.score_case(case, _flow(case, mode="answered", answer="x", sources=[]))["passed"]
    cited = scoring.score_case(case, _flow(case, mode="abstained", sources=[{"doc_id": "tnau_agriculture", "page_number": 1, "excerpt": "x"}]))
    assert not cited["passed"] and cited["failure_reasons"][0]["code"] == "citation_on_abstention_case"


def test_adjacent_case_flags_maize_interval_as_forbidden_evidence():
    case = BY_ID["en_unsup_adjacent_01"]
    maize = {"doc_id": "tn_crop_sop_2023", "page_number": 18,
             "excerpt": "Minimum interval between application of chemical insecticide and harvest of maize corn should be 30 days."}
    result = scoring.score_case(case, _flow(case, mode="answered", answer="30 days", sources=[maize]), RELATED["unsup_adjacent_01"])
    assert not result["passed"]
    assert result["citations"][0]["classification"] == scoring.FORBIDDEN_EVIDENCE
    assert "answered_unsupported_question" in {r["code"] for r in result["failure_reasons"]}


def test_must_preserve_uses_translated_answer_for_hindi():
    case = BY_ID["hi_fert_01"]
    flow = _flow(case, answer=_good_answer(case), sources=[_src(case)], translated="जिप्सम 400 किग्रा/हे 40 वें 45")
    result = scoring.score_case(case, flow)
    assert result["must_preserve"]["checked_against"] == "translated_answer"
    assert "kg/ha" in result["must_preserve"]["missing"]  # Latin unit absent: reported, not hidden
    assert result["passed"]  # must-preserve is a reported metric, not a pass condition


def test_aggregate_counts_per_language():
    case_en, case_hi = BY_ID["en_irrig_01"], BY_ID["hi_irrig_01"]
    results = [
        scoring.score_case(case_en, _flow(case_en, answer=_good_answer(case_en), sources=[_src(case_en)])),
        scoring.score_case(case_hi, _flow(case_hi, mode="abstained")),
    ]
    metrics = scoring.aggregate_all(results)
    assert metrics["en"]["strict_pass"]["k"] == 1 and metrics["hi"]["strict_pass"]["k"] == 0
    assert metrics["overall"]["strict_pass"] == {"k": 1, "n": 2, "rate": 0.5}
    assert metrics["hi"]["answerable"]["over_abstentions"] == 1


# -------------------------------------------------------------------- runner
class _FakePipeline:
    """Answers each case's English question with its gold evidence (or abstains)."""

    def __init__(self):
        self.by_question = {c["english_reference_question"]: c for c in CASES if c["language"] == "en"}

    def answer(self, question):
        case = self.by_question[question]
        if case["expected_behavior"] == "abstain":
            return AnswerResult(question, "abstained", "abstention", "no evidence")
        source = SourceCitation(case["gold_doc_id"], "t", "o", "", case["gold_pages"][0], " ".join(case["gold_terms"]), 0.9)
        return AnswerResult(question, "answered", "extractive_evidence", " ".join(case["required_points"]), (source,))


class _FakeTranslator:
    def translate(self, text, source, target):
        for case in CASES:
            if case["question"] == text:
                return case["english_reference_question"]
        raise AssertionError("unknown question")

    def translate_batch(self, texts, source, target):
        return ["उत्तर " + t for t in texts]  # Devanagari prefix: passes the script check for hi


def test_runner_processes_all_48_cases_and_never_marks_a_missing_answer_as_pass():
    hi_only = [c for c in CASES if c["language"] != "kn"]
    results = run_evaluation.run_cases(hi_only, _FakePipeline(), _FakeTranslator(), RELATED)
    assert len(results) == 32
    assert all(r["passed"] for r in results if r["language"] == "en")
    assert all(r["retrieval"]["rrf_top5_gold_hit"] is None for r in results)  # no retriever on the stand-in
    kn = [c for c in CASES if c["language"] == "kn"]
    kn_results = run_evaluation.run_cases(kn, _FakePipeline(), _FakeTranslator(), RELATED)
    # The stand-in translator emits Devanagari, so Kannada answers fail the script check.
    answerable = [r for r in kn_results if r["expected_behavior"] == "answer"]
    assert answerable and all(not r["passed"] for r in answerable)
    assert {r["flow_status"] for r in answerable} == {"translation_failed"}


def test_report_renders_and_identifies_the_dataset_hash(tmp_path):
    results = run_evaluation.run_cases([c for c in CASES if c["language"] == "en"], _FakePipeline(), _FakeTranslator(), RELATED)
    payload = {
        "run": {"started_utc": "t", "python": "3", "packages": {}, "languages_run": ["en"], "full_run": False,
                "index_chunk_count": 1, "faiss_index_sha256": None, "code_sha256": {}},
        "dataset": {"path": "evaluation/test_cases.jsonl", "sha256": "abc123", "cases": 48, "per_language": {"en": 16, "hi": 16, "kn": 16}},
        "metrics": scoring.aggregate_all(results),
        "cases": results,
    }
    text = run_evaluation.render_report(payload)
    assert "abc123" in text and "PARTIAL RUN" in text
    json_path, md_path = run_evaluation.write_outputs(payload, tmp_path, "T")
    assert json_path.name.endswith("_partial.json") and md_path.exists()
    with pytest.raises(FileExistsError):
        run_evaluation.write_outputs(payload, tmp_path, "T")


# ------------------------------------------- must-preserve and translation-markup reporting
def test_pass_with_missing_must_preserve_is_visible_not_silently_complete():
    """A strict PASS may lack must-preserve items (they are a reported metric); that must show in the metrics."""
    case = BY_ID["kn_crop_03"]
    translated = "ಜೋಳದ ಶುದ್ಧ ಬೆಳೆಯ ಬೀಜದ ದರ 10 ಕೆ.ಜಿ. ಮತ್ತು ಅಂತರ 15 ಮತ್ತು 45 ಸೆಂ.ಮೀ."
    result = scoring.score_case(case, _flow(case, answer=_good_answer(case), sources=[_src(case)], translated=translated))
    assert result["passed"]
    assert "kg/ha" in result["must_preserve"]["missing"] and "cm" in result["must_preserve"]["missing"]
    result["retrieval"] = None
    metrics = scoring.aggregate([result])
    assert metrics["strict_pass"]["k"] == 1
    assert metrics["strict_pass_with_must_preserve_complete"] == {"k": 0, "n": 1, "rate": 0.0}


def test_complete_must_preserve_is_counted():
    case = BY_ID["en_crop_01"]
    answer = "adopt the seed rate of 20 kg/ha for CO 1 and TNAU Maize Hybrid CO 6 and 25 kg/ha for COBC 1"
    result = scoring.score_case(case, _flow(case, answer=answer, sources=[_src(case)]))
    result["retrieval"] = None
    assert result["passed"] and not result["must_preserve"]["missing"]
    assert scoring.aggregate([result])["strict_pass_with_must_preserve_complete"]["k"] == 1


def test_unresolved_translation_placeholder_markup_is_reported():
    """kn_crop_03 (2026-11-01 run) passed with '10 <ಐ. ಡಿ. 2>' in the Kannada answer."""
    case = BY_ID["kn_crop_03"]
    dirty = "ಜೋಳದ ಬೀಜದ ದರವನ್ನು 10 <ಐ. ಡಿ. 2> ಮತ್ತು ಬೇಳೆಕಾಳು 10 <ಐ. ಡಿ. 1> ಎಂದು ಕಾಪಾಡಿಕೊಳ್ಳಿ."
    result = scoring.score_case(case, _flow(case, answer=_good_answer(case), sources=[_src(case)], translated=dirty))
    assert result["translation_artifacts"] == ["<ಐ. ಡಿ. 2>", "<ಐ. ಡಿ. 1>"]
    assert result["passed"], "reported metric only: the pre-defined pass rules are unchanged"
    result["retrieval"] = None
    markup = scoring.aggregate([result])["translated_answers_with_placeholder_markup"]
    assert markup == {"k": 1, "n": 1, "case_ids": ["kn_crop_03"]}


@pytest.mark.parametrize("clean", ["10 किलोग्राम/हेक्टेयर", "नियम: 1-2 दिन", None, ""])
def test_clean_translations_have_no_markup(clean):
    assert scoring.translation_artifacts(clean) == []


def test_recorded_kannada_answer_from_the_evaluation_run_is_flagged():
    recorded = ROOT / "evaluation" / "results" / "evaluation_results_20261101T154404Z.json"
    if not recorded.is_file():
        pytest.skip("recorded evaluation results not present")
    cases = json.loads(recorded.read_text(encoding="utf-8"))["cases"]
    flagged = [c["id"] for c in cases if scoring.translation_artifacts(c.get("translated_answer"))]
    assert flagged == ["kn_crop_03"]
