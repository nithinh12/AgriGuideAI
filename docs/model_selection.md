# Model Selection — Verified Compatibility Report

*Compiled 2026-10-29 from official sources (Hugging Face API/model cards,
official GitHub repositories). Every fact below was fetched and checked on
that date; URLs are given so claims can be re-verified. Nothing here is
assumed from memory.*

*Updated 2026-11-01: AgriParam was downloaded and evaluated and is **not
integrated** (it failed the final accuracy criteria), so the professor's
mandatory AgriParam requirement is **unmet**. Its licence is **unresolved**.
The original planning text for AgriParam below is kept for the record and is
marked where it has been superseded; the translation section was updated to the
verified status. Evidence: `artifacts/agriparam_cpu_smoke_test.md`.*

## Hardware context

| Item | Value |
|---|---|
| CPU | Intel Core i5-12500H (12 cores, Alder Lake) |
| RAM | 16 GB |
| GPU | RTX 3050 Laptop, **4 GB VRAM** (~1.9 GB already used by desktop apps) |
| torch installed | **2.14.1+cpu** — CUDA build not installed; `torch.cuda.is_available() == False` |
| Disk free (project drive) | ~273 GB |
| OS | Windows 11; **WSL2 Ubuntu installed** (Ubuntu, WSL version 2) |
| MSVC build tools | **NOT installed** (vswhere found nothing) — native C/Cython extension builds will fail |
| HF token | none in environment on 2026-10-29; later stored in the gitignored `.env` for the gated IndicTrans2 downloads |

Decision: **CPU-only inference**, as the project spec requires. The GPU is not
used; this is deliberate and consistent with the installed CPU torch build.

---

## 1. BharatGen AgriParam — `bharatgenai/AgriParam`

Official model of the BharatGen initiative (MeitY-funded). Note: the correct
Hugging Face org is **`bharatgenai`** (an org literally named `BharatGen` /
`bharatgen` exists but is empty and unrelated).

| Property | Verified value |
|---|---|
| Repo | https://huggingface.co/bharatgenai/AgriParam |
| License | **UNRESOLVED.** The Hugging Face metadata field declares `apache-2.0`, but the repository ships no LICENSE file and the README's licence badge link did not resolve; the custom modeling file's header says MIT; the parent Param-1 model's README body says MIT but also carries research-only / not-for-production wording; the AgriParam page on AIKosh could not be read. These were recorded in the 2026-11-01 audit and not re-fetched when writing this note. Because the sources conflict, **this project makes no licensing claim for AgriParam.** |
| Gated? | **No** — public download, no token required |
| Architecture | `ParamBharatGenForCausalLM` (custom code → `trust_remote_code=True`) |
| Base model | `bharatgenai/Param-1-2.9B-Instruct` |
| Parameters | 2,860,664,832 (~2.9 B), stored **F32** |
| Weights size | 3 safetensors shards: 4.98 + 4.36 + 2.10 = **~11.45 GB** (tokenizer +35 MB) |
| Context length | 2048 positions |
| Languages | **en, hi only** — no Kannada (IndicTrans2 is required for Kannada, as the spec anticipates) |
| Prompt format | `<user> {question} <assistant>` or `<context> {evidence} <user> {question} <assistant>` — a native context/RAG mode that fits our pipeline |
| Generation (official example) | `max_new_tokens=300, do_sample=True, top_k=50, top_p=0.95, temperature=0.6` |
| Last modified | 2026-02-24 |
| Revision evaluated | `a6d42de79de39020e0e2f81d7c17663b9623a461`; the three LFS shards and `tokenizer.json` matched the Hub-reported SHA-256, and the small files matched their git blob SHA-1 |

### Outcome of the 2026-11-01 evaluation: downloaded, evaluated, NOT integrated

Official files only (no GGUF or other checkpoints) were downloaded to the
project cache and run in an isolated environment, CPU, bf16, with no change to
the application, `requirements.txt` or the production `.venv`.

| Question | Measured result |
|---|---|
| Does it load and generate on this machine? | Yes. bf16 load took about 8 to 10 s. Peak RSS 7.8 to 8.8 GB (higher than the ~5.7 GB weight-size estimate below), peak commit 11.6 to 12.1 GB, system free memory fell to 1.2 to 3.1 GB during runs |
| Does the default cache path work? | No. `generate(use_cache=True)` fails under transformers 4.57.1 with the pinned custom code (legacy tuple KV cache vs. the library's cache object). Nothing was patched; a manual tuple-cache loop around the unmodified `forward()` worked |
| Speed | Decode about 2.7 to 4.3 tokens/s; prefill about 5 to 7.5 prompt tokens/s. Answers took roughly 73 to 129 s with a single ~500 to 700-token passage and 226 to 443 s with ~1.2 to 1.5k tokens of evidence |
| Accuracy with real retrieved evidence | Poor: wrong irrigation interval and gypsum quantity, and a Hindi question answered in English with irrelevant text |
| Accuracy with only the gold passage (final diagnostic) | 0 of 3 English answers fully correct: soybean K2O and S stated as 25 kg instead of 40 kg; finger-millet row spacing stated as 10 cm instead of 22.5 to 30 cm; ratoon-sorghum irrigation incomplete. The Hindi answer was in Hindi but reversed the rule not to delay irrigation beyond 24 hours |
| Dtype / tokenizer / weights at fault? | No evidence of it. A streaming FP32 reference gave the same argmax as bf16, and the official prompt format was used without BOS |

**Decision:** the pre-set criteria (all three English answers correct, no
cross-topic recommendations, values and conditions preserved, meaningful
improvement) were not met, so AgriParam is **not integrated** and
experimentation was stopped. **The professor's mandatory AgriParam integration
requirement remains unmet.** Caveat: this is a small qualitative probe (3
English cases and 1 Hindi case, greedy decoding, one prompt format), not a
statistical evaluation. Full record: `artifacts/agriparam_cpu_smoke_test.md`.

### Hardware feasibility (pre-download planning estimate, 2026-10-29)

*Superseded where the 2026-11-01 measurements above differ (notably memory
and speed).*

- **GPU (4 GB): impossible** in F32 (11.45 GB) and even in fp16 (~5.7 GB >
  ~2 GB free VRAM). 8-bit would still be borderline with desktop apps using
  half the VRAM. → GPU excluded.
- **CPU F32**: ~11.5 GB weights + OS + Streamlit + embedding model risks
  paging on a 16 GB machine. → too risky as default.
- **CPU bf16/fp16 (chosen primary)**: ~5.7 GB weights, fits comfortably.
  Expect slow generation (rough estimate: well under 5 tokens/s), so answers
  must be short (`LLM_MAX_NEW_TOKENS=200`) and the UI must show progress.
- **Download**: ~11.5 GB (F32 shards) even when loading bf16; the project drive has space.

### Fallback (optional, needs approval — unofficial conversion; NOT used)

*Not downloaded, not evaluated, not used. Listed for the record only.*

`arunmcops/AgriParam-GGUF` (community quantization of the same weights,
licence as declared on its Hub page, not verified here, created 2026-09-29): F16 5.7 GB, Q8_0, Q6_K, Q5_K_M, **Q4_K_M
~1.9 GB**, Q3_K_M, Q2_K; llama architecture, same chat template. Runs on CPU
via llama.cpp / `llama-cpp-python` with much better token throughput —
useful for a live demo. **Caveat**: third-party conversion (not officially
published by BharatGen); must be disclosed in docs and the professor's
"prescribed model" requirement should be checked — the weights are AgriParam's.

### Risks (planning notes from 2026-10-29; outcome recorded above)

- Custom code (`modeling_parambharatgen.py`, Feb 2026) vs installed
  `transformers==5.20.2`: this was **never tested** under 5.20.2. All tests ran
  under transformers 4.57.1 in the isolated environment. The default KV-cache
  path failed there (see the outcome table).
- The official example sets `use_cache=False` (slower); the planned switch to
  `use_cache=True` could not be done with `generate()`, and the manual-cache
  workaround was not adopted.

---

## 2. AI4Bharat IndicTrans2 — translation (en ⇄ hi, en ⇄ kn)

| Property | Verified value |
|---|---|
| Official repo | https://github.com/AI4Bharat/IndicTrans2 (MIT license) |
| Paper | Gala et al., TMLR 2023 (arXiv:2305.16307) |
| Checkpoint license | **MIT** (repo license table: "Model checkpoints — MIT") |
| HF checkpoints (distilled, recommended) | `ai4bharat/indictrans2-en-indic-dist-200M` (274 M params, ~1.1 GB safetensors), `ai4bharat/indictrans2-indic-en-dist-200M` (~0.9 GB) |
| HF checkpoints (base, 1B) | `indictrans2-en-indic-1B`, `indictrans2-indic-en-1B`, `indictrans2-indic-indic-1B` — larger/slower; not chosen |
| Gated? | **Yes — `gated: auto`** for the distilled checkpoints. Requires a (free) HF account: accept the license on the model page, then set `HF_TOKEN` in `.env`. No manual review. |
| Languages | 22 scheduled Indic languages + English. **hin_Deva (Hindi)** and **kan_Knda (Kannada)** both supported, plus eng_Latn. |
| Custom code | Yes (`configuration_indictrans.py`, `modeling_indictrans.py`, `tokenization_indictrans.py`) → `trust_remote_code=True` |
| Official preprocessing | IndicTransToolkit's `IndicProcessor(inference=True)`; official package is not Windows-supported and includes a Cython extension |
| Project preprocessing | `src/indic_processor.py`, a pure-Python port of the official processor for use on Windows; its Python dependencies are pinned in `requirements.txt` |

### The Windows blocker (critical)

The official IndicTransToolkit README states verbatim:

> "A `Linux/MacOS` based environment (This toolkit is not meant/built/tested
> for `Windows` as of now.)"

Its `setup.py` compiles a **Cython extension**; this machine has no MSVC build
tools (vswhere found none). This blocks building the official package here.
The project's Python port does not import or require PyICU. PyICU/ICU should
not be described as a blocker for the project's three-language path. The port
uses IndicNLP's normalizers and `UnicodeIndicTransliterator`; for Hindi and
Kannada it transliterates through a Hindi intermediate representation, then
converts back to the requested Indic script. English follows its own path.

### Translation strategy for en/hi/kn (decision)

Hindi and Kannada use their native Devanagari and Kannada scripts at the
model boundary. The port does not use ICU or perform script unification, but
it does use IndicNLP's Unicode transliterator through a Hindi intermediate
for Indic-script preprocessing/postprocessing. The implemented port covers
the official processor's pipeline behavior. The translator wrapper is
implemented and real CPU inference has been verified (see the status list
below). The translation path requires:

1. Unicode/number normalization used by `IndicProcessor`
2. SentencePiece tokenization using the checkpoint's own `model.SRC` /
   `model.TGT` files
3. Correct language-tag handling (`eng_Latn`, `hin_Deva`, `kan_Knda`)

Implementation and verification status (updated 2026-11-01; items 1 to 3 were
first written on 2026-10-30):

1. `src/indic_processor.py` is implemented as a pure-Python port of the
   official `IndicProcessor`.
2. Differential verification against the official Cython processor in WSL2
   was previously recorded as 0 differences across 19 steps in five
   scenarios. Those differential checks were **not independently rerun in
   this documentation session**; see `tests/differential/` for the recorded
   artifacts.
3. `src/translator.py` is implemented and its routing/error behavior is
   covered by mocked tests. On 2026-10-30, both prescribed distilled
   checkpoints were downloaded to the project-local Hugging Face cache
   (`.cache/huggingface/hub/`, gitignored) and their safetensors hashes and
   tensor headers were verified. The translator sets `HF_MODULES_CACHE` to the
   project-local `.cache/huggingface/modules/` before importing Transformers.
   **Update:** the checkpoints' remote code does not load under the production
   `.venv` (transformers 5.20.2: `No module named 'transformers.onnx'`). It
   loads in the isolated `.venv-indic-test` (transformers 4.57.1, torch
   2.14.1+cpu), where real CPU inference succeeded for en to hi, en to kn,
   hi to en, kn to en, and hi to kn and kn to hi via an English pivot (the
   per-direction smoke-test and pivot-test logs were kept locally as
   development diagnostics and are not tracked in the repository).
   Inference must use `use_cache=False` because the modeling code fails with
   the default cache on that version. The application reaches it through a
   persistent worker (`src/translation_worker.py`, `src/translation_client.py`).
   Recreation notes: `docs/indictrans2_environment.md`. Translation *quality*
   has not been reviewed by a native speaker. The final evaluation (2026-11-01)
   scores English-side answer quality; it does not independently validate the
   Hindi/Kannada translation step itself. The 32 Hindi/Kannada questions were
   AI-written and manually reviewed but have not been validated by native
   speakers (see `evaluation/native_language_review.md`).
4. The official toolkit in a WSL2 sidecar remains a possible fallback if the
   port proves insufficient; it has not been implemented.

### Terminology/number preservation

The official IndicTrans2 README demonstrates preservation of digits and Latin
identifiers in its examples. Systematic validation of that behavior in this project has not been done as a
standalone translation check. The final evaluation (2026-11-01) includes a
must-preserve metric (numbers, units, Latin-script names in the answer) as a
reported measure; see `docs/evaluation_methodology.md` section on
terminology/number preservation and `docs/failure_remediation_20261101.md`
for the must-preserve miss list. This measure is applied to the English-side
answer for Hindi/Kannada (not the translated answer text) and does not
independently validate fertilizer quantities or unit preservation through
the translation step itself, which remains unvalidated.

---

## 3. Embeddings — `intfloat/multilingual-e5-small`

| Property | Verified value |
|---|---|
| Repo | https://huggingface.co/intfloat/multilingual-e5-small |
| License | **MIT** |
| Gated? | No |
| Size | 118 M params, ~470 MB |
| Languages | 100+ incl. **en, hi, kn** (Kannada present in the official language list; XLM-R backbone) |
| Usage requirement | Prefix inputs: `"query: ..."` and `"passage: ..."` (we must apply this consistently at index and query time) |
| Why | Explicit Kannada coverage + MIT + CPU-friendly + strong multilingual retrieval benchmarks |

Fallback: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
(Apache-2.0, ~470 MB) — **weaker Kannada coverage** (Kannada is absent from
its language tags), so it is second choice. Both were fetched from the HF API
on 2026-10-29 (license and language tags as listed there).

---

## 4. Decision summary

| Component | Choice | License | Size | Runs where |
|---|---|---|---|---|
| Domain LLM | `bharatgenai/AgriParam` (official): **evaluated, NOT integrated; professor's requirement unmet** | **Unresolved** (no claim made) | 11.45 GB dl; measured peak RSS 7.8 to 8.8 GB in bf16 | CPU (tested only) |
| LLM fallback (optional) | `arunmcops/AgriParam-GGUF` Q4_K_M: **not used** | Not verified (community conversion) | ~1.9 GB | CPU (llama.cpp) |
| Answer generation actually used | Deterministic extractive evidence (no model) | our code | — | CPU |
| Translation | `ai4bharat/indictrans2-{en-indic,indic-en}-dist-200M` | MIT (gated: auto → HF token) | ~2.0 GB total | CPU |
| Translation preprocessing | Pure-Python `IndicProcessor` port; prior WSL2 differential result recorded (not rerun in this session) | our code | — | CPU |
| Embeddings | `intfloat/multilingual-e5-small` | MIT | ~470 MB | CPU |
| Vector search | `faiss-cpu` 1.15.1 (installed) | MIT | — | CPU |
| PDFs | `pypdf` 6.21.4 (installed) | BSD | — | CPU |

## 5. Open items requiring user decisions

1. **HF token**: user must create a free HF account, accept the license on
   both gated IndicTrans2 model pages, and put the token in `.env`.
2. **AgriParam** — resolved 2026-11-01: downloaded (approved) and evaluated;
   not integrated because it failed the final accuracy criteria. The
   mandatory requirement remains unmet and is disclosed in the README and the
   report. Licence unresolved.
3. **GGUF acceleration** — closed: not pursued; AgriParam experimentation was
   stopped.
4. **transformers version** — resolved: production stays on 5.20.2; the
   IndicTrans2 checkpoints run in the isolated environment (4.57.1), as
   documented in `docs/indictrans2_environment.md`.
