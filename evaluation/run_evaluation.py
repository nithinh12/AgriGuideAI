"""Run the 48-case trilingual evaluation through the real application flow.

    python -m evaluation.run_evaluation      (run from the project root, production .venv)

English questions go straight to the existing RAG pipeline. Hindi and Kannada
questions go through ``src.multilingual_flow.answer_multilingual`` with the real
IndicTrans2 worker, exactly as the Streamlit app does. Nothing is mocked here;
if the index, the embedding model or the translation worker cannot be loaded the
run stops with the exact error instead of producing results.

Outputs (never overwritten) go to ``evaluation/results/``:
  evaluation_results_<UTC>.json   machine-readable per-case results and metrics
  evaluation_report_<UTC>.md      readable report with failure analysis

This is a single evaluation run of ``evaluation/test_cases.jsonl``. It is
separate from the 40-case development set used by ``run_retrieval_relevance.py``.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation import scoring  # noqa: E402
from src.multilingual_flow import answer_multilingual  # noqa: E402
from src.rag_pipeline import PROCESSING_ERROR_MESSAGE, AnswerResult  # noqa: E402

CASES_PATH = ROOT / "evaluation" / "test_cases.jsonl"
RELATED_PATH = ROOT / "evaluation" / "related_evidence.json"
RESULTS_DIR = ROOT / "evaluation" / "results"
EXPECTED_COUNTS = {"en": 16, "hi": 16, "kn": 16}
CODE_FILES = (
    "src/rag_pipeline.py",
    "src/retriever.py",
    "src/embeddings.py",
    "src/multilingual_flow.py",
    "src/translation_client.py",
    "src/translator.py",
    "evaluation/scoring.py",
    "evaluation/run_evaluation.py",
    "evaluation/related_evidence.json",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_cases(path: Path = CASES_PATH) -> list[dict[str, Any]]:
    cases = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = [c["id"] for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate case ids in {}".format(path))
    return cases


def flatten_flow(result) -> dict[str, Any]:
    """Flatten a MultilingualResult into the plain dict the scorer uses."""
    english = result.english_result
    return {
        "status": result.status,
        "english_question": result.english_question,
        "mode": english.mode if english is not None else None,
        "answer_kind": english.answer_kind if english is not None else None,
        "answer_text": english.answer_text if english is not None else None,
        "translated_answer": result.translated_answer,
        "sources": [
            {"doc_id": s.doc_id, "page_number": s.page_number, "excerpt": s.excerpt, "score": s.score}
            for s in (english.sources if english is not None else ())
        ],
        "error": result.error,
        "warnings": list(result.warnings),
    }


def make_ask(pipeline) -> Callable[[str], AnswerResult]:
    """The same safe wrapper the app uses around ``pipeline.answer``."""

    def ask(question: str) -> AnswerResult:
        try:
            return pipeline.answer(question)
        except Exception as exc:  # recorded as a flow error, never a pass
            return AnswerResult(
                question=question.strip(),
                mode="error",
                answer_kind="error",
                answer_text=PROCESSING_ERROR_MESSAGE,
                warnings=("question processing failed ({})".format(type(exc).__name__),),
            )

    return ask


def retrieval_signal(pipeline, case: Mapping[str, Any], english_question: str | None) -> dict[str, Any]:
    """Top-5 RRF gold hit on the English question actually searched."""
    if case["expected_behavior"] != "answer" or not english_question:
        return {"rrf_top5_gold_hit": None}
    try:
        embedding = pipeline.embedder.encode_query(english_question)
        passages = pipeline.retriever.search_hybrid(embedding, english_question, top_k=5)
    except Exception as exc:
        return {"rrf_top5_gold_hit": None, "error": type(exc).__name__}
    ranked = [
        {
            "chunk_id": p.chunk.chunk_id,
            "gold": bool(
                p.chunk.doc_id == case["gold_doc_id"]
                and p.chunk.page_number in case["gold_pages"]
                and all(scoring.contains(p.chunk.text, t) for t in case["gold_terms"])
            ),
        }
        for p in passages
    ]
    return {"rrf_top5_gold_hit": any(r["gold"] for r in ranked), "rrf_top5": ranked}


def run_cases(
    cases: Sequence[Mapping[str, Any]],
    pipeline,
    translator,
    related_by_intent: Mapping[str, Sequence[Mapping[str, Any]]],
    progress: Callable[[str], None] = lambda message: None,
) -> list[dict[str, Any]]:
    ask = make_ask(pipeline)
    results = []
    for index, case in enumerate(cases, 1):
        started = time.perf_counter()
        flow_result = answer_multilingual(ask, translator, case["question"], case["language"])
        flow = flatten_flow(flow_result)
        scored = scoring.score_case(case, flow, related_by_intent.get(case["intent_id"], ()))
        scored["retrieval"] = retrieval_signal(pipeline, case, flow["english_question"])
        scored["answer_kind"] = flow["answer_kind"]
        scored["warnings"] = flow["warnings"]
        scored["seconds"] = round(time.perf_counter() - started, 2)
        scored["provisional_failure_category"] = None if scored["passed"] else scoring.provisional_category(scored)
        results.append(scored)
        progress("[{}/{}] {} {} ({}s)".format(index, len(cases), case["id"], "PASS" if scored["passed"] else "FAIL", scored["seconds"]))
    return results


def package_versions() -> dict[str, str | None]:
    out = {}
    for name in ("numpy", "faiss-cpu", "sentence-transformers", "torch", "transformers", "rank-bm25"):
        try:
            out[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            out[name] = None
    return out


def run_metadata(pipeline, cases_path: Path, languages: Sequence[str], started: datetime) -> dict[str, Any]:
    from src.config import settings

    index_path = Path(settings.faiss_index_path)
    chunks = getattr(getattr(pipeline, "retriever", None), "size", None)
    return {
        "started_utc": started.isoformat(),
        "python": platform.python_version(),
        "packages": package_versions(),
        "languages_run": list(languages),
        "full_run": sorted(languages) == sorted(EXPECTED_COUNTS),
        "index_chunk_count": chunks,
        "faiss_index_sha256": sha256_file(index_path) if index_path.is_file() else None,
        "chunks_jsonl_sha256": sha256_file(index_path.parent / "chunks.jsonl") if (index_path.parent / "chunks.jsonl").is_file() else None,
        "code_sha256": {rel: sha256_file(ROOT / rel) for rel in CODE_FILES if (ROOT / rel).is_file()},
        "seed": settings.seed if hasattr(settings, "seed") else None,
        "single_run": True,
    }


def _pct(ratio: Mapping[str, Any]) -> str:
    if ratio["n"] == 0:
        return "n/a (0 cases)"
    return "{}/{} ({:.1f}%)".format(ratio["k"], ratio["n"], 100 * ratio["rate"])


def render_report(payload: Mapping[str, Any]) -> str:
    meta, ds, metrics, cases = payload["run"], payload["dataset"], payload["metrics"], payload["cases"]
    lines = [
        "# AgriGuide AI evaluation report",
        "",
        "*Single run of `evaluation/test_cases.jsonl` through the real application flow "
        "(English: RAG pipeline directly; Hindi/Kannada: IndicTrans2 worker, RAG pipeline, "
        "answer translation). Every number below comes from this run's `evaluation_results` JSON. "
        "This is **not** the 40-case development set (`retrieval_relevance_cases.jsonl`).*",
        "",
        "## Run identity",
        "",
        "| Item | Value |",
        "|---|---|",
        "| Dataset | `{}` |".format(ds["path"]),
        "| **Dataset SHA-256** | `{}` |".format(ds["sha256"]),
        "| Cases | {} (en {}, hi {}, kn {}) |".format(ds["cases"], ds["per_language"].get("en", 0), ds["per_language"].get("hi", 0), ds["per_language"].get("kn", 0)),
        "| Run started (UTC) | {} |".format(meta["started_utc"]),
        "| Languages run | {}{} |".format(", ".join(meta["languages_run"]), "" if meta["full_run"] else " **(PARTIAL RUN: not the full 48 cases)**"),
        "| Index chunks | {} |".format(meta["index_chunk_count"]),
        "| FAISS index SHA-256 | `{}` |".format(meta["faiss_index_sha256"]),
        "| Python | {} |".format(meta["python"]),
        "| Packages | {} |".format(", ".join("{} {}".format(k, v) for k, v in meta["packages"].items() if v)),
        "",
        "Code hashes (SHA-256): " + "; ".join("`{}` {}".format(k, v[:12]) for k, v in meta["code_sha256"].items()),
        "",
        "## Pass rules (defined before the run)",
        "",
        "- **Answerable case passes** when the pipeline answered, every `required_points` item is found in the English answer, "
        "at least one cited source is exact (gold document, page in `gold_pages`, all `gold_terms` in the excerpt), "
        "and for Hindi/Kannada the question and answer translations did not fail.",
        "- **Unsupported case passes** when the pipeline abstained and returned no citations.",
        "- Must-preserve survival, citation precision, extra citations and retrieval signals are **reported metrics, not pass conditions**.",
        "- Matching normalises formatting only (case, whitespace, dash variants, number formatting, number-unit spacing). Numbers match on digit boundaries, so `400 kg/ha` does not match `40 kg/ha`.",
        "- Not measured here: manual question-meaning, answer adequacy/terminology/fluency, and any native-speaker validation.",
        "",
        "## Metrics",
        "",
    ]
    langs = [l for l in ("overall", "en", "hi", "kn") if l in metrics]
    header = "| Metric | " + " | ".join(langs) + " |"
    lines += [header, "|---|" + "---|" * len(langs)]

    def row(label: str, getter) -> None:
        lines.append("| {} | {} |".format(label, " | ".join(getter(metrics[l]) for l in langs)))

    row("Cases", lambda m: str(m["cases"]))
    row("**Strict pass**", lambda m: _pct(m["strict_pass"]))
    row("Behaviour accuracy (answered/abstained as expected)", lambda m: _pct(m["behaviour_accuracy"]))
    row("Answerable: answered", lambda m: _pct(m["answerable"]["answered"]))
    row("Answerable: over-abstentions", lambda m: str(m["answerable"]["over_abstentions"]))
    row("Answerable: full required-point coverage", lambda m: _pct(m["answerable"]["full_required_point_coverage"]))
    row("Answerable: mean coverage when answered", lambda m: "n/a" if m["answerable"]["mean_required_point_coverage_when_answered"] is None else "{:.1f}%".format(100 * m["answerable"]["mean_required_point_coverage_when_answered"]))
    row("Answered: citation exact (case)", lambda m: _pct(m["answerable"]["citation_exact_case"]))
    row("Answered: citation precision (pooled)", lambda m: _pct(m["answerable"]["citation_precision_pooled"]))
    row("Answered: cases with a non-exact citation", lambda m: _pct(m["answerable"]["extra_citation_cases"]))
    row("Answered: must-preserve fully present", lambda m: _pct(m["answerable"]["must_preserve_full_survival"]))
    row("Answerable: RRF top-5 gold hit (English question searched)", lambda m: _pct(m["answerable"]["retrieval_rrf_top5_gold_hit"]))
    row("Unsupported: abstained with no citations", lambda m: _pct(m["unsupported"]["abstained_with_no_citations"]))
    row("Unsupported: false answers", lambda m: str(m["unsupported"]["false_answers"]))
    row("Translation failures", lambda m: str(m["translation_failures"]))
    row("Answerable: strict pass AND all must-preserve items present", lambda m: _pct(m["strict_pass_with_must_preserve_complete"]))
    row(
        "Translated answers with placeholder markup (e.g. `<ID 2>`)",
        lambda m: "{}/{}".format(m["translated_answers_with_placeholder_markup"]["k"], m["translated_answers_with_placeholder_markup"]["n"]),
    )

    failed = [c for c in cases if not c["passed"]]
    lines += ["", "## Failure analysis", ""]
    if not failed:
        lines.append("No case failed its pass rule in this run.")
    else:
        lines += [
            "{} of {} cases failed. Categories are **provisional** (derived from recorded signals) and need manual confirmation.".format(len(failed), len(cases)),
            "",
            "| Case | Language | Expected | Actual | Provisional category | Reasons |",
            "|---|---|---|---|---|---|",
        ]
        for c in failed:
            reasons = "; ".join("{}: {}".format(r["code"], r["detail"]) for r in c["failure_reasons"]).replace("|", "/")
            lines.append("| `{}` | {} | {} | {} | {} | {} |".format(c["id"], c["language"], c["expected_behavior"], c["actual_mode"], c["provisional_failure_category"], reasons))
    mp_misses = [c for c in cases if c.get("must_preserve") and c["must_preserve"]["missing"] and c["actual_mode"] == "answered"]
    lines += ["", "## Must-preserve misses (answered cases, reported metric)", ""]
    if not mp_misses:
        lines.append("None.")
    else:
        lines += ["| Case | Checked against | Missing |", "|---|---|---|"]
        for c in mp_misses:
            lines.append("| `{}` | {} | {} |".format(c["id"], c["must_preserve"]["checked_against"], ", ".join("`{}`".format(m) for m in c["must_preserve"]["missing"])))
    noted = [(c["id"], ci["note"]) for c in cases for ci in c["citations"] if ci.get("note")]
    if noted:
        lines += ["", "## Citation notes", ""] + ["- `{}`: {}".format(i, n) for i, n in sorted(set(noted))]
    lines += [
        "",
        "## Per-case results",
        "",
        "`Must-preserve` is not a pass condition; a PASS row can still show missing items. "
        "Automatic matching cannot recognise a unit the translator localised "
        "(e.g. `cm` rendered as the Hindi word for centimetre), so Hindi/Kannada unit misses can be translation, not loss of the fact.",
        "",
        "| Case | Result | Mode | Required points | Must-preserve | Citation | Seconds |",
        "|---|---|---|---|---|---|---|",
    ]
    for c in cases:
        rp = c["required_points"]
        rp_text = "n/a" if rp is None else "{}/{}".format(len(rp["found"]), rp["total"])
        mp = c.get("must_preserve")
        mp_text = "n/a" if not mp or not mp["total"] else "{}/{}".format(len(mp["found"]), mp["total"])
        if c.get("translation_artifacts"):
            mp_text += " + placeholder markup in translation"
        cit = ", ".join("p{} {}".format(ci["page"], ci["classification"]) for ci in c["citations"]) or "none"
        lines.append("| `{}` | {} | {} | {} | {} | {} | {} |".format(c["id"], "PASS" if c["passed"] else "FAIL", c["actual_mode"], rp_text, mp_text, cit, c["seconds"]))
    lines.append("")
    return "\n".join(lines)


def write_outputs(payload: Mapping[str, Any], results_dir: Path, stamp: str) -> tuple[Path, Path]:
    results_dir.mkdir(parents=True, exist_ok=True)
    suffix = "" if payload["run"]["full_run"] else "_partial"
    json_path = results_dir / "evaluation_results_{}{}.json".format(stamp, suffix)
    md_path = results_dir / "evaluation_report_{}{}.md".format(stamp, suffix)
    for path, text in ((json_path, json.dumps(payload, ensure_ascii=False, indent=2)), (md_path, render_report(payload))):
        with path.open("x", encoding="utf-8") as handle:  # never overwrite an earlier run
            handle.write(text)
    return json_path, md_path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--languages", nargs="+", default=["en", "hi", "kn"], choices=["en", "hi", "kn"])
    parser.add_argument("--expect-sha256", help="Abort unless the dataset has this SHA-256")
    args = parser.parse_args(argv)

    dataset_sha = sha256_file(CASES_PATH)
    if args.expect_sha256 and args.expect_sha256 != dataset_sha:
        print("Dataset SHA-256 mismatch: expected {} got {}".format(args.expect_sha256, dataset_sha), file=sys.stderr)
        return 2
    all_cases = load_cases()
    counts = {lang: sum(1 for c in all_cases if c["language"] == lang) for lang in EXPECTED_COUNTS}
    if len(all_cases) != 48 or counts != EXPECTED_COUNTS:
        print("Unexpected dataset shape: {} cases {}".format(len(all_cases), counts), file=sys.stderr)
        return 2
    cases = [c for c in all_cases if c["language"] in args.languages]

    from app.bootstrap import build_pipeline
    from src.translation_client import SubprocessTranslator

    started = datetime.now(timezone.utc)
    pipeline = build_pipeline()
    translator = SubprocessTranslator()
    try:
        results = run_cases(cases, pipeline, translator, scoring.load_related_evidence(RELATED_PATH), progress=print)
    finally:
        translator.close()

    payload = {
        "run": run_metadata(pipeline, CASES_PATH, args.languages, started),
        "dataset": {
            "path": "evaluation/test_cases.jsonl",
            "sha256": dataset_sha,
            "cases": len(all_cases),
            "per_language": counts,
            "cases_run": len(cases),
        },
        "metrics": scoring.aggregate_all(results),
        "failed_case_ids": [r["id"] for r in results if not r["passed"]],
        "cases": results,
    }
    json_path, md_path = write_outputs(payload, RESULTS_DIR, started.strftime("%Y%m%dT%H%M%SZ"))
    overall = payload["metrics"]["overall"]["strict_pass"]
    print("Strict pass {}/{}".format(overall["k"], overall["n"]))
    print("Wrote", json_path)
    print("Wrote", md_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
