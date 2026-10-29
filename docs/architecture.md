# Architecture

*Draft — 2026-10-29 (scaffold phase). Update as implementation lands.*

## Pipeline overview

```
                    ┌────────────────────────────────────────────────────┐
 user question      │                  Streamlit app (app/)              │
 (en / hi / kn) ───►│  language selector · question box · answer +       │
                    │  sources panel · safety notices                   │
                    └───────────────┬────────────────────────────────────┘
                                    │
              ┌─────────────────────▼─────────────────────┐
              │ src/rag_pipeline.py  (orchestrator)       │
              └─────────────────────┬─────────────────────┘
                                    │
   1) if lang != en:  src/translator.py  (IndicTrans2 en⇄hi/kn, English pivot)
   2) embed query:    src/embeddings.py  (multilingual-e5-small, "query:" prefix)
   3) retrieve:       src/retriever.py   (FAISS IndexFlatIP over normalized
                                          embeddings, top-k + score filter)
   4) compose prompt: <context> evidence <user> question <assistant>
   5) generate:       src/llm_service.py (AgriParam, CPU bf16, short answers,
                                          abstention instruction when evidence
                                          is weak)
   6) translate back: src/translator.py  (en → target language)
   7) format:         src/source_formatter.py (sources, excerpts, safety
                                          labels, retrieved vs generated)
```

## Module responsibilities

| Module | Responsibility | Status |
|---|---|---|
| `src/config.py` | Env-driven settings, deterministic defaults, token masking | implemented |
| `src/document_loader.py` | Load PDFs/TXT from `data/raw/`, extract text via pypdf, attach provenance from `sources.jsonl` | planned (Phase 5) |
| `src/text_chunker.py` | Clean/normalize text; split into overlapping chunks that keep sentence/number integrity | planned (Phase 5) |
| `src/embeddings.py` | Wrap multilingual-e5-small with the mandatory `query:`/`passage:` prefixes; batch encode on CPU | planned (Phase 5) |
| `src/retriever.py` | Build/load FAISS index; top-k search with a minimum-score gate (enables honest abstention) | planned (Phase 5) |
| `src/translator.py` | en⇄hi and en⇄kn via IndicTrans2 dist-200M; Windows preprocessing shim; terminology/number checks | planned (Phase 6) |
| `src/llm_service.py` | AgriParam loading (CPU bf16, `trust_remote_code`), prompt building, generation, timeouts, failure fallbacks | planned (Phase 6) |
| `src/rag_pipeline.py` | Orchestrate 1–7; produce a structured result object (answer, sources, flags) | planned (Phase 6) |
| `src/source_formatter.py` | Render source cards (title, org, URL, excerpt); distinguish retrieved facts from generated text | planned (Phase 7) |
| `app/streamlit_app.py` | Trilingual UI | planned (Phase 7) |

## Trilingual strategy

AgriParam supports **English and Hindi only**; Kannada support must come from
translation (verified — see `docs/model_selection.md`).

- **en question** → retrieve (e5 works multilingually, but we query with the
  English text for best recall) → AgriParam (English) → answer in English.
- **hi question** → translate hi→en (IndicTrans2 `indic-en`) → retrieve +
  generate in English → translate answer en→hi (IndicTrans2 `en-indic`).
  *Alternative considered*: retrieve with Hindi text directly (e5 supports
  hi). Chosen approach keeps generation in the model's stronger language and
  matches the spec's translation requirement; retrieval may also be run with
  the original-language query as a recall boost (hybrid query = concat of
  original + translated) — to be decided by evaluation results.
- **kn question** → same pivot via English (kn⇄en checkpoints exist).
- Source titles/excerpts shown in their original language with the translated
  question alongside, so users can see what the evidence actually says.

## Grounding and abstention

- Retrieval gate: if the best FAISS score is below a configurable threshold,
  the pipeline **abstains** — it returns "insufficient evidence in the
  knowledge base" plus pointers to consult an agricultural expert, instead of
  generating.
- The prompt instructs AgriParam to answer **only** from `<context>` and to
  say when the context does not contain the answer (faithful QA).
- Every answer object carries its sources; the UI cannot render an answer
  without them.

## Safety layer

- Detect and flag high-risk content (pesticide recommendations, specific
  fertilizer doses without soil/crop context) and attach "consult a qualified
  agricultural expert / local KVK" notices.
- General vs location-specific: the answer is labeled by whether retrieved
  evidence mentions the user's crop/region explicitly.
- No claim of official government endorsement unless the source itself is the
  government document being quoted (then it is cited as such).

## Failure handling

- Missing model / OOM at load time → clear error surfaced in UI + log;
  RAG retrieval-only mode still shows evidence excerpts (no generated claims).
- Translation failure → fall back to showing the English answer with a notice.
- FAISS index missing → UI explains that the index must be built first.
- All failures logged via `logging` with no secrets.
