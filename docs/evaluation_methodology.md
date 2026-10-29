# Evaluation Methodology

*Defined 2026-10-29, **before** any evaluation was run (spec requirement:
define the method and scoring criteria first). No numbers in this file are
results; results go to `evaluation/results/` and `evaluation/failure_analysis.md`
after actual execution.*

## Test set: 30–50 cases (`evaluation/test_cases.jsonl`)

Each case is one JSON line:

```json
{
  "id": "en_fert_001",
  "language": "en",
  "category": "fertilizer",
  "question": "...",
  "expected_behavior": "answer | abstain | clarify",
  "reference_answer": "short verified answer or null",
  "relevant_doc_ids": ["uas_wheat_fert_2024"],
  "evidence_quotes": ["verbatim quote that supports the reference"],
  "must_preserve": ["120 kg/ha", "urea"],
  "notes": "requires soil test context; ideal answer asks for soil type"
}
```

Coverage matrix (target ≈ 40 cases):

| Dimension | Distribution |
|---|---|
| Language | ~13 en, ~13 hi, ~14 kn |
| Topic | crop management, irrigation, fertilizer (≈ equal), + 3–4 cross-topic |
| Expected behavior | majority `answer`; ≥ 6 `abstain` (no/weak evidence in KB); ≥ 4 `clarify` (ambiguous: missing crop/soil/stage/location) |
| Difficulty | easy factual lookup, medium multi-fact, hard comparison/scheduling |

Hindi/Kannada questions are written/validated natively (not just machine
translated) where possible; where machine-translated, flagged in `notes` and
excluded from "language quality" scoring of the *test set itself*.

## Metrics (rubrics fixed in advance)

### 1. Retrieval relevance — hit rate @ k
- For cases with `relevant_doc_ids`: **Hit@5** = fraction where at least one
  chunk from an annotated doc is in the top-5 (primary), also report Hit@3.
- Additionally Mean Reciprocal Rank (MRR@5) over annotated chunks.
- Minimum-score gate behavior on `abstain` cases: false-positive retrieval
  (retrieved something judged irrelevant) is counted as a failure of the gate.

### 2. Groundedness (claim support)
- Answers are decomposed into atomic claims by the evaluator (manual for the
  academic scale of this project; scripted to enforce format).
- Each claim scored 1 (supported by a cited excerpt), 0.5 (partially /
  inferred), 0 (unsupported).
- **Groundedness score** = mean claim score. Target ≥ 0.8; any 0-score claim
  on a fertilizer/pesticide dose is a **critical failure**.

### 3. Factual correctness
- Against `reference_answer` + `evidence_quotes` (independently verified when
  the case was authored): score whole answer 1 / 0.5 / 0.
- Numbers/units: any contradiction of a reference quantity = score 0
  regardless of the rest.

### 4. Domain QA quality (composite per case)
`0.3·groundedness + 0.3·correctness + 0.2·retrieval + 0.2·behavior_match`
where `behavior_match` = 1 when the system's behavior (answer/abstain/clarify)
equals `expected_behavior`.

### 5. Translation fidelity
- **Automatic**: en→hi→en and en→kn→en round-trip on 10 test sentences with
  numbers/units; check all entries in `must_preserve` survive verbatim
  (digits, units, chemical names like "DAP"/"urea").
- **Manual rubric** (per language, 1–5): adequacy, fluency, terminology
  accuracy — scored on the ~13 answers per language by the author; rubric
  anchors defined before scoring (5 = no meaning loss; 3 = understandable
  with minor errors; 1 = unusable).

### 6. Abstention correctness
- On `abstain`-expected cases: correct = explicit insufficient-evidence
  message + expert-referral, no fabricated specifics. Fabricated dose/citation
  = critical failure.

## Failure taxonomy (`evaluation/failure_analysis.md`)

Categories to tag on every failed case: `retrieval_miss`, `retrieval_gate_miss`,
`llm_hallucination`, `llm_offtopic`, `llm_refused_correctly_but_scored_low`,
`translation_error`, `terminology_loss`, `ui_layer_error`, `prompt_format`,
`model_limitation` (e.g. AgriParam Hindi-only), `kb_gap` (knowledge base
lacks the fact — not the model's fault).

## Reproducibility

- Fixed `SEED=42`; deterministic FAISS IndexFlat (exact search).
- Model versions pinned in `requirements.txt`; checkpoint revisions recorded
  in run logs.
- `evaluation/run_evaluation.py` writes machine-readable results (JSON) plus
  a summary table; raw model outputs retained per case.
- No metric may be reported unless produced by an executed run.
