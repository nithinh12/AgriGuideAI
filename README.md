# AgriGuide AI

A trilingual (English / हिन्दी / ಕನ್ನಡ) AI agricultural advisory assistant for
Indian agriculture. It answers questions about crops, irrigation, and
fertilizers using **retrieval-augmented generation (RAG)** over curated,
credible agricultural advisory documents, with **source transparency** for
every substantive recommendation.

Academic mini-project — CS3235 (CIE3 Lab Assessment). Individual project.

## Status

**Scaffold phase (2026-10-29).** The application is not yet functional.
Verified model compatibility is documented in
[`docs/model_selection.md`](docs/model_selection.md). Nothing is claimed to
work until it has been implemented and tested.

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
4. *(upcoming)* Build the FAISS index over `data/raw/`, then
   `streamlit run app/streamlit_app.py`.

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
