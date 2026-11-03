# AgriGuide AI

A trilingual (English / हिन्दी / ಕನ್ನಡ) AI agricultural advisory assistant for
Indian agriculture. It answers questions about crops, irrigation, and
fertilizers using **retrieval-augmented generation (RAG)** over curated,
credible agricultural advisory documents, with **source transparency** for
every substantive recommendation.

Academic mini-project — CS3235 (CIE3 Lab Assessment). Individual project.

## Status

**Milestone 1 complete (2026-10-29); multilingual application working (verified 2026-10-31)** — working end-to-end core: document
ingestion → cleaning/chunking → multilingual embeddings → FAISS retrieval →
grounded answer pipeline with an abstention gate and source citations.

- **Knowledge base**: 3 verified official documents (~938 pages → 977 chunks):
  TNAU/Directorate-of-Agriculture *Crop Production Guide — Agriculture 2020*
  and *— Horticulture Crops 2020*, plus the Government of India *Crop-Specific
  SOP for Drone Pesticide Application 2023* (provenance in
  `data/raw/sources.jsonl`).
- **Embeddings**: `intfloat/multilingual-e5-small` (MIT, 384-dim, CPU),
  verified for en/hi/kn by measured probe similarities (see
  `tests/test_embeddings_multilingual.py`).
- **Tests**: **288 passed** (2026-11-01, `.\.venv\Scripts\python.exe -m pytest`,
  production environment; targeted retrieval remediation added 42 regression
  tests, bringing the suite from 246 to 288). The translation and multilingual
  tests use mocked models and a fake worker process; real-model behaviour was
  verified separately by the live runs described below, not by this suite.
- **Answer generation is extractive, not AgriParam-generated.** The pipeline
  quotes verbatim sentences from retrieved passages (answer kind
  `extractive_evidence`) and does not use an LLM.
- **BharatGen AgriParam was investigated but is NOT integrated, and the
  professor's mandatory AgriParam requirement remains UNMET.** The official
  `bharatgenai/AgriParam` checkpoint (pinned revision
  `a6d42de79de39020e0e2f81d7c17663b9623a461`, files hash-verified) was
  downloaded and evaluated on 2026-11-01 on CPU in bf16, in an isolated
  environment. It loads and generates, but it failed our final accuracy
  criteria: with retrieved evidence its answers contained wrong or off-topic
  content, and with only the gold passage supplied 0 of 3 English answers were
  fully correct (wrong soybean K2O and sulphur rates, wrong finger-millet row
  spacing, incomplete ratoon-sorghum irrigation) and a Hindi answer reversed an
  irrigation rule. Answers also took roughly 1 to 7 minutes each. This was a
  small qualitative probe (3 English cases and 1 Hindi case, greedy decoding,
  one prompt format), not a statistical evaluation. Experimentation was stopped
  and no code path calls AgriParam. Details: `artifacts/agriparam_cpu_smoke_test.md`
  and `docs/model_selection.md`. AgriParam's licence is **unresolved**; this
  project makes no licensing claim about it.
- **Hindi and Kannada are working end to end** (verified 2026-10-31 by real
  IndicTrans2 inference through the Streamlit flow, not only by unit tests):
  the question is translated to English, answered by the English RAG
  pipeline, and the answer text is translated back. Source citations stay in
  English. See "How a question is answered" below.
- **Retrieval relevance check** (English, 40 labeled cases,
  `evaluation/retrieval_relevance_cases.jsonl`): baseline (2026-10-31): 19 of
  27 answerable cases answered with gold evidence, 8 abstained, 13 of 13
  unsupported/unrelated cases abstained. Post-remediation replay (2026-11-01,
  same dataset, same pipeline after targeted fixes): 21 of 27 answered with
  gold evidence (see `docs/failure_remediation_20261101.md`). This is a
  retrieval development check, **not** the final trilingual evaluation.
- **Final trilingual evaluation** (48 cases: 16 English, 16 Hindi, 16 Kannada;
  `evaluation/test_cases.jsonl` SHA-256 `5e7491da…`). Post-remediation run
  2026-11-01 through the real application flow:

  | Metric | Result |
  |---|---|
  | Overall strict accuracy | **38/48 (79.2%)** |
  | English | 16/16 (100%) |
  | Hindi | 11/16 (68.8%) |
  | Kannada | 11/16 (68.8%) |
  | Unsupported queries safely abstained (no citations) | 12/12 |

  Scoring rules: `docs/evaluation_methodology.md` and `evaluation/scoring.py`;
  runner: `evaluation/run_evaluation.py`. Per-run output files are written to
  `evaluation/results/`, which is not tracked in this repository.
  **Caveats:** (1) the evaluation dataset was used during development
  (retrieval-gate tuning and targeted remediation of 11 failing cases), so it
  is **not an independent held-out test set** and these numbers likely
  overestimate out-of-distribution performance; (2) the 32 Hindi and Kannada
  evaluation questions were AI-written and manually reviewed by the project
  owner, but **have not been validated by native speakers** (see
  `evaluation/native_language_review.md`).

### Two Python environments (by design, never merged)

| Environment | Used for | Notes |
|---|---|---|
| `.venv` (production) | Streamlit app, RAG pipeline, FAISS, E5 embeddings, the test suite | transformers 5.20.2. The IndicTrans2 checkpoints' remote code does **not** load here (`No module named 'transformers.onnx'`) |
| `.venv-indic-test` (isolated) | IndicTrans2 translation worker only | transformers 4.57.1, torch 2.14.1 (CPU). Translation runs with `use_cache=False`, because the checkpoints' modeling code fails with the default key/value cache on this version |

The app talks to a **persistent translation worker**
(`python -m src.translation_worker`, started with the isolated interpreter)
through `src/translation_client.py`. The worker is started on the first Hindi
or Kannada question, keeps both translation checkpoints loaded, and is
restarted if it crashes or times out. Messages are one JSON object per line
over stdin/stdout, ASCII-escaped so they survive any console code page. The
worker runs offline from the cached checkpoints and does not receive
credentials (variables containing TOKEN, SECRET, PASSWORD or API_KEY are
removed from its environment).

### How a question is answered

1. **English**: the question goes straight to the English RAG pipeline. No
   translation and no worker.
2. **Hindi / Kannada**: the question is translated to English; the existing
   English pipeline retrieves and selects evidence; the answer text is
   translated back sentence by sentence. The English question the model
   produced is shown to the user.
3. **Retrieval**: hybrid dense (multilingual-e5-small, FAISS) plus lexical
   (BM25) ranking fused by reciprocal rank, followed by an evidence-relevance
   gate that checks crop agreement and question-term support.
4. **Evidence selection**: deterministic extractive sentence selection with
   safeguards for very long extracted blocks and for repeated table text.
5. **Citations**: always the original English passages (title, issuing
   organization, URL, page number, excerpt); they are never translated.
   A translated answer is labeled as machine translation and kept apart from
   the "Original English evidence".
6. **Abstention**: when evidence is insufficient the pipeline abstains and
   returns **no citations**. In Hindi/Kannada the abstention message is
   translated.
7. **Translation failure**: never a crash and never presented as a Hindi or
   Kannada answer. If the question cannot be translated, nothing is searched
   and an error is shown. If only the answer cannot be translated, the error
   is shown and the English evidence is displayed marked "NOT a Hindi/Kannada
   answer".

- **Milestone status**: Milestones 1 and 2 are substantially complete
  (12 of 13 Milestone-2 tasks verified; task 10, the AgriParam integration, is
  **not done**: AgriParam was downloaded and evaluated but not integrated, see
  above. 12/13 task completion does **not** mean the prescribed-model
  requirement is fulfilled; it is unmet). Milestone 3: evaluation and
  documentation complete. Final post-remediation run 2026-11-01: **38/48
  strict pass (79.2%)**; English 16/16 (100%), Hindi 11/16 (68.8%), Kannada
  11/16 (68.8%). Dataset caveat above applies. Project report:
  `AgriGuideAI_Report_Compressed.pdf`. UI screenshots (4 viewport sizes,
  desktop through mobile): `artifacts/ui_redesign_20261102/photo_background/viewport/`.
  See `MILESTONE_PROGRESS.md` and [`docs/model_selection.md`](docs/model_selection.md).
- **Known limitations** (honest status):
  - Hindi and Kannada answer quality depends on how the question happens to
    be translated into English. Some phrasings abstain or return a partial
    answer (for example, a "when to water wheat" answer says "at the critical
    stages" without listing them). An earlier live run also returned an
    irrelevant drone-SOP passage for one Hindi phrasing, since fixed by a
    query-normalization change.
  - Only a few wheat-irrigation questions were checked live in Hindi and
    Kannada. Translation quality was read for plausibility only and has not
    been reviewed by a native speaker. Kannada output contains transliterated
    technical terms and stray punctuation after colons.
  - The first Hindi or Kannada question takes roughly 35 to 65 seconds while
    the worker loads the models. The worker then holds about 1.85 GB of RAM.
  - A single sentence over 256 model tokens cannot be translated; the user is
    told the translation failed.
  - Extractive answers can be incomplete or contain adjacent unrelated
    sentences. The buffer-zone table answer is a special reading of one
    specific table layout. The source drone SOP PDF has duplicated page text
    layers, so some chunks labeled with one page contain text printed on its
    neighbour.
  - The creation procedure for `.venv-indic-test` is documented in
    `docs/indictrans2_environment.md` but has not been re-run from an empty
    directory.
  - The Milestone-1 note that the cosine-score gate alone could not abstain on
    topically adjacent but irrelevant questions (e.g. export certification
    queries hit horticulture text at ~0.84) predates the evidence-relevance
    gate and has not been re-measured; Kannada's relevant-vs-distractor
    embedding margin (0.089) is narrower than en/hi (~0.144).

## Design goals

- **Prescribed models** (per project spec): BharatGen **AgriParam** as the
  domain answer generator; AI4Bharat **IndicTrans2** for translation. These
  were not silently replaced: IndicTrans2 is integrated and working;
  AgriParam was tested but failed the accuracy criteria and is **not**
  integrated, so the requirement to use it is unmet. The running system's
  answers are extractive, with no generative model.
- **Evidence grounding**: answers are generated only from retrieved passages;
  when evidence is insufficient, the app says so instead of inventing answers.
- **Source transparency**: every recommendation shows source title, issuing
  organization, URL, and a supporting excerpt.
- **Safety**: no unsupported fertilizer/pesticide doses; general guidance is
  distinguished from location-specific advice; users are directed to
  agricultural experts when evidence is weak.
- **CPU-first**: retrieval and inference run on CPU by default (16 GB RAM);
  the 4 GB RTX 3050 is not used for model inference.

## Repository layout

```
AgriGuideAI/
├── app/
│   ├── bootstrap.py        # Loads the saved FAISS index + local E5 model
│   └── streamlit_app.py    # Streamlit UI (English / Hindi / Kannada)
├── src/                    # Library code — one module per pipeline stage
│   ├── config.py                # Env-driven settings
│   ├── document_loader.py       # PDF text extraction + provenance
│   ├── text_chunker.py          # Sentence-aware chunking, page numbers kept
│   ├── embeddings.py            # multilingual-e5-small wrapper
│   ├── build_index.py           # CLI: documents -> chunks -> FAISS index
│   ├── retriever.py             # Hybrid retrieval + evidence-relevance gate
│   ├── rag_pipeline.py          # Extractive answer pipeline, citations, abstention
│   ├── indic_processor.py       # Pure-Python IndicProcessor port (MIT)
│   ├── translator.py            # IndicTrans2 wrapper (runs in .venv-indic-test)
│   ├── translation_worker.py    # Persistent translation worker process
│   ├── translation_client.py    # Production-side client for the worker
│   └── multilingual_flow.py     # Question -> English RAG -> answer translation
├── data/
│   ├── raw/                # Downloaded source documents (gitignored)
│   ├── processed/          # Chunks, embeddings, FAISS index (gitignored)
│   └── README.md           # Provenance policy + sources registry
├── evaluation/             # 48-case trilingual dataset, scorer and runner
│                           # (run_evaluation.py); 40-case retrieval development set
│                           # + its own runner; run outputs go to evaluation/results/ (not tracked)
├── tests/                  # pytest suite (288 tests; tests/differential/ holds
│                           # the IndicProcessor differential cases)
├── assets/
│   └── agriguide_background.webp  # Full-screen background (AI-generated for this project)
├── .streamlit/
│   └── config.toml         # Light theme, minimal toolbar, watcher disabled
├── artifacts/              # Recorded smoke-test and evaluation outputs;
│                           # final UI screenshots in
│                           # artifacts/ui_redesign_20261102/photo_background/viewport/
├── docs/
│   ├── model_selection.md        # Verified model compatibility report
│   ├── architecture.md           # Pipeline design as implemented
│   ├── evaluation_methodology.md # Scoring rubrics (defined before tests)
│   ├── third_party_licenses.md   # Third-party license notices
│   └── indictrans2_environment.md # Isolated translation environment (recreation)
├── MILESTONE_PROGRESS.md   # Verified task tracker
├── .env.example            # Config template (copy to .env)
├── requirements.txt        # Verified dependency pins (production .venv)
└── AGENTS.md               # Rules for AI coding agents on this project
```

## Setup

1. Create/activate the virtual environment: `.venv\Scripts\activate`
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in values. An Hugging Face token
   (`HF_TOKEN`) is required for the **gated** IndicTrans2 checkpoints
   (auto-approve license on their model pages).
4. Build the index over `data/raw/`:
   `python -m src.build_index` (~3.5 min on CPU for the current KB; writes
   `data/processed/` artifacts).
5. Launch the app: `.venv\Scripts\streamlit run app/streamlit_app.py`.
   English runs entirely in `.venv`. Hindi and Kannada additionally start a
   persistent translation worker (`python -m src.translation_worker`) with the
   isolated interpreter `.venv-indic-test\Scripts\python.exe` (override with
   `AGRIGUIDE_TRANSLATOR_PYTHON`). The two environments are never merged:
   IndicTrans2's remote code does not load under the production `.venv`
   (transformers 5.x). The worker uses cached checkpoints only (offline) and
   the first Hindi/Kannada question loads the models (about a minute).
   The recorded versions of the isolated environment are transformers 4.57.1,
   torch 2.14.1 (CPU), sentencepiece 0.2.2, sacremoses 0.2.0 and
   indic-nlp-library-itt 0.1.1. The full recorded package list and a
   reconstructed (not re-run from scratch) creation procedure are in
   [`docs/indictrans2_environment.md`](docs/indictrans2_environment.md).

## Key documents

| Document | Purpose |
|---|---|
| [`docs/model_selection.md`](docs/model_selection.md) | Verified facts about AgriParam, IndicTrans2, embeddings; hardware feasibility; decisions |
| [`docs/architecture.md`](docs/architecture.md) | Modules, data flow, trilingual strategy |
| [`MILESTONE_PROGRESS.md`](MILESTONE_PROGRESS.md) | Milestone task tracker; "done" only with executed evidence |
| [`docs/third_party_licenses.md`](docs/third_party_licenses.md) | Third-party license notices |
| [`docs/indictrans2_environment.md`](docs/indictrans2_environment.md) | Isolated IndicTrans2 environment: recorded packages and recreation steps |
| [`artifacts/agriparam_cpu_smoke_test.md`](artifacts/agriparam_cpu_smoke_test.md) | AgriParam download, CPU tests and the decision not to integrate |
| [`docs/evaluation_methodology.md`](docs/evaluation_methodology.md) | Metrics and rubrics, defined **before** running the 30–50 case evaluation |
| [`data/README.md`](data/README.md) | Document provenance requirements and source registry |
| [`AGENTS.md`](AGENTS.md) | Constraints for AI agents working on this repo |

## License

Project code license: TBD (decided before GitHub publication).
Third-party models keep their own licenses (IndicTrans2 checkpoints: MIT;
multilingual-e5-small: MIT). BharatGen AgriParam's licence is **unresolved**
(see `docs/third_party_licenses.md`); it is not used by the application, and
no licensing claim is made for it.
