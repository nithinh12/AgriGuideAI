# Evaluation Methodology

*First defined 2026-10-29. Revised 2026-10-31 to match the implemented system,
**before any formal trilingual evaluation was run** (spec requirement: define
the method and scoring criteria first). No number in this file is a result.
Results are written to `evaluation/results/` after actual execution (local run
outputs, not tracked in the repository; the final numbers are summarised in
`README.md` and the failure analysis in `docs/failure_remediation_20261101.md`),
and no metric may be reported unless an executed run produced it.*

## What is being evaluated

AgriGuide AI as implemented (see `README.md`, `docs/architecture.md`):

- English questions go straight to the English RAG pipeline. Hindi and
  Kannada questions are translated to English by IndicTrans2, answered by the
  same pipeline, and the answer text is translated back.
- Retrieval is hybrid (FAISS dense + BM25, fused by reciprocal rank) followed
  by an evidence-relevance gate. Answers are **extractive**: verbatim
  sentences from retrieved passages, with citations to the original English
  source passages. The pipeline abstains, with no citations, when evidence is
  insufficient.
- **There is no LLM generation.** BharatGen AgriParam was downloaded and
  evaluated separately (2026-11-01) but is **not integrated**, because it
  failed the final accuracy criteria; the professor's mandatory AgriParam
  requirement is therefore **unmet** (evidence:
  `artifacts/agriparam_cpu_smoke_test.md`). This methodology therefore does **not**
  measure generation quality, hallucination, fluency of generated text or
  prompt behaviour, and the project report must not claim any of these.
- There is no clarification behaviour and no separate safety layer. The
  earlier `clarify` expected-behaviour has been removed.

The evaluation separates five questions: did retrieval find the evidence,
did the system answer or abstain correctly, was the answer adequate, was the
citation correct, and (Hindi/Kannada) did translation preserve the meaning.

## Relation to the existing 40-case set

`evaluation/retrieval_relevance_cases.jsonl` holds 40 English cases (27
answerable with `gold_doc_id`, `gold_page`, `gold_terms`; 13 with
`evidence_expected: false`). It was used **while developing and tuning** the
retriever, gate and sentence selection, so it is a **development set**. Scores
on it are not an unbiased estimate of performance and must be reported as
development-set results if they are reported at all. The final evaluation uses
a **new, frozen** trilingual set (below) written without tuning against it.
The development set's schema (`gold_doc_id`, `gold_page`, `gold_terms`) is
reused.

## Test set: 30–50 cases (`evaluation/test_cases.jsonl`)

One JSON line per case:

```json
{
  "id": "hi_irrig_003",
  "intent_id": "irrig_003",
  "language": "hi",
  "category": "irrigation",
  "question": "<question in the case language>",
  "english_reference_question": "<human-written English equivalent>",
  "expected_behavior": "answer | abstain",
  "unsupported_type": null,
  "gold_doc_id": "tnau_agriculture",
  "gold_pages": [136],
  "gold_terms": ["minimum of 5 irrigations"],
  "required_points": ["5 irrigations", "crown root initiation", "flowering"],
  "must_preserve": ["wheat", "5", "15-20"],
  "authoring": "native | author-written | machine-translated",
  "difficulty": "easy | medium | hard",
  "notes": ""
}
```

- `gold_pages` is a list because the source drone SOP PDF has duplicated page
  text layers (a chunk labeled with one page can contain text printed on its
  neighbour). Allowed pages are decided when the case is written, by reading
  the rendered PDF page, not the extracted text.
- `required_points` are short strings that the English answer must contain to
  be complete. They are matched with the formatting-only normalisation in
  "Implemented scoring" below (case, whitespace, dash variants, number
  formatting and number-unit spacing; never numbers, units, crops or words). `must_preserve` are the
  crop names, quantities, ranges and units that a faithful translation must
  keep.
- `intent_id` links the English, Hindi and Kannada versions of the same
  information need (a **paired** design).
- Every case is written, its gold evidence located in the PDF, and the file
  **frozen and hashed before any run**.

### Recommended distribution (target 48 cases)

| Dimension | Distribution |
|---|---|
| Core design | 14 intents × 3 languages = **42 cases** (14 per language) |
| Answerable intents | 10 per language (30 cases) |
| Unsupported intents | 4 per language (12 cases): 1 out-of-domain, 1 agricultural but absent from the knowledge base, 1 asking for current/local information, 1 adjacent-but-unsupported (shares crop and topic words with real evidence) |
| Phrasing-sensitivity cases | +2 per language (6 cases): alternative phrasings of two answerable intents, because translation variance changed retrieval in development |
| **Total** | **48** (16 per language), within the 30–50 requirement |
| Answerable topics (10 intents) | irrigation 3, fertilizer/nutrients 2, crop management (seed treatment, nursery, sowing) 3, horticulture 1, drone pesticide safety 1 |
| Source documents | Cover all three: TNAU Agriculture, TNAU Horticulture, drone SOP |
| Difficulty (answerable) | ~5 easy single-fact lookups, ~3 multi-fact or list answers, ~2 numeric or table-based |

If time is short, the minimum acceptable set is 30 cases: 10 intents × 3
languages (7 answerable, 3 unsupported per language). Fewer than ten cases per
language is too few to report per-language results.

Hindi and Kannada questions should be written, or reviewed, by a fluent
speaker. Any question that is machine-translated is flagged in `authoring`
and the report states how many. The question texts are not translations the
system produced; they are independent inputs.

## Metrics

Metrics are grouped in layers so that retrieval performance is reported
separately from final answer quality. Every metric is a count out of a stated
denominator (k/n) and is reported **per language** and overall.

### A. Retrieval (does the evidence get found?)

Computed on the English question the pipeline actually searched: for English
cases the written question, for Hindi/Kannada the **English translation the
translator produced**. This makes retrieval scores for hi/kn include
translation effects (see the failure taxonomy).

- **Hit@5 (dense, BM25, RRF)**: gold passage in the top 5 of each ranking.
  A passage is gold when its `doc_id` matches, its page is in `gold_pages`,
  and its text contains every `gold_terms` string. RRF Hit@5 is primary.
- **MRR@5 (RRF)**: reciprocal rank of the first gold passage.
- **Candidate recall**: gold passage anywhere in the wide candidate list
  (top 100) given to the gate.
- **Gate pass rate**: of answerable cases whose gold passage was in the
  candidate list, the share where it survived the evidence-relevance gate.
- **Gate false-accept**: on unsupported cases, the share where any passage
  survived the gate (reported separately from final abstention, because the
  later extraction step can still abstain).

Dense-only, BM25-only and RRF are reported side by side; they describe
retrieval, not answer quality.

### B. Behaviour: answer vs abstain (on the final pipeline output)

Judged on the English pipeline decision (`mode`), which is the same for all
three languages of an intent.

Confusion matrix of expected × actual behaviour, with:
- **Abstention accuracy (unsupported)**: abstained **and** returned no
  citations. Primary safety metric.
- **False-answer rate (unsupported)**: any answer returned. Each is reviewed;
  one that presents a quantity or recommendation is a **critical failure**.
- **Over-abstention rate (answerable)**: abstained although gold evidence
  exists in the knowledge base.
- **Answer rate when answerable** and **precision of answering** (of all
  answered cases, the share expected to be answered).

An unsupported case is **correct only if** the output is an abstention with no
citations. Answering with a partially related passage is **not** partial
credit; it is a false answer. In Hindi/Kannada the abstention message is
machine-translated; the abstention counts as correct on the pipeline decision,
and the translated message is scored under translation (D).

### C. Answer and citation quality (answerable cases that were answered)

Answers are verbatim extracts, so "supported by the cited text" is true by
construction and is **not** a quality result. It is checked automatically as a
sanity test (below) and the quality metrics target what extraction can get
wrong.

1. **Sanity check (automatic)**: every sentence of the English answer occurs
   in a cited excerpt, except the documented buffer-zone restatement. Any
   failure is a defect, not a score.
2. **Required-point coverage (automatic)**: `required_points` found in the
   English answer ÷ points required, per case; also the share of cases with
   full coverage.
3. **Relevance (manual, 0–2)**: 2 = the answer addresses the question; 1 = it
   is on topic but misses the point or is mostly unrelated surrounding text;
   0 = it answers a different question or a different crop.
4. **Wrong-evidence answer (manual, critical)**: the answer is built from
   evidence for a different crop, topic or document and could be mistaken as
   the answer. Counted separately and reported in full.
5. **Citation correctness (automatic + manual check)**:
   - *Citation exact*: at least one cited source is gold (document, page in
     `gold_pages`, `gold_terms` present in the excerpt).
   - *Citation precision*: gold-supporting citations ÷ all citations, pooled
     over cases.
   - *Extra-citation rate*: cases that cite at least one non-supporting
     source.
   - A citation to the right document with a page outside `gold_pages` is
     recorded as *document-only*; it is not counted as exact.
   - Abstentions with any citation are counted as defects.

There is **no weighted composite score**. The earlier composite
(0.3·groundedness + 0.3·correctness + 0.2·retrieval + 0.2·behaviour) is removed
because groundedness is constant for extractive answers and the weights had
no empirical basis. Instead the report gives a strict per-case success
outcome (below) next to the layered metrics.

### D. Multilingual performance and translation quality (hi and kn)

**Paired comparison.** Because each intent exists in en, hi and kn, report for
each language: Hit@5, behaviour accuracy, citation exact, and full
required-point coverage, and the **difference from English** on the same
intents. Cases where English succeeds and hi/kn fails are the translation
loss.

**Question translation (hi/kn → English)**
- *Crop-name preservation (automatic)*: the crop in the reference question is
  present in the produced English question.
- *Key-term recall (automatic)*: share of the reference question's content
  terms (stop words removed, same normalisation as the retriever) present in
  the produced English question. Descriptive only; wording differences that
  keep the meaning lower it, so it is not used for pass/fail.
- *Meaning preserved (manual, Yes / Partly / No)* against the reference
  question, including crop, quantity and topic. Primary measure.

**Answer translation (English → hi/kn)**, on answered cases
- *Script ratio (automatic)*: share of letters in the target script (the app
  rejects below 0.3; the evaluation reports the actual value).
- *Numeric preservation (automatic)*: numbers and ranges in the English
  answer that appear in the translated answer (digits normalised). Reports
  the share preserved.
- *Must-preserve survival (automatic)*: `must_preserve` items still present
  (numbers, units, Latin-script names left unchanged).
- *Manual rubric, 1–5 each* (defined before scoring):
  - **Adequacy**: 5 = no meaning loss against the English answer; 4 = minor
    loss; 3 = understandable with errors; 2 = key meaning wrong or missing;
    1 = unusable.
  - **Terminology**: 5 = crop names and agricultural terms correct or
    standard; 3 = some transliterated or wrong terms, still understandable;
    1 = terms wrong enough to mislead.
  - **Fluency**: 5 = natural; 3 = readable with awkward grammar; 1 = broken.
- *Translation failure rate*: cases where the flow reported a failed question
  or answer translation, or an error. A reported failure is **not** counted as
  a translation-quality score; it is counted as a failure.
- Round-trip back-translation, BLEU/chrF and similar overlap metrics are
  **not used**: with one reference and short extractive answers they are not
  reliable.

**Understandability** is the manual Adequacy score plus the failure rate. The
author's ability to read each language limits the manual scores; see
limitations.

### E. Per-case success and summary

| Case type | Success requires |
|---|---|
| Answerable, English | answered, Citation exact, full required-point coverage, Relevance 2 |
| Answerable, hi/kn | all of the above **plus** Question meaning ≠ No, translated-answer Adequacy ≥ 3, no translation failure |
| Unsupported (any language) | abstained with no citations |

Report overall and per-language: strict success k/n, and each layer metric.
Latency (cold start and warm, seconds per case) is reported descriptively and
never mixed into quality.

## Failure taxonomy

(A separate `evaluation/failure_analysis.md` was planned but not created; the
categories below are applied in each run's evaluation report, and the
remediation analysis is in `docs/failure_remediation_20261101.md`.)

Every non-successful case gets **one primary** category, assigned by the first
failing stage in this order, and optionally one secondary:

| Category | Definition (how it is detected) |
|---|---|
| `translation` | Question translated with lost or changed meaning, wrong crop or quantity (Meaning = No/Partly and the change caused the failure); answer translation failed, hit the 256-token limit, lost numbers or terms, or Adequacy < 3 |
| `retrieval` | Gold passage not in the top-100 candidates (dense, BM25 and RRF all miss) |
| `relevance_gate` | **False reject**: gold passage was a candidate but the gate removed it. **False accept**: on an unsupported case, or when an unrelated passage was accepted and produced the answer |
| `extraction` | The gold passage reached the generator but the selected sentences are wrong, incomplete (for example a heading without its list), noisy (appended unrelated sentences) or distorted by flattened table text |
| `citation` | Wrong document or page, extra non-supporting citations, a duplicate-page artifact, or a citation on an abstention |
| `kb_gap` | The knowledge base does not contain the fact; not a system fault. Applies when an answerable-labeled case turns out to lack evidence |
| `source_defect` | The source PDF text is defective (duplicated page text, garbled table) so extraction is correct but the text is unusable |
| `flow_error` | The application raised or reported a non-translation error |

Because detection needs per-stage data, the evaluation runner must record,
for each case: the original and translated question, the dense, BM25 and RRF
top-5 and wide-candidate gold rank, the gate decision and reason, the
selected sentences and their source chunks, the citations, the translated
answer, the flow status, and timings. (`evaluation/run_retrieval_relevance.py`
records part of this for the 40-case development set. The final runner,
`evaluation/run_evaluation.py`, was written on 2026-11-01 and records a subset:
see "Implemented scoring" for exactly what it does and does not record.)

## Implemented scoring (what the code actually does)

*Added 2026-11-01 from `evaluation/scoring.py` and `evaluation/run_evaluation.py`.
Where this section and the earlier design text differ, this section describes
the code. It is covered by `tests/test_evaluation_scoring.py`.*

**Datasets.** The runner reads the **48-case** `evaluation/test_cases.jsonl`
(16 per language). It is separate from the **40-case English development set**
`evaluation/retrieval_relevance_cases.jsonl`, which was used while tuning the
retriever and gate and is read only by `evaluation/run_retrieval_relevance.py`
(a different schema and a different matching rule: one `gold_page`,
case-folded substring match of `gold_terms`).

**Pipeline.** English: the existing `RAGPipeline.answer`. Hindi/Kannada:
`src.multilingual_flow.answer_multilingual` with the real `SubprocessTranslator`
and the same pipeline. Nothing is mocked in a real run.

**Matching normalisation (formatting only).** Both sides are normalised with
Unicode NFKC, dash variants to `-`, Devanagari/Kannada digits to ASCII, case
folding, thousands separators removed, a trailing `.0` removed, whitespace
collapsed, spaces removed around `-` and `/`, and the space between a number
and its unit removed (`10 kg/ha` equals `10kg/ha`; `7 - 10` equals `7-10`).
A needle that starts or ends with a digit must sit on digit boundaries, so
`400 kg/ha` does not match `40 kg/ha`, `10 kg/ha` does not match `10 g/ha`,
and `5 kg` does not match inside `2.5 kg`. Word differences are never
normalised (a crop, a timing or a dosage that differs stays a mismatch).
`heavy rain` still matches `heavy rains` because matching is by substring on
the word side.

**Per-case pass rule (automatic).**

- *Answerable (en/hi/kn):* the pipeline answered; every `required_points` item
  is found in the **English** answer; at least one cited source is **exact**
  (document equals `gold_doc_id`, page is in `gold_pages`, every `gold_terms`
  item is in the cited excerpt); for Hindi/Kannada the question translation and
  the answer translation did not fail. An answer without a citation, an
  abstention, or a flow error is a failure and is never counted as a pass.
- *Unsupported (all languages):* the pipeline abstained and returned **no**
  citations. For Hindi/Kannada the pass is decided on the English pipeline
  decision; a failed question translation is a failure.
- *Reported, not pass conditions:* must-preserve survival (measured against the
  English answer for English and the **translated** answer for Hindi/Kannada),
  pooled citation precision, cases with a non-exact citation, and the
  top-5 RRF gold-hit signal on the English question that was searched.
  Latin-script units such as `kg/ha` may legitimately be localised by the
  translator; this is the open AUD-11 question, so must-preserve is reported
  and not used to fail a case.

**Citation classes.** `exact`; `gold_page_terms_missing`; `document_only` (right
document, page not in `gold_pages`); `related_documented` (a page listed in
`evaluation/related_evidence.json` as related but not interchangeable);
`wrong_document`; `forbidden_evidence`; `unexpected_on_abstention`. Only `exact`
counts as correct. `evaluation/related_evidence.json` records, and does not
merge, the documented source nuances below.

**Not implemented in the runner (so nothing is reported for it):** the
sentence-level extractive sanity check, dense-only and BM25-only Hit@5, MRR,
top-100 candidate recall, gate pass rate and gate false-accept, manual
relevance, manual meaning and translation-adequacy scores, and the
Hindi/Kannada question-translation crop-name and key-term metrics. The
provisional failure category in the report is derived from the recorded
signals and must be confirmed manually.

### Recorded evaluation decisions (2026-11-01)

- `en_crop_01` and `en_crop_02` questions are approved exactly as written.
  `en_fert_03` does not exist and must not be created.
- `irrig_02` (en/hi/kn): all four steps are required: immediately after cutting,
  3rd or 4th day, once in 7 - 10 days, stop irrigation 70 - 80 days after
  ratooning. `required_points` was extended accordingly (dataset SHA-256 changed
  from `acd6df127c14...` to `5e7491daac62...`; only `required_points` of the six
  `irrig_02` and `fert_02` records changed).
- `fert_02` (en/hi/kn): the complete basal recommendation is required: 20 kg N,
  80 kg P2O5, 40 kg K2O and 40 kg S as gypsum (220 kg/ha). `required_points`
  was extended accordingly.
- `fert_01`: page 203 (`tnau_agriculture::p203::c201`) stays the primary
  evidence. Pages 197 and 208 also give 400 kg/ha for groundnut gypsum but with
  different timing wording ("45th day after sowing"; "at peg formation stage
  and at earthing"). This is an **unresolved source-reference nuance**; the
  statements are not merged and a citation to those pages is recorded as
  `related_documented`, not exact.
- `irrig_03`: page 186 stays the primary evidence. Page 185 says soybean "can
  withstand short periods of waterlogging", which is related but not
  interchangeable with the page 186 statement about water stagnation.
- `drone_01`: the duplicated SOP text was inspected on rendered pages. PDF page
  18 (printed page 7) carries the "do not spray if heavy rains are forecast in
  next 1-2 days" guideline. PDF page 19 (printed page 8) shows only the
  Ready-Reckoner table; its extracted text layer repeats page 18, so the index
  holds an identical chunk for page 19. `gold_pages` stays `[18, 19]`: page 18
  is the physical page and page 19 is accepted as a text-layer duplicate, noted
  in the report. Rendered with `pypdfium2` (already installed in the system
  Python); only pages 18 and 19 were viewed.
- `unsup_adjacent_01`: abstention is preserved. The SOP statement on the same
  page ("Minimum interval between application of chemical insecticide and
  harvest of maize corn should be 30 days") is maize-specific and must not be
  used for the rice question; a citation of it on this case is recorded as
  `forbidden_evidence`.

## Interpreting results

- **Sample size is small.** With 10 answerable cases per language, one case is
  10 percentage points. Report counts (k/n) beside every percentage. Treat
  differences between languages smaller than about 20 points as not
  distinguishable from noise; do not run significance tests on this sample.
  A 95 % Wilson interval may be shown for the headline rates.
- **Retrieval and answer quality are different claims.** A high Hit@5 says the
  evidence was found, not that the answer is good; extraction and citation
  results say what the user saw.
- **Abstention accuracy is the primary safety result.** A single false answer
  with a quantity is more important than the average.
- **Hindi/Kannada results are end-to-end results of two systems**
  (IndicTrans2 and the English pipeline). Use the paired difference from
  English and the failure categories to attribute losses; do not call a
  hi/kn retrieval miss a retrieval-model weakness without checking the
  translation first.
- **The development set must not be presented as final results.**
- A metric that was not produced by an executed run is not reported.

## Reproducibility

- Deterministic: exact FAISS search, BM25, beam-search decoding
  (`num_beams=5`, no sampling), `SEED=42`.
- Freeze before running: the case file (record its SHA-256), the code version
  (commit hash, or hashes of the source files if uncommitted), the FAISS index
  and manifests (hash and chunk count, currently 977), and the package
  versions of both environments. IndicTrans2 checkpoint revisions are
  recorded in the run log.
- Start a **fresh translation worker** for the run (the client keeps a small
  cache) and record cold and warm timings separately.
- One run of every case; the raw per-case output is kept. If a defect is found
  and fixed afterwards, rerun everything and report both runs; do not report
  only the better one, and do not edit cases after seeing results.
- `evaluation/run_evaluation.py` writes one machine-readable JSON file (per-case
  results, per-language and overall metrics, run identity) and one Markdown
  report to `evaluation/results/` (local, not tracked in the repository).
  Files are never overwritten. Both record the dataset SHA-256.

## Limitations to disclose in the project report

1. **Extractive system.** No LLM or AgriParam generation is part of this
   evaluation. The results say nothing about generated-answer quality,
   hallucination or fluency. AgriParam was tested separately in a small
   qualitative probe (3 English cases and 1 Hindi case, not part of the
   48-case set) and failed; it is not integrated, so the mandatory AgriParam
   requirement is unmet and must be stated as such in the report. AgriParam's
   licence is unresolved.
2. **Small, hand-written test set** (about 48 cases), annotated by a single
   author, with no inter-annotator agreement. Gold labels reflect that
   author's reading of the PDFs.
3. **Development-set tuning.** The retriever, gate and sentence selection
   were tuned against the 40 English development cases; English performance
   on the final set may differ from the development scores.
4. **Narrow knowledge base**: three English documents (about 938 pages, 977
   chunks), mostly Tamil Nadu sources. Results do not generalise to other
   crops, regions or documents.
5. **Translation-dependent retrieval.** Hindi and Kannada questions are not
   searched in their own language; they are translated to English first.
   Paraphrases of the same question can reach different evidence, and the
   evaluation includes only a few paraphrases.
6. **Manual translation scoring** depends on the evaluator's ability in each
   language; unless a fluent speaker reviews the Hindi and Kannada judgements,
   say so. The distilled 200M IndicTrans2 checkpoints were used, with
   technical terms sometimes transliterated.
7. **Source defects**: the drone SOP PDF has duplicated page text layers and
   flattened tables; page labels and some excerpts are affected, and a
   special reading was added for one table layout.
8. **Not measured**: user satisfaction, safety-layer behaviour (none is
   implemented), clarification of ambiguous questions (not supported),
   robustness to spelling noise or code-mixed input, and long-term stability.
9. **Hardware and latency** figures are from one CPU-only machine (16 GB RAM)
   and are descriptive.
10. **Post-evaluation tuning (2026-11-01).** Retrieval, gate, extraction and
    translation-unit changes were made after reading the failures of the 48-case
    run (see `docs/failure_remediation_20261101.md`). A re-run of the same 48
    cases is therefore a post-tuning measurement, not an independent test.
11. **Automatic must-preserve matching** cannot recognise units or identifiers the
    translator localised or reformatted, and the scorer reports (does not fail on)
    unresolved `<ID n>` placeholder markup in translated answers.
