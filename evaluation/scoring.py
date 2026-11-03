"""Scoring rules for the 48-case evaluation (pure functions, no model code).

These functions implement the rules in ``docs/evaluation_methodology.md``.
They are deliberately separate from ``run_evaluation.py`` so the matching and
pass/fail logic can be unit-tested without loading any model.

Normalisation is limited to *formatting*: Unicode compatibility forms, dash
variants, case, whitespace, thousands separators, trailing ``.0``, and spaces
around ``-``, ``/`` and between a number and its unit. It never changes a
digit, a unit letter or a word, and numbers are matched on digit boundaries, so
``400 kg/ha`` never matches ``40 kg/ha`` and ``10 kg/ha`` never matches
``10 g/ha``.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

_DASHES = {ord(ch): "-" for ch in "‐‑‒–—―−"}

# Classification of one cited source against a case's gold evidence.
EXACT = "exact"
GOLD_PAGE_TERMS_MISSING = "gold_page_terms_missing"
DOCUMENT_ONLY = "document_only"
RELATED_DOCUMENTED = "related_documented"
FORBIDDEN_EVIDENCE = "forbidden_evidence"
WRONG_DOCUMENT = "wrong_document"
UNEXPECTED_ON_ABSTENTION = "unexpected_on_abstention"


def normalize(text: str) -> str:
    """Return ``text`` with formatting differences removed (see module doc)."""
    text = unicodedata.normalize("NFKC", text or "").translate(_DASHES)
    # Devanagari / Kannada digits -> ASCII digits.
    text = "".join(
        str(unicodedata.digit(ch)) if ch.isdigit() and not ch.isascii() else ch
        for ch in text
    )
    text = text.casefold()
    text = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", text)  # 1,000 -> 1000
    text = re.sub(r"(?<=\d)\.0+(?!\d)", "", text)  # 10.0 -> 10
    text = re.sub(r"\s*-\s*", "-", text)  # "7 - 10" -> "7-10"
    text = re.sub(r"\s*/\s*", "/", text)  # "kg /ha" -> "kg/ha"
    text = re.sub(r"(?<=\d)\s+(?=[^\W\d_])", "", text)  # "10 kg" -> "10kg"
    return re.sub(r"\s+", " ", text).strip()


def contains(haystack: str, needle: str) -> bool:
    """True if normalised ``needle`` occurs in normalised ``haystack``.

    A needle that starts or ends with a digit must sit on digit boundaries, so
    a number cannot match inside a longer number (``40`` in ``400``).
    """
    n = normalize(needle)
    if not n:
        return False
    pattern = re.escape(n)
    if n[0].isdigit():
        pattern = r"(?<![\d.])" + pattern
    if n[-1].isdigit():
        pattern += r"(?!\d)(?!\.\d)"
    return re.search(pattern, normalize(haystack)) is not None


def split_found(text: str, items: Iterable[str]) -> tuple[list[str], list[str]]:
    found, missing = [], []
    for item in items:
        (found if contains(text, item) else missing).append(item)
    return found, missing


def load_related_evidence(path: Path) -> dict[str, list[dict[str, Any]]]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def classify_citation(
    source: Mapping[str, Any], case: Mapping[str, Any], related: Sequence[Mapping[str, Any]] = ()
) -> dict[str, Any]:
    """Classify one cited source. ``source`` needs doc_id, page_number, excerpt."""
    doc_id, page = source["doc_id"], source["page_number"]
    note = None
    for entry in related:
        if entry["doc_id"] == doc_id and page in entry["pages"]:
            if entry["role"] == "duplicate_text_layer":
                note = entry["note"]
    if case["expected_behavior"] != "answer":
        label = UNEXPECTED_ON_ABSTENTION
        for entry in related:
            if entry["role"] == "forbidden" and entry["doc_id"] == doc_id and page in entry["pages"]:
                label = FORBIDDEN_EVIDENCE
        return {"doc_id": doc_id, "page": page, "classification": label, "note": note}

    gold_pages = case["gold_pages"]
    if doc_id == case["gold_doc_id"] and page in gold_pages:
        terms_ok = all(contains(source["excerpt"], t) for t in case["gold_terms"])
        label = EXACT if terms_ok else GOLD_PAGE_TERMS_MISSING
    elif any(
        e["role"] == "related" and e["doc_id"] == doc_id and page in e["pages"] for e in related
    ):
        label = RELATED_DOCUMENTED
    elif doc_id == case["gold_doc_id"]:
        label = DOCUMENT_ONLY
    else:
        label = WRONG_DOCUMENT
    return {"doc_id": doc_id, "page": page, "classification": label, "note": note}


def score_case(
    case: Mapping[str, Any],
    flow: Mapping[str, Any],
    related: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Score one case. ``flow`` is the flattened multilingual-flow output.

    Keys used: status (english|translated|translation_failed|error),
    english_question, mode (answered|abstained|error|None), answer_text,
    translated_answer, sources [{doc_id, page_number, excerpt}], error.
    A missing answer or citation is always a failure, never a pass.
    """
    expected = case["expected_behavior"]
    status = flow.get("status")
    mode = flow.get("mode")
    sources = list(flow.get("sources") or [])
    reasons: list[dict[str, str]] = []

    def fail(code: str, detail: str) -> None:
        reasons.append({"code": code, "detail": detail})

    citations = [classify_citation(s, case, related) for s in sources]
    result: dict[str, Any] = {
        "id": case["id"],
        "intent_id": case["intent_id"],
        "language": case["language"],
        "phrasing": case["phrasing"],
        "expected_behavior": expected,
        "flow_status": status,
        "actual_mode": mode,
        "english_question": flow.get("english_question"),
        "english_answer": flow.get("answer_text"),
        "translated_answer": flow.get("translated_answer"),
        "citations": citations,
        "flow_error": flow.get("error"),
    }

    # Flow-level failures first: they are never converted into a pass.
    if status == "translation_failed" and mode is None:
        fail("question_translation_failed", str(flow.get("error")))
    elif status == "error" or mode == "error":
        fail("flow_error", str(flow.get("error") or "pipeline returned mode=error"))
    elif status == "translation_failed":
        fail("answer_translation_failed", str(flow.get("error")))

    if expected == "abstain":
        if mode == "answered":
            fail("answered_unsupported_question", "pipeline answered a question that requires abstention")
        if citations:
            fail(
                "citation_on_abstention_case",
                "cited " + ", ".join("{}:p{}({})".format(c["doc_id"], c["page"], c["classification"]) for c in citations),
            )
        result["abstained_correctly"] = mode == "abstained" and not citations
        result["required_points"] = None
        result["must_preserve"] = None
        result["citation_exact"] = None
    else:
        points = list(case["required_points"])
        if mode == "answered":
            found, missing = split_found(flow.get("answer_text") or "", points)
        else:
            found, missing = [], points
        result["required_points"] = {"total": len(points), "found": found, "missing": missing}
        if mode == "abstained":
            fail("over_abstention", "pipeline abstained on an answerable question")
        elif mode == "answered" and missing:
            fail("required_points_missing", "missing: " + "; ".join(missing))

        exact = any(c["classification"] == EXACT for c in citations)
        result["citation_exact"] = exact
        if mode == "answered":
            if not citations:
                fail("no_citation", "answered without any cited source")
            elif not exact:
                fail(
                    "citation_not_gold",
                    "cited " + ", ".join("{}:p{}({})".format(c["doc_id"], c["page"], c["classification"]) for c in citations),
                )

        # Must-preserve is measured on the text the user sees; it is reported as a
        # metric and is not part of the pass rule (see docs/evaluation_methodology.md).
        shown = flow.get("translated_answer") if case["language"] != "en" else flow.get("answer_text")
        if mode == "answered" and shown:
            mp_found, mp_missing = split_found(shown, case["must_preserve"])
        else:
            mp_found, mp_missing = [], list(case["must_preserve"])
        result["must_preserve"] = {
            "checked_against": "translated_answer" if case["language"] != "en" else "english_answer",
            "total": len(case["must_preserve"]),
            "found": mp_found,
            "missing": mp_missing,
        }

    # Reported, not a pass condition (the pass rules were fixed before the run):
    # markup left behind by the translation step in the text the user sees.
    result["translation_artifacts"] = translation_artifacts(flow.get("translated_answer"))
    result["passed"] = not reasons
    result["failure_reasons"] = reasons
    return result


# IndicProcessor wraps numbers and similar spans in "<ID1>"-style placeholders
# before translation. If the model renders one in the target script instead of
# copying it, the placeholder is not restored and markup such as "<ಐ. ಡಿ. 2>"
# remains in the answer shown to the user.
_PLACEHOLDER_MARKUP = re.compile(r"<[^<>\n]{1,30}>")


def translation_artifacts(text: str | None) -> list[str]:
    """Placeholder-style markup left in a translated answer (empty if clean)."""
    return _PLACEHOLDER_MARKUP.findall(text or "")


def _ratio(num: int, den: int) -> dict[str, Any]:
    return {"k": num, "n": den, "rate": (num / den) if den else None}


def aggregate(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Aggregate per-case results (one language, or all)."""
    n = len(results)
    ans = [r for r in results if r["expected_behavior"] == "answer"]
    uns = [r for r in results if r["expected_behavior"] == "abstain"]
    answered = [r for r in ans if r["actual_mode"] == "answered"]

    behaviour_ok = sum(
        1
        for r in results
        if (r["expected_behavior"] == "answer" and r["actual_mode"] == "answered")
        or (r["expected_behavior"] == "abstain" and r["actual_mode"] == "abstained")
    )
    full_cov = sum(1 for r in ans if r["required_points"] and not r["required_points"]["missing"] and r["actual_mode"] == "answered")
    cov_values = [len(r["required_points"]["found"]) / r["required_points"]["total"] for r in answered if r["required_points"]["total"]]
    cit_total = sum(len(r["citations"]) for r in answered)
    cit_exact = sum(1 for r in answered for c in r["citations"] if c["classification"] == EXACT)
    extra = sum(1 for r in answered if any(c["classification"] != EXACT for c in r["citations"]))
    mp_full = sum(1 for r in answered if r["must_preserve"] and not r["must_preserve"]["missing"])
    trans_fail = sum(1 for r in results if r["flow_status"] == "translation_failed")
    # A strict pass does not require must-preserve items; count how many passes also have them all.
    pass_mp_complete = sum(
        1
        for r in ans
        if r["passed"] and r["must_preserve"] is not None and not r["must_preserve"]["missing"]
    )
    translated = [r for r in results if r.get("translated_answer")]
    artifact_cases = [r["id"] for r in translated if r.get("translation_artifacts")]
    rrf_cases = [r for r in ans if r.get("retrieval") and r["retrieval"].get("rrf_top5_gold_hit") is not None]

    return {
        "cases": n,
        "strict_pass": _ratio(sum(1 for r in results if r["passed"]), n),
        "behaviour_accuracy": _ratio(behaviour_ok, n),
        "answerable": {
            "cases": len(ans),
            "answered": _ratio(len(answered), len(ans)),
            "over_abstentions": sum(1 for r in ans if r["actual_mode"] == "abstained"),
            "flow_errors_or_translation_failures": sum(1 for r in ans if r["actual_mode"] not in ("answered", "abstained")),
            "full_required_point_coverage": _ratio(full_cov, len(ans)),
            "mean_required_point_coverage_when_answered": (sum(cov_values) / len(cov_values)) if cov_values else None,
            "citation_exact_case": _ratio(sum(1 for r in answered if r["citation_exact"]), len(answered)),
            "citation_precision_pooled": _ratio(cit_exact, cit_total),
            "extra_citation_cases": _ratio(extra, len(answered)),
            "must_preserve_full_survival": _ratio(mp_full, len(answered)),
            "retrieval_rrf_top5_gold_hit": _ratio(
                sum(1 for r in rrf_cases if r["retrieval"]["rrf_top5_gold_hit"]), len(rrf_cases)
            ),
        },
        "unsupported": {
            "cases": len(uns),
            "abstained_with_no_citations": _ratio(sum(1 for r in uns if r.get("abstained_correctly")), len(uns)),
            "false_answers": sum(1 for r in uns if r["actual_mode"] == "answered"),
        },
        "translation_failures": trans_fail,
        "strict_pass_with_must_preserve_complete": _ratio(pass_mp_complete, len(ans)),
        "translated_answers_with_placeholder_markup": {
            "k": len(artifact_cases),
            "n": len(translated),
            "case_ids": artifact_cases,
        },
    }


def aggregate_all(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_lang: dict[str, list] = defaultdict(list)
    for r in results:
        by_lang[r["language"]].append(r)
    out = {"overall": aggregate(results)}
    for lang in ("en", "hi", "kn"):
        if lang in by_lang:
            out[lang] = aggregate(by_lang[lang])
    return out


def provisional_category(result: Mapping[str, Any]) -> str:
    """Provisional failure category from recorded signals (needs manual confirmation)."""
    codes = {r["code"] for r in result["failure_reasons"]}
    if codes & {"question_translation_failed", "answer_translation_failed"}:
        return "translation"
    if "flow_error" in codes:
        return "flow_error"
    if "answered_unsupported_question" in codes:
        return "relevance_gate (false accept)"
    if "over_abstention" in codes:
        hit = (result.get("retrieval") or {}).get("rrf_top5_gold_hit")
        return "relevance_gate (false reject)" if hit else "retrieval"
    if codes & {"no_citation", "citation_not_gold", "citation_on_abstention_case"}:
        return "citation"
    if "required_points_missing" in codes:
        return "extraction"
    return "unclassified"
