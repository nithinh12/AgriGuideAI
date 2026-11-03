# Architecture

*Updated 2026-11-01 to describe the system as implemented. The BharatGen
AgriParam generator named in the project specification was downloaded and
evaluated but is **not integrated** because it failed the project's final
accuracy criteria, so the mandatory AgriParam requirement is **unmet**; it is
not part of the running system. See "AgriParam: evaluated, not integrated"
below.*

## Implemented pipeline

```
 user question (en / hi / kn)
        │
        ▼
 app/streamlit_app.py ── language selector · question box · result view
        │
        ▼
 src/multilingual_flow.py  (answer_multilingual)
        │
        ├─ en ───────────────────────────────────────────────┐
        │                                                    │
        └─ hi / kn: translate question → English             │
              via src/translation_client.py                  │
                 └─ persistent worker process (isolated env) │
                    src/translation_worker.py → src/translator.py (IndicTrans2)
                                                             │
                                                             ▼
                              English RAG pipeline  (src/rag_pipeline.py)
                                1) embed query            src/embeddings.py
                                2) hybrid retrieval       src/retriever.py
                                3) evidence-relevance gate src/retriever.py
                                4) extractive sentence selection
                                5) citations (original English passages)
                                                             │
        ┌────────────────────────────────────────────────────┘
        ▼
 hi / kn: translate the answer text English → target language (same worker)
        ▼
 result view: translated answer (labeled machine translation) +
              "Original English evidence" + English citations
```

English never touches the translator or the worker.

## Two environments

| Environment | Runs | Why |
|---|---|---|
| `.venv` (production, transformers 5.20.2) | Streamlit app, RAG pipeline, FAISS, E5 embeddings, test suite, translation client | The IndicTrans2 checkpoints' remote code does not load here (`No module named 'transformers.onnx'`) |
| `.venv-indic-test` (isolated, transformers 4.57.1, torch 2.14.1 CPU) | Translation worker only | The checkpoints load and run here, with `use_cache=False` (the default key/value cache fails in the checkpoints' modeling code on this version) |

The environments are never merged and production dependencies were not
upgraded to accommodate translation.

## Module responsibilities

| Module | Responsibility | Status |
|---|---|---|
| `src/config.py` | Env-driven settings, deterministic defaults, token masking | implemented |
| `src/document_loader.py` | Load PDFs from `data/raw/`, extract text per page with pypdf, attach provenance from `sources.jsonl` | implemented |
| `src/text_chunker.py` | Normalize text; sentence-aware word windows with overlap; page numbers preserved for citation | implemented |
| `src/embeddings.py` | multilingual-e5-small wrapper with the mandatory `query:`/`passage:` prefixes; CPU batch encode | implemented |
| `src/build_index.py` | CLI: load → chunk → embed → FAISS index + manifests | implemented |
| `src/retriever.py` | FAISS index (exact inner product over normalized vectors) plus BM25 lexical ranking fused by reciprocal rank; query normalization; the evidence-relevance gate | implemented |
| `src/rag_pipeline.py` | Orchestrates retrieval, gating, extractive answer generation, citations and abstention; returns a structured `AnswerResult` | implemented |
| `src/indic_processor.py` | Pure-Python port of IndicTransToolkit's `IndicProcessor` (MIT): normalization, tokenization, placeholder restore. Compared with the official Cython build in WSL2 earlier (0 differences over 19 steps; not re-run since) | implemented |
| `src/translator.py` | IndicTrans2 en⇄hi/kn on CPU from cached checkpoints (no downloads); Hindi↔Kannada by English pivot. Imported only by the worker | implemented |
| `src/translation_worker.py` | Long-lived worker process run with the isolated interpreter; JSON-lines protocol; loads each checkpoint once | implemented |
| `src/translation_client.py` | `SubprocessTranslator`: starts and restarts the worker, timeouts, output validation, small cache | implemented |
| `src/multilingual_flow.py` | Question → English RAG → answer translation; failure handling; `MultilingualResult` | implemented |
| `app/bootstrap.py` | Loads the saved FAISS index, manifests and local E5 model without rebuilding or downloading | implemented |
| `app/streamlit_app.py` | Streamlit UI: English, Hindi, Kannada; rendering of results, sources and failures | implemented |
| `src/llm_service.py` | AgriParam generation | **not implemented** (AgriParam evaluated and rejected on accuracy; requirement unmet) |
| `src/source_formatter.py` | (Planned in the original design.) Source rendering lives in `app/streamlit_app.py`; there is no separate module | not present |

## Retrieval and evidence selection

- **Retrieval**: dense search (FAISS, cosine over normalized E5 vectors) and
  BM25 over the same chunks, fused by reciprocal rank. The pipeline requests
  a wide candidate set and lets the gate decide.
- **Query normalization** (`src/retriever.py`): canonical forms for crop and
  topic words (for example irrigation/irrigated/irrigating → irrigate);
  broad question-intent words ("recommended", "need", "list") count toward
  coverage but are not mandatory; "under/in what conditions" is dropped as
  boilerplate while concrete conditions ("saline", "soil conditions") stay
  mandatory; "water" becomes irrigation **only** as a verb applied to a crop
  ("when to water wheat"), never for water bodies, spray volume or water
  management.
- **Evidence-relevance gate** (`FaissRetriever.relevant_evidence`): rejects
  questions about current or local information, questions outside the
  agricultural topics covered, passages for a different crop than the one
  asked about, passages that share too few question terms, passages missing a
  required context phrase (for example "before planting"), and table-of-
  contents pages. A pre-plant watering question must be supported by a clause
  that actually says so.
- **Extractive generation** (`ExtractiveEvidenceGenerator`): selects up to
  three verbatim sentences by question-term overlap and retrieval score.
  Safeguards: a weaker match from a different document than the best sentence
  is not appended; very long extracted blocks (60+ words) need strong
  overlap; supporting sentences must be near the best sentence in the same
  passage or nearly as strong; "which crops" questions are exempt from that
  locality rule; consecutive repeated table text is collapsed; text after an
  unrequested table caption is trimmed.
- **Special reading of one table**: for a "buffer zone" question the
  pipeline restates the drone SOP's flattened buffer-zone row in words, only
  when that row's labels and identical per-crop cells are present in the
  cited passage. This is specific to that layout.
- The answer is **extractive**: it quotes the knowledge base and generates no
  text of its own, apart from the buffer-zone restatement and from machine
  translation.

## Citations and abstention across languages

- Citations (`SourceCitation`: document, title, organization, URL, page,
  excerpt, score) come from the English pipeline result and are **never
  translated or altered**. The source documents are English, so a Hindi or
  Kannada user sees a translated answer plus the original English excerpts
  and page numbers, labeled as such. Identical excerpts are cited once.
- The pipeline **abstains** (answer kind `abstention`) when no passage
  passes the gates, when the question is empty, when selected text is not
  specific enough, or when no excerpt can be matched to the answer. An
  abstention carries **no citations**. In Hindi/Kannada the abstention
  message is translated like any other answer.
- If retrieval raises an unexpected error the result is an `error`, not an
  answer.

## Translation worker protocol

- The client starts `python -X utf8 -m src.translation_worker` using the
  isolated interpreter (`.venv-indic-test`, or `AGRIGUIDE_TRANSLATOR_PYTHON`)
  on the first Hindi or Kannada question and keeps it alive.
- One JSON object per line on stdin/stdout, ASCII-escaped, UTF-8 pipes;
  stdout carries protocol lines only (library output goes to stderr). The
  worker announces `ready`, then answers `translate`/`ping` requests with
  `ok`/`translations` or `ok:false`/`error`.
- The worker environment is UTF-8, offline (`HF_HUB_OFFLINE`,
  `TRANSFORMERS_OFFLINE`), and has variables containing TOKEN, SECRET,
  PASSWORD or API_KEY removed.
- Timeouts: 180 s to start, 300 s per request. A crashed, hung or malformed
  worker is killed and replaced on the next request.
- Both checkpoints are loaded lazily and stay resident. A measured run showed
  about 1.85 GB working set after both were loaded (about 380 MB before any
  model).
- Answers are translated sentence by sentence; a single sentence longer than
  256 model tokens is rejected rather than truncated.

## Trilingual request flow and failure handling

- **en**: question → English RAG → English result. No translation.
- **hi / kn**: translate the question (validated to contain Latin letters) →
  English RAG → translate the answer (validated to be mostly in the target
  script) → `MultilingualResult` with the translated answer, the original
  English evidence and the English citations.
- **Question translation fails** (worker missing, crash, timeout, empty or
  invalid output): nothing is searched; an error is shown.
- **Answer translation fails**: an error is shown, and the English evidence
  is displayed only as reference, marked as **not** a Hindi/Kannada answer.
  It is never presented as a successful translated answer.
- **Retrieval/pipeline error**: reported as an error; no answer is translated.
- Other failures: a missing FAISS index or local model produces a clear
  start-up error in the UI; all failures are logged without secrets.

## Language handling notes

- The embedding model handles en/hi/kn, but retrieval always uses the
  English question produced by translation. Hindi/Kannada text is not used
  directly for retrieval.
- Result quality depends on the English the translator produces; paraphrases
  of the same question can retrieve different evidence. A retrieval-relevance
  check exists for English only (40 cases); the final 48-case trilingual
  evaluation was run on 2026-11-01 (post-remediation: 38/48 strict, 16/16
  English, 11/16 Hindi, 11/16 Kannada). See `README.md` and
  `docs/evaluation_methodology.md` for the full results and caveats.

## Not implemented

- **Safety layer**: the original design called for flagging high-risk content
  (pesticide, fertilizer doses) and for general vs location-specific labels.
  This is **not implemented**. What exists is abstention with a pointer to a
  qualified agricultural expert / local KVK, and labeling answers as
  extracted evidence.
- **Retrieval-only fallback mode** and a hybrid original-plus-translated
  query for recall were considered in the design and are not built.

## AgriParam: evaluated, not integrated

BharatGen AgriParam (`bharatgenai/AgriParam`) is the answer generator named in
the project specification. **The professor's mandatory requirement to use it
remains unmet.** On 2026-11-01 the official checkpoint (pinned revision
`a6d42de79de39020e0e2f81d7c17663b9623a461`) was downloaded and run on CPU in
bf16 in an isolated environment, without touching the application. It was
**not integrated** because it failed the final accuracy criteria:

- Given real retrieved evidence in its official `<context>` prompt format,
  outputs included wrong or off-topic content (wrong irrigation interval, wrong
  gypsum quantity), and a Hindi question was answered in English with
  irrelevant text.
- Given only the gold passage, 0 of 3 English answers were fully correct
  (soybean K2O and sulphur rates wrong, finger-millet row spacing wrong,
  ratoon-sorghum irrigation incomplete) and the Hindi answer reversed a
  24-hour irrigation rule.
- Engineering costs: peak RSS about 8.8 GB on a 16 GB machine; 1 to 7.5 minutes
  per answer; the default `generate(use_cache=True)` fails with the pinned
  custom code under transformers 4.57.1, so decoding needed a manual
  key/value-cache loop (no upstream code was patched).

This was a small qualitative probe (3 English cases and 1 Hindi case, greedy
decoding, one prompt format), not a statistical evaluation. Experimentation
was then stopped by project decision. No code path calls AgriParam, there is
no `src/llm_service.py`, and the `LLM_MODEL`, `LLM_DTYPE` and
`LLM_MAX_NEW_TOKENS` settings in `src/config.py` and `.env.example` are unused
(`LLM_DEVICE` is only read as the embedding device by `src/build_index.py`).
Full evidence:
`artifacts/agriparam_cpu_smoke_test.md`. Had it been integrated, it would have
plugged in through the existing generator interface of `RAGPipeline`, with
Kannada still going through English via the translation flow, since AgriParam
supports English and Hindi only. Answers are extractive, as described above.
