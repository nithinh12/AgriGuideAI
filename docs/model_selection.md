# Model Selection — Verified Compatibility Report

*Compiled 2026-10-29 from official sources (Hugging Face API/model cards,
official GitHub repositories). Every fact below was fetched and checked on
that date; URLs are given so claims can be re-verified. Nothing here is
assumed from memory.*

## Hardware context

| Item | Value |
|---|---|
| CPU | Intel Core i5-12500H (12 cores, Alder Lake) |
| RAM | 16 GB |
| GPU | RTX 3050 Laptop, **4 GB VRAM** (~1.9 GB already used by desktop apps) |
| torch installed | **2.14.1+cpu** — CUDA build not installed; `torch.cuda.is_available() == False` |
| Disk free (D:) | ~273 GB |
| OS | Windows 11; **WSL2 Ubuntu installed** (Ubuntu, WSL version 2) |
| MSVC build tools | **NOT installed** (vswhere found nothing) — native C/Cython extension builds will fail |
| HF token | none in environment |

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
| License | **Apache-2.0** (model card + API `cardData.license`) |
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

### Hardware feasibility

- **GPU (4 GB): impossible** in F32 (11.45 GB) and even in fp16 (~5.7 GB >
  ~2 GB free VRAM). 8-bit would still be borderline with desktop apps using
  half the VRAM. → GPU excluded.
- **CPU F32**: ~11.5 GB weights + OS + Streamlit + embedding model risks
  paging on a 16 GB machine. → too risky as default.
- **CPU bf16/fp16 (chosen primary)**: ~5.7 GB weights, fits comfortably.
  Expect slow generation (rough estimate: well under 5 tokens/s), so answers
  must be short (`LLM_MAX_NEW_TOKENS=200`) and the UI must show progress.
- **Download**: ~11.5 GB (F32 shards) even when loading bf16; D: has space.

### Fallback (optional, needs approval — unofficial conversion)

`arunmcops/AgriParam-GGUF` (community quantization of the same weights,
Apache-2.0, created 2026-09-29): F16 5.7 GB, Q8_0, Q6_K, Q5_K_M, **Q4_K_M
~1.9 GB**, Q3_K_M, Q2_K; llama architecture, same chat template. Runs on CPU
via llama.cpp / `llama-cpp-python` with much better token throughput —
useful for a live demo. **Caveat**: third-party conversion (not officially
published by BharatGen); must be disclosed in docs and the professor's
"prescribed model" requirement should be checked — the weights are AgriParam's.

### Risks

- Custom code (`modeling_parambharatgen.py`, Feb 2026) vs installed
  `transformers==5.20.2`: expected to be compatible (recent update), but this
  is unverified until Phase 6. If it breaks, options are: upgrade/downgrade
  transformers within the constraints of IndicTransToolkit (>=4.51) and
  sentence-transformers, or vendor the modeling file.
- The official example sets `use_cache=False` (slower); we will use the KV
  cache (`use_cache=True`) after verifying output parity.

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
| Required preprocessing | **IndicTransToolkit** (`pip install indictranstoolkit`), `IndicProcessor(inference=True)` |
| Toolkit requirements | Python >=3.10 ✓, `numpy>=2.1` ✓ (2.2.6), `torch>=2.5` ✓ (2.14.1), `transformers>=4.51` ✓ (5.20.2) |

### The Windows blocker (critical)

The official IndicTransToolkit README states verbatim:

> "A `Linux/MacOS` based environment (This toolkit is not meant/built/tested
> for `Windows` as of now.)"

Additionally, its `setup.py` compiles a **Cython extension** and this machine
has **no MSVC build tools** (vswhere: nothing found), and its preprocessing
relies on ICU (`PyICU`), which has no Windows wheels and needs the ICU C++
SDK. Therefore **Windows-native installation of the official toolkit is
blocked**.

### Translation strategy for en/hi/kn (decision)

Hindi and Kannada use Devanagari and Kannada scripts natively; **no script
unification or ICU transliteration is needed for our three languages** (those
steps exist for Kashmiri/Sindhi/Manipuri variants). What we do need from the
official pipeline:

1. Unicode/number normalization used by `IndicProcessor`
2. SentencePiece tokenization using the checkpoint's own `model.SRC` /
   `model.TGT` files
3. Correct language-tag handling (`eng_Latn`, `hin_Deva`, `kan_Knda`)

Fallback ladder (each step verified before the next):

1. **Primary**: a small Windows-native preprocessing module
   (`src/translator.py`) that reuses the **official checkpoint tokenizers**
   and replicates the inference-path normalization for the three required
   languages only. Transparent, documented, and unit-tested (round-trip +
   numbers/units preservation tests).
2. **Verification**: compare shim outputs against the official
   `IndicProcessor` running inside the installed **WSL2 Ubuntu** on a sample
   set; record agreement in the docs.
3. **Fallback**: if the shim proves inaccurate, run the official toolkit in a
   small WSL2 sidecar service (FastAPI on localhost) while the main app stays
   on Windows.
4. **Not chosen**: installing MSVC Build Tools + ICU SDK + PyICU just to
   compile the toolkit (time-heavy, brittle, against the "reliability over
   complexity" priority).

### Terminology/number preservation

IndicTrans2's own tokenizer/normalizer already preserves digits and Latin
identifiers (demonstrated in the official README example: phone numbers,
dates, emails survive translation). We add automated checks that fertilizer
quantities, units (kg/ha, mm, litres), and crop names survive en→hi→en and
en→kn→en round trips (see `docs/evaluation_methodology.md`).

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
| Domain LLM | `bharatgenai/AgriParam` (official) | Apache-2.0 | 11.45 GB dl / ~5.7 GB in RAM (bf16) | CPU |
| LLM fallback (optional) | `arunmcops/AgriParam-GGUF` Q4_K_M | Apache-2.0 (community conversion) | ~1.9 GB | CPU (llama.cpp) |
| Translation | `ai4bharat/indictrans2-{en-indic,indic-en}-dist-200M` | MIT (gated: auto → HF token) | ~2.0 GB total | CPU |
| Translation preprocessing | Windows shim + WSL2 verification (fallback: WSL sidecar) | our code | — | CPU |
| Embeddings | `intfloat/multilingual-e5-small` | MIT | ~470 MB | CPU |
| Vector search | `faiss-cpu` 1.15.1 (installed) | MIT | — | CPU |
| PDFs | `pypdf` 6.21.4 (installed) | BSD | — | CPU |

## 5. Open items requiring user decisions

1. **HF token**: user must create a free HF account, accept the license on
   both gated IndicTrans2 model pages, and put the token in `.env`.
2. **AgriParam download timing**: 11.45 GB — approve now or after the RAG
   core works (recommended: later; the pipeline can be built and tested with
   a stub generator first).
3. **GGUF acceleration**: approve or reject the unofficial quantized
   fallback for demo responsiveness.
4. **transformers version**: keep 5.20.2 for now; revisit only if the
   AgriParam/IndicTrans2 custom code fails at load time (Phase 6).
