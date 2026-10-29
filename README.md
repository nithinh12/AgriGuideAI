# AgriGuide AI

A trilingual (English / हिन्दी / ಕನ್ನಡ) AI agricultural advisory assistant for
Indian agriculture. It answers questions about crops, irrigation, and
fertilizers using **retrieval-augmented generation (RAG)** over curated,
credible agricultural advisory documents, with **source transparency** for
every substantive recommendation.

Academic mini-project — CS3235 (CIE3 Lab Assessment). Individual project.

## Status

**Milestone 1 complete (2026-10-29)** — working end-to-end core: document
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
- **Tests**: 47/47 passing (`pytest`, 2026-10-29), covering PDF extraction,
  chunking, retrieval/gating, provenance, abstention, and multilingual probes.
- **Answer generation** is currently *extractive* (quotes retrieved evidence,
  labeled `extractive_evidence`) — **BharatGen AgriParam integration is
  Phase 6** (deferred by decision; not yet downloaded).
- **Known limitations** (honest status): the cosine-score gate cannot yet
  abstain on *topically adjacent but irrelevant* questions (e.g. export
  certification queries hit horticulture text at ~0.84); Kannada
  relevant-vs-distractor margin is narrower (0.089) than en/hi (~0.144).
  Both are Phase-6/8 calibration items.

## Design goals

- **Prescribed models** (per project spec): BharatGen **AgriParam** as the
  domain answer generator; AI4Bharat **IndicTrans2** for translation. These
  are not to be silently replaced.
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
├── app/                    # Streamlit UI (Phase 7)
├── src/                    # Library code — one module per pipeline stage
│   └── config.py           # Env-driven settings (active)
├── data/
│   ├── raw/                # Downloaded source documents (gitignored)
│   ├── processed/          # Chunks, embeddings, FAISS index (gitignored)
│   └── README.md           # Provenance policy + sources registry
├── evaluation/             # 30–50 test cases, metrics, failure analysis
├── tests/                  # pytest suite (Phase 5+)
├── docs/
│   ├── model_selection.md        # Verified model compatibility report
│   ├── architecture.md           # Pipeline design
│   └── evaluation_methodology.md # Scoring rubrics (defined before tests)
├── .env.example            # Config template (copy to .env)
├── requirements.txt        # Verified dependency pins
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
5. *(upcoming Phase 7)* `streamlit run app/streamlit_app.py`.

## Key documents

| Document | Purpose |
|---|---|
| [`docs/model_selection.md`](docs/model_selection.md) | Verified facts about AgriParam, IndicTrans2, embeddings; hardware feasibility; decisions |
| [`docs/architecture.md`](docs/architecture.md) | Modules, data flow, trilingual strategy |
| [`docs/evaluation_methodology.md`](docs/evaluation_methodology.md) | Metrics and rubrics, defined **before** running the 30–50 case evaluation |
| [`data/README.md`](data/README.md) | Document provenance requirements and source registry |
| [`AGENTS.md`](AGENTS.md) | Constraints for AI agents working on this repo |

## License

Project code license: TBD (decided before GitHub publication).
Third-party models keep their own licenses (AgriParam: Apache-2.0;
IndicTrans2 checkpoints: MIT; multilingual-e5-small: MIT).
