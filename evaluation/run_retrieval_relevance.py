"""Run the labeled retrieval relevance cases against cached local assets.

This script reads the existing FAISS index and manifests only. It does not
write/rebuild the index or download models. It creates a new dated report and
refuses to overwrite an existing artifact.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.bootstrap import build_pipeline

ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "evaluation" / "retrieval_relevance_cases.jsonl"
OUTPUT_PATH = ROOT / "artifacts" / "retrieval_relevance_eval_20261030_final5.jsonl"


def _passage_record(passage, case, documents_by_id):
    document = documents_by_id.get(passage.chunk.doc_id)
    evidence_match = bool(
        case["evidence_expected"]
        and passage.chunk.doc_id == case["gold_doc_id"]
        and passage.chunk.page_number == case["gold_page"]
        and all(term.casefold() in passage.chunk.text.casefold() for term in case["gold_terms"])
    )
    return {
        "chunk_id": passage.chunk.chunk_id,
        "document_id": passage.chunk.doc_id,
        "document_title": document.title if document else None,
        "organization": document.organization if document else None,
        "document_topics": list(document.topics) if document else [],
        "page": passage.chunk.page_number,
        "cosine_score": passage.score,
        "bm25_score": passage.lexical_score,
        "rrf_score": passage.fused_score,
        "matched_query_terms": list(passage.matched_terms),
        "query_term_coverage": passage.term_coverage,
        "supports_labeled_evidence": evidence_match,
        "text": passage.chunk.text,
    }


def main() -> None:
    cases = [json.loads(line) for line in CASES_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    pipeline = build_pipeline()
    records = []
    for case in cases:
        embedding = pipeline.embedder.encode_query(case["query"])
        dense = pipeline.retriever.search(embedding, top_k=5)
        lexical = pipeline.retriever.search_lexical(case["query"], top_k=5)
        hybrid = pipeline.retriever.search_hybrid(embedding, case["query"], top_k=5)
        result = pipeline.answer(case["query"])
        pipeline_support = any(
            source.doc_id == case["gold_doc_id"]
            and source.page_number == case["gold_page"]
            and all(term.casefold() in source.excerpt.casefold() for term in case["gold_terms"])
            for source in result.sources
        )
        records.append(
            {
                "case": case,
                "dense_top_passages": [
                    _passage_record(item, case, pipeline.documents_by_id) for item in dense
                ],
                "bm25_top_passages": [
                    _passage_record(item, case, pipeline.documents_by_id) for item in lexical
                ],
                "rrf_top_passages": [
                    _passage_record(item, case, pipeline.documents_by_id) for item in hybrid
                ],
                "pipeline": {
                    "mode": result.mode,
                    "answer_kind": result.answer_kind,
                    "answer": result.answer_text,
                    "warnings": list(result.warnings),
                    "sources": [
                        {
                            "document_id": source.doc_id,
                            "title": source.title,
                            "organization": source.organization,
                            "page": source.page_number,
                            "cosine_score": source.score,
                            "excerpt": source.excerpt,
                        }
                        for source in result.sources
                    ],
                    "supports_labeled_evidence": pipeline_support,
                },
            }
        )

    answerable = [record for record in records if record["case"]["evidence_expected"]]
    unsupported = [record for record in records if not record["case"]["evidence_expected"]]

    def retrieval_hits(method, records_subset):
        return sum(
            any(item["supports_labeled_evidence"] for item in record[method])
            for record in records_subset
        )

    summary = {
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "case_count": len(records),
        "answerable_count": len(answerable),
        "unsupported_and_unrelated_count": len(unsupported),
        "retrieval_top5_gold_hits": {
            "dense": retrieval_hits("dense_top_passages", answerable),
            "bm25": retrieval_hits("bm25_top_passages", answerable),
            "rrf": retrieval_hits("rrf_top_passages", answerable),
        },
        "pipeline_answered_with_gold_evidence": sum(
            record["pipeline"]["mode"] == "answered"
            and record["pipeline"]["supports_labeled_evidence"]
            for record in answerable
        ),
        "pipeline_abstentions_on_answerable_cases": sum(
            record["pipeline"]["mode"] == "abstained" for record in answerable
        ),
        "pipeline_abstentions_on_unsupported_cases": sum(
            record["pipeline"]["mode"] == "abstained" for record in unsupported
        ),
        "pipeline_answers_on_unsupported_cases": sum(
            record["pipeline"]["mode"] == "answered" for record in unsupported
        ),
        "index_was_read_only": True,
        "records": records,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(summary, ensure_ascii=False) + "\n")
    print(
        json.dumps(
            {key: value for key, value in summary.items() if key != "records"},
            ensure_ascii=True,
        )
    )
    print("report=" + str(OUTPUT_PATH))


if __name__ == "__main__":
    main()
