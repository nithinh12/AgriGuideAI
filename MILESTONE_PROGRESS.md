# Milestone progress — AgriGuide AI

Tracking file for CS3235 CIE3 mini-project milestones. Completion =
verified-complete tasks / total tasks for the milestone ("verified" = backed by
executed evidence: command output, test runs, or validated artifacts — never
assumed). This file was created 2026-10-29 during Milestone 2, Step 3.

---

## Milestone 1 — offline RAG core (COMPLETE, 2026-10-29)

- 47/47 tests passed (100.6 s at the time); FAISS index built over 977 chunks
  from provenance-tracked sources; commits `200233e` → `d31ba89`.

---

## Milestone 2 — prescribed-model integration (12/13 tasks verified; AgriParam evaluated but NOT integrated: professor's requirement UNMET)

13 equally weighted tasks. Last updated: 2026-10-31.

| # | Task | Status | Evidence |
|---|---|---|---|
| 1 | HF Hub access verified for gated IndicTrans2 checkpoints | ✅ done (Step 1) | `hf_hub_download` test with token from `.env`; no token logged |
| 2 | `indictrans2-en-indic-dist-200M` checkpoint downloaded + safetensors validated | ✅ done | 2026-10-30 snapshot in the project-local `.cache/huggingface/hub/` contains 12 required files / 1,106,584,395 B; safetensors SHA-256 matches Hub manifest; 767 tensor keys; no `pytorch_model.bin` |
| 3 | `indictrans2-indic-en-dist-200M` checkpoint downloaded + safetensors validated | ✅ done | 2026-10-30 snapshot in the project-local `.cache/huggingface/hub/` contains all 11 required files published by this repo / 921,510,585 B; safetensors SHA-256 matches Hub manifest; 767 tensor keys; no `pytorch_model.bin` (repo does not publish `special_tokens_map.json`) |
| 4 | Translator Python dependencies reviewed, installed, pinned | ✅ done (Step 3) | `sentencepiece 0.2.2`, `sacremoses 0.2.0`, `indic-nlp-library-itt 0.1.1`, `nltk 3.10.4` (`regex 2026.9.29` already present); pinned in `requirements.txt` |
| 5 | `src/indic_processor.py` — pure-Python Windows port of the official `IndicProcessor` | ✅ done (Step 3) | mechanical port of MIT `processor.pyx`; smoke round-trips pass; 18 unit tests pass |
| 6 | Differential verification of the port vs the official Cython build | ✅ done (Step 3) | official toolkit compiled in WSL2; 5 scenarios / 19 steps compared with `PYTHONHASHSEED=0`: **0 differences**, 1 wording-only warning (Cython vs CPython unpack error message, same `ValueError`); see `tests/differential/` |
| 7 | Unit tests for translation pre/post-processing (en↔hi, en↔kn, edge/error cases) | ✅ done (Step 3) | `tests/test_indic_processor.py`: 18 passed in 0.94 s; **full suite 65/65 passed in 100.6 s** |
| 8 | AgriParam checkpoint download + CPU load test | ✅ done as a diagnostic (2026-11-01); NEGATIVE outcome | Approved download of the official files at revision `a6d42de79de39020e0e2f81d7c17663b9623a461` (11,442,692,776 B; hashes verified), isolated CPU bf16 load and generation in `.venv-indic-test`. It loads and generates, but `generate(use_cache=True)` fails and, in the realistic-context and gold-passage-only tests, answers were wrong (0 of 3 English gold-only answers fully correct; a Hindi answer reversed a rule). Full record: `artifacts/agriparam_cpu_smoke_test.md`. Doing the task does **not** mean the requirement is met. |
| 9 | `src/translator.py` (model load + en⇄hi/kn wrappers) | ✅ done | Wrapper/routing/error handling is implemented and mocked tests were previously recorded. Real CPU inference has now succeeded for en→hi, en→kn, hi→en, kn→en, hi→kn via English pivot, and kn→hi via English pivot; the per-direction smoke-test and pivot-test logs were kept locally as development diagnostics and are not tracked in the repository. The pivot reports confirm the two model instances were not held simultaneously. Production `.venv` (transformers 5.20.2) cannot load the checkpoints; inference runs in the isolated `.venv-indic-test` (transformers 4.57.1) with `use_cache=False`, reached through the persistent translation worker (`src/translation_worker.py`, `src/translation_client.py`). |
| 10 | `src/llm_service.py` (AgriParam, CPU bf16, fallbacks) | ❌ not done, abandoned | AgriParam failed the final accuracy criteria (task 8), so it was **not integrated**. No `llm_service.py` exists and no code path calls the model. **The professor's mandatory AgriParam integration requirement is UNMET.** |
| 11 | RAG pipeline trilingual wiring (query translate → retrieve → generate → answer translate) | ✅ done (extractive generation; AgriParam not integrated) | `src/multilingual_flow.py` (question → English RAG → answer translation), `src/translation_client.py`, `src/translation_worker.py`, `app/streamlit_app.py` language selector. English bypasses translation. Failures never crash and are never shown as successful Hindi/Kannada answers; citations stay the original English passages and abstentions carry no citations. Evidence: `tests/test_multilingual.py` (38 tests, fake worker/translators) and real inference runs on 2026-10-31 (task 12 and the log below). "Generate" is the existing extractive generator, so the original dependency on task 10 is **not** satisfied. |
| 12 | End-to-end trilingual smoke test (en / hi / kn questions) | ✅ done (smoke test; quality limited, not an evaluation) | 2026-10-31, real IndicTrans2 worker + real FAISS index. `AppTest` of the actual `main()` for en/hi/kn: no exceptions; English and Hindi answered from TNAU page 136, Kannada abstained for that phrasing. Six Hindi/Kannada wheat-irrigation questions: all reached TNAU Agriculture page 136; 2 Kannada questions returned the complete five-stage answer, 3 Hindi questions returned a partial answer (stage list missing), and 1 Kannada question selected a fertilizer-table chunk whose answer translation failed with the 256-token limit (reported correctly as a translation failure). After the contextual `water`-verb normalization, the exact Kannada question "ಗೋಧಿಗೆ ಯಾವಾಗ ನೀರು ಹಾಕಬೇಕು?" (English: "When to water wheat?") returned the page 136 irrigation passage and translated without error, and its two five-stage control questions still returned the five-stage answer. Only wheat-irrigation phrasings were exercised live; translation quality was not reviewed by a native speaker. |
| 13 | Docs: `model_selection.md` PyICU/Kannada-transliteration corrections + status updates | ✅ done | `model_selection.md` now distinguishes the Windows Cython build blocker from PyICU, documents the port's Hindi-intermediate transliteration, and labels the prior differential result as not rerun in this session; README status updated; architecture status already recorded |

**Completion: 12/13 ≈ 92.3 %** (tasks 1–9 and 11–13 verified complete; task 10, the AgriParam integration, is **not** done). Calculation: 12 ÷ 13 × 100 = 92.307…%. **12/13 task completion does NOT mean the prescribed-model requirement is fulfilled.** The professor's mandatory AgriParam integration requirement is **unmet**: task 8 is counted only because the download and CPU diagnostic were carried out (with a negative result), and task 10, the integration itself, is incomplete and abandoned. The percentage was 11/13 ≈ 84.6 % until 2026-10-31, when tasks 8 and 10 were both deferred.

### Verification log (2026-10-31)

- **Full suite**: `.\.venv\Scripts\python.exe -m pytest -v` -> **206 passed, 0 failed,
  0 skipped, 0 errors in 119.95 s** (production `.venv`). By file:
  `test_app` 7, `test_document_loader` 10, `test_embeddings_multilingual` 5,
  `test_indic_processor` 18, `test_multilingual` 38, `test_provenance` 5,
  `test_rag_pipeline` 45, `test_retriever` 50, `test_text_chunker` 11,
  `test_translator` 17. (The earlier "65/65" in task 7 is a historical count.)
  The translation tests use mocked models or a fake worker; real inference is
  evidenced by the live runs in task 12, not by this suite.
- **Retrieval relevance check** (English only, 40 labeled cases,
  `evaluation/retrieval_relevance_cases.jsonl`; run output kept locally,
  not tracked): baseline 2026-10-31: 19 of 27 answerable answered with gold
  evidence, 8 abstained; 13 of 13 unsupported or unrelated cases abstained, 0
  answered. Post-remediation replay 2026-11-01: 21 of 27 answered with gold
  evidence (details in `docs/failure_remediation_20261101.md`). This is **not**
  the Milestone-3 trilingual evaluation.
- **Translation worker memory** (measured): about 378 MB before any model,
  about 1.24 GB after the English->Indic checkpoint, about 1.85 GB with both
  checkpoints resident.
- **Git**: HEAD is still `d31ba89` (Milestone 1). All Milestone 2 work and
  the multilingual application are uncommitted working-tree changes.

### Known risks / open items (Milestone 2)

- Both required IndicTrans2 dist-200M snapshots exist in the project-local
  `.cache/huggingface/hub/` and their safetensors integrity checks passed. The
  Transformers module cache resolves to the project-local
  `.cache/huggingface/modules/`, and real CPU inference validation has succeeded for all six supported
  direct/pivot directions (task 9 evidence above).
- AgriParam was only ever run under transformers 4.57.1 (isolated
  environment); loading it under the production transformers 5.20.2 was never
  tested. Moot, since it is not integrated.
- Official-code findings recorded 2026-10-29 (see `tests/test_indic_processor.py`
  docstring + `tests/differential/cases.json`): `IndicProcessor.preprocess_batch`
  SIGSEGVs on a `src_lang` without `_`; `postprocess_batch` with an empty
  placeholder queue blocks forever; IndicTransToolkit 1.1.1's package `__init__`
  is incompatible with transformers 5.x (the processor extension itself is fine).
  `src/translator.py` must respect the preprocess→(infer)→postprocess sequence.
- Timeline: trilingual Streamlit Nov 1 · 40-case eval dataset Nov 2 · eval +
  rubrics Nov 3 · failure analysis Nov 4 · docs/screenshots Nov 5 · submission
  Nov 6, 10:00.
- **AgriParam (prescribed model) was downloaded and evaluated on 2026-11-01
  but not integrated, because it failed the final accuracy criteria. The
  professor's mandatory requirement is UNMET** and must be disclosed in the
  report and presentation, not worked around or described as fulfilled. This
  is not a substitution: the running system uses extractive answers and no
  generative model. AgriParam experimentation is stopped. Its licence is
  unresolved (no licensing claim). Evidence: `artifacts/agriparam_cpu_smoke_test.md`.
  The 11.4 GB checkpoint remains in the gitignored `.cache/` (not deleted).
- Two environments are required (`.venv`, `.venv-indic-test`). The recorded
  package list and a reconstructed creation procedure are now in
  `docs/indictrans2_environment.md`; the procedure has **not** been re-run
  from an empty directory (open item).
- Hindi/Kannada answer quality depends on the English the translator
  produces; some phrasings abstain or return partial answers. The first
  Hindi/Kannada request takes roughly 35-65 s (model load) and the worker
  holds about 1.85 GB of RAM.

---


## Milestone 3 — evaluation & report (in progress)

Task breakdown recorded 2026-10-31. Status updated through 2026-11-03.
Nothing is marked done without executed evidence. The existing 40-case English
retrieval relevance set and the 288-test suite are precursors, not these
deliverables. Submission: 2026-11-06, 10:00.

| # | Task | Status | Evidence required before marking done |
|---|---|---|---|
| 1 | Trilingual evaluation set of 30–50 cases (English, Hindi, Kannada, including unsupported questions) | ✅ done | 48 cases (16 per language), SHA-256 `5e7491daac6240bf6a4c77f14014c399a7fcce2a8caa96f8c822dea08bbe0a5a`, verified 2026-11-01. Dataset approved after audit of 9 manual corrections (`evaluation/EVALUATION_DATASET_AUDIT.md`). |
| 2 | Evaluation rubrics and metrics finalized | ✅ done | `evaluation/scoring.py` implements strict/partial/must-preserve metrics plus `translation_artifacts` flag. `docs/evaluation_methodology.md` documents rubrics and limitations (sections 10–11 added post-run). Defined and reviewed before final evaluation run. |
| 3 | Run the evaluation and record results | ✅ done | Baseline run 2026-11-01 (`20261101T154404Z`): 17/48 strict. Post-remediation run 2026-11-01 (`20261101T184956Z`): **38/48 strict pass, 79.2%**; English 16/16, Hindi 11/16, Kannada 11/16; 0 false answers; 5/16 Kannada answers flagged `translation_artifacts`. Each run's JSON results and Markdown report were written to `evaluation/results/`, which is local and not tracked in the repository; the final numbers are summarised in `README.md`. **Caveat: the dataset was used during development (retrieval tuning, targeted remediation of 11 cases) and is not an independent test set.** |
| 4 | Failure analysis | 🟨 partial | 10 failed cases identified and categorised in the evaluation report: `hi_irrig_01`, `hi_irrig_01_alt`, `kn_irrig_01`, `kn_irrig_01_alt`, `hi_irrig_02`, `kn_irrig_02`, `hi_irrig_03`, `kn_irrig_03`, `hi_fert_01`, `kn_fert_02`. Root causes: MT paraphrase gaps (hi/kn failed on "important" vs "critical" and "planting distance"; MT produced "rattune corn"), insufficient multi-hop context for kn_fert_02. Formal write-up beyond the run report not done. |
| 5 | Final documentation and limitations | ✅ done | README updated with final eval numbers and dataset caveat; `docs/architecture.md`, `docs/model_selection.md`, `docs/evaluation_methodology.md`, `docs/third_party_licenses.md`, `docs/indictrans2_environment.md`, `.env.example` all synchronized; app sidebar states model limitation; IndicTrans2 `<ID n>` placeholder artifact (Kannada output, 5/16 cases) disclosed in scorer and methodology docs. |
| 6 | Project report | 🟨 exists | `AgriGuideAI_Report_Compressed.pdf` present in project root. Content not independently re-verified against all recorded numbers in this session. |
| 7 | Screenshots and demo preparation | ✅ done | Four viewport-size screenshots of the final Streamlit UI (desktop 1920×1080, laptop 1366×768, tablet 820×1180, mobile 390×844) in `artifacts/ui_redesign_20261102/photo_background/viewport/`. Full-page development captures were also taken but are not tracked in the repository. App was verified end-to-end in Chrome: English answer, abstention, Hindi/Kannada selectors and translation (hi/kn submissions re-run earlier in the session). |

**Completion: 5 verified complete, 2 partial (tasks 4 and 6) ≈ 71 %.** The unmet item from Milestone 2 (AgriParam integration, task 10) remains unmet and is not counted here.

### Verification log (2026-11-01 — post-remediation)

- **Full suite**: `.\.venv\Scripts\python.exe -m pytest` → **288 passed, 0 failed, 0 skipped** (production `.venv`; suite grew from 246 to 288 with remediation regression tests).
- **Protected files** (src/retriever.py, src/rag_pipeline.py, src/multilingual_flow.py, translation worker, evaluation data, evaluation scoring): SHA-256-verified unchanged (21/21) after all remediation and UI work.
- **Evaluation final run** (command: `.venv\Scripts\python.exe -m evaluation.run_evaluation --expect-sha256 5e7491daac6240bf6a4c77f14014c399a7fcce2a8caa96f8c822dea08bbe0a5a`): strict 38/48 (79.2%), 0 false answers, dataset-integrity check passed.

- Timeline (from the Milestone 2 plan): 40-case eval dataset Nov 2 · eval +
  rubrics Nov 3 · failure analysis Nov 4 · docs/screenshots Nov 5 ·
  submission Nov 6, 10:00.
