# AgriParam CPU smoke test

Date: 2026-11-01. Scope: download, isolated CPU bf16 load, minimal generation. **No application code, requirements, tests, configuration or production `.venv` were touched. No integration was attempted.**

## FINAL (section 11, gold-chunk-only diagnostic): STOP. AgriParam remains an unmet requirement

With only the gold evidence supplied, 0 of 3 English answers were fully correct (soybean K2O and S rates wrong; finger-millet row spacing wrong; ratoon irrigation incomplete), 1 improved and 2 got worse versus the previous run, and the Hindi answer reversed the 24-hour irrigation rule. Pre-set criteria not met; no further AgriParam experiments were run. Recommendation: focus the remaining time on the working RAG + IndicTrans2 application and submission materials. Details: section 11.

## SUPERSEDED: earlier recommendation (section 10, realistic RAG evidence): NOT YET SUITABLE for controlled integration testing

> **SUPERSEDED by the FINAL STOP verdict above (section 11).** Kept unchanged below as the historical record of what was found at that point; it is not the current recommendation.

With real retrieved evidence in the official `<context>` format, outputs were wrong or off-topic in 3 of 5 greedy cases (including wrong irrigation and gypsum quantities), a Hindi question was answered in English with irrelevant text, and each answer took 4–7.5 minutes. Details and exact outputs: section 10.

## SUPERSEDED: verdict (smoke test, updated after the diagnosis in section 9): CONDITIONAL

> **SUPERSEDED by the FINAL STOP verdict above (section 11).** The CONDITIONAL verdict below was reached before the realistic-evidence test (section 10) and the gold-chunk-only diagnostic (section 11). Its findings and exact results are preserved unchanged as history; its point 3 ("the `<context>` prompt was not tested") has since been tested, and the outcome was negative. The current verdict is STOP.

The model downloads, verifies, loads and generates on CPU in bf16. **The earlier incoherent output is explained and is not an implementation, dtype, tokenizer or loading defect** (section 9): it came from greedy decoding on a near-tied first-token distribution for the single rice prompt I used, plus an invalid BOS-prepended diagnostic. In the follow-up tests, 5 of 7 decodes were coherent English or Hindi (my judgement of coherence only; factual correctness was **not** evaluated).

It is not a PASS because:

1. **`generate(use_cache=True)` still fails** with the pinned official code under transformers 4.57.1. The cause is understood (section 9.3). No patch was applied. Cached decoding works only through a manual loop around the unmodified `forward()`.
2. **Robustness is limited:** 2 of the 4 rice-prompt decodes (greedy and one sampled seed) fell into a wrong-language branch (Luganda) and one looped.
3. **The evidence-grounded `<context>` prompt, which is the one a RAG integration would use, was not tested.**
4. **Memory is tight:** peak RSS 7.8 GB, peak commit 11.6 GB, and the system ran at 80–82% load with only 2.8–3.1 GB free during generation.
5. Licence remains unresolved (no claim made).

Not a FAIL, because it loads, runs and produces coherent text in most tested cases.

Original smoke-test verdict, now superseded (first by the section 9 update, and finally by the section 11 STOP verdict): CONDITIONAL, with the incoherent output listed as unresolved.

Legend: **[M]** measured here, **[V]** verified against a repository-provided value, **[I]** inference from code or traceback, **[U]** unresolved or not tested.

## 1. Pinned revision and provenance

- Repository: `bharatgenai/AgriParam` (official BharatGen org). Resolved via the Hugging Face API from `main` on 2026-11-01. **[V]**
- Immutable commit SHA used for every download and for the test: `a6d42de79de39020e0e2f81d7c17663b9623a461` (last modified 2026-02-24T09:30:13Z).
- No community GGUF, other checkpoints or optional files were downloaded. `README.md` and `.gitattributes` were not downloaded (not needed for inference).
- Cache location: project-local HuggingFace hub cache (`.cache/huggingface/hub/`). Weights were not converted or overwritten; bf16 conversion happens in memory only.

## 2. Files, sizes and SHA-256

Size and SHA-256 of the three LFS files and `tokenizer.json` match the hub-reported LFS SHA-256 **[V]**. For the remaining small files the hub provides only a git blob SHA-1; all five matched `git hash-object` **[V]**. The SHA-256 shown for those is computed locally **[M]** and has no upstream counterpart to compare against.

| File | Bytes | SHA-256 | Check |
|---|---:|---|---|
| model-00001-of-00003.safetensors | 4,983,075,736 | `516418978dd7faf9c8d3abb5596ffdb093ce3958f6e99e71be2e9b3fb7e0b166` | hub SHA-256 match |
| model-00002-of-00003.safetensors | 4,362,432,144 | `decd1fd962f4348944ee22c515bb7341524ce993ab48f93c7f59d913382de3a5` | hub SHA-256 match |
| model-00003-of-00003.safetensors | 2,097,184,896 | `26fb0f7ff2cb9ab82db532831745be46659456a1e290edbc4ba5b36a8065096c` | hub SHA-256 match |
| tokenizer.json | 34,810,459 | `6d48e9bac8d8da08e05700059356583e3d9106a5976c697504a5db20008dc2ba` | hub SHA-256 match |
| modeling_parambharatgen.py | 47,532 | `4745b5bc5596aa906ce880c14d15bdc3197cd04337e7685ebbed4d4f9ea719b5` | git blob `d750495…` match |
| config_parambharatgen.py | 1,964 | `9d89451dabb06aa289b35d48fc24bc8d0818d48fe51cad80c5d21df95abed3eb` | git blob `391f3ff…` match |
| tokenizer_config.json | 180,685 | `c54dbcecef0378531646407d0a201d92e4ff5e95173691601594acb6de450e42` | git blob `8ac7178…` match |
| model.safetensors.index.json | 23,986 | `4bf89e37a0965f822f6b8a9b8fa561d53b69b22c5ad1b7c51ec4588093cd92fe` | git blob `5a9a8ed…` match |
| config.json | 850 | `7c241bb8fa85c45a8d0aa175b2f98afd4383c2873bac1ccfc7ec9021437709b0` | git blob `891e090…` match |
| special_tokens_map.json | 913 | `bb8c877c40315b1634a99505d171efa72c63be6dc265a07a58f31196eaece715` | git blob `655e664…` match |
| generation_config.json | 111 | `eb67fce3f3ac3e7d4b88e5ac550b7168eda8b79370dd48bd933b07e3044307ed` | git blob `0f66086…` match |

Total downloaded: 11,477,759,276 bytes (11,442,692,776 weights + 35,066,500 other).

## 3. Custom-code security review (before `trust_remote_code=True`)

I read the pinned `config_parambharatgen.py` in full and `modeling_parambharatgen.py` in full (1,037 lines), after verifying their hashes. Findings:

- Imports are limited to `math`, `typing`, `torch` and `transformers` modules, plus a relative import of the config file.
- No network access, subprocess, `os`/`sys` use, file reads or writes, `eval`/`exec`/`compile`, `pickle`/`torch.load`, `importlib` or `ctypes`. A grep for those patterns was clean and a manual read agrees.
- Import-time side effects: `ParamBharatGenConfig.register_for_auto_class()` and two `AutoModel*.register(...)` calls, which add entries to transformers' registries.
- The code is Llama-derived with an eager attention path, legacy tuple KV cache and a header stating "Licensed under the MIT License". Its source link points at a third-party GitHub mirror rather than upstream transformers.
- **Security concerns: none found.** This is a code-reading conclusion, not a guarantee.

## 4. Environment

Used the existing `.venv-indic-test` interpreter **without installing, updating or removing anything** **[M]**. No dedicated `.venv-agriparam` was needed. Production `.venv` was not run.

| Component | Version |
|---|---|
| Python | 3.10.11 |
| PyTorch | 2.14.1+cpu (`cuda.is_available() == False`; 12 threads) |
| transformers | 4.57.1 |
| tokenizers / safetensors | 0.22.2 / 0.8.0 |

Side effect: transformers copied the remote code to the project-local HuggingFace modules cache (`.cache/huggingface/modules/transformers_modules/a6d42de…/`). The test ran offline (`HF_HUB_OFFLINE=1`) with credential-like variables removed from the environment. No other model process (IndicTrans2 worker, Streamlit) was running.

**Not tested:** production `.venv` (transformers 5.20.2). By static reading, 5.20.2's `cache_utils.py` has no `DynamicCache.__getitem__` and no legacy-cache conversion **[I]**, so tuple-cache code is not expected to work there. This was not run and the production environment was not touched.

## 5. Load and generation results

Setup: `AutoModelForCausalLM.from_pretrained(<pinned snapshot>, trust_remote_code=True, torch_dtype=torch.bfloat16, low_cpu_mem_usage=True)`, CPU, greedy decoding, seed 42, `max_new_tokens=64`. The whole test was run twice (run 1 and run 2) and was fully repeatable.

| Item | Result |
|---|---|
| Load | **Success.** 10.4 s (run 1), 9.4 s (run 2) **[M]**. No missing or unexpected-weight warnings in the log. |
| Parameters | 2,860,664,832, all `torch.bfloat16` on `cpu` **[M]** |
| Model class | `ParamBharatGenForCausalLM`; `GenerationMixin` was added by transformers' auto-class shim, so `generate()` exists **[M]** |
| Tokenizer | `PreTrainedTokenizerFast`. The tokenizer adds no BOS, so the prompt starts with `<user>` (id 256001) **[M]** |
| Prompt | `<user> Name two common insect pests of rice. <assistant>` (11 tokens) |

### `use_cache=True`: **FAILS** (both runs, ~0.05–0.09 s)

```
modeling_parambharatgen.py, line 658, in forward
    past_key_values_length = past_key_values[0][0].shape[2]
AttributeError: 'NoneType' object has no attribute 'shape'
```

Interpretation **[I]**: `generate()` passes an empty `DynamicCache`. The model treats any non-`None` `past_key_values` as a legacy tuple of tensors and indexes it, and the empty cache's first layer returns `None`. This matches the official README example setting `use_cache=False`.

### `use_cache=False`: **works mechanically**

| Run | Prompt | Tokens | Seconds | Tokens/s | Stopped |
|---|---|---:|---:|---:|---|
| 1 | primary | 12 | 28.0 | 0.43 | EOS |
| 2 | primary | 12 | 30.1 | 0.40 | EOS (identical output and token ids to run 1) |
| 2 | diagnostic: BOS `<s>` prepended | 40 | 169.7 | 0.24 | length limit |

First step (prefill plus 1 token) was about 2.1 s. Per-token time stays near 2.3 s even for a short context, and falls to 0.24 tokens/s at 40 tokens as the uncached sequence recomputation grows **[M]**. These are **cache-off numbers under memory pressure** and must not be taken as the achievable cached speed.

**Generated output (verbatim):**
- Primary prompt: `Ebiwuka ebiyitibwa rice ` (12 tokens, ids `252342, 4619, 252323, 10326, 1309, 4619, 203446, 1498, 3537, 11808, 252303, 3`)
- BOS-prepended diagnostic: `.).).).).).).).).).).).).).).).).).).).).).).).).).).).).).).).).).).).).). (` (a repetition loop)

**Neither output is a coherent answer** to an English agriculture question. An answer such as stem borer or brown planthopper would be expected from a working model; I did not independently confirm that expectation.

### Diagnostic checks on the incoherence (partial)

- RoPE tables (non-persistent buffers created in `__init__`): recomputed and compared in all 32 layers. `inv_freq` is identical to the config-derived values (max diff 0.0). The cos/sin cache is stored in bf16, with max abs difference 0.00195 from fp32 **[M]**. This is minor precision loss, and the buffers are not corrupted.
- Weights: embeddings, `lm_head`, a sample attention projection and the final norm are finite with plausible statistics (e.g. embedding std 0.0087, final-norm mean 2.46) **[M]**.
- **Not tested [U]:** sampling with the official parameters (temperature 0.6, top-p 0.95), the `<context>` RAG prompt format, a Hindi prompt, an fp32 reference run (needs about 11.4 GB), and a cache-compatible forward. The root cause of the incoherent output is **not identified**. Candidates not excluded: bf16 numerics, a model-code or transformers-version interaction, the prompt format, or the model's own behaviour with a very short generic prompt.

## 6. Memory and resource behaviour

| Measure | Value |
|---|---|
| Total RAM / available before load | 15.69 GB / 8.12 GB (run 2) **[M]** |
| **Peak working set (RSS)** | **7.86 GB** (run 2) **[M]** |
| **Peak commit (private bytes)** | **11.57 GB**, during F32-to-bf16 load conversion **[M]** |
| Resident RSS after load / after generation | 3.02 GB / 4.40–4.47 GB (working set trimmed by the OS under pressure) **[M]** |
| System available memory | 8.12 GB before, 3.28 GB after load, 2.13 GB after generation (memory load 48% to 86%) **[M]** |
| Page faults | about 4.45 M after load, about 5.74 M by the end of run 2 **[M]** |
| Run 1 | available memory fell to 0.86 GB (94% load). Process RSS was not captured in run 1 (my ctypes call was faulty; fixed for run 2) |

No crash and no out-of-memory error occurred. However, the system ran close to its limit with only the browser and ordinary apps open. When I first checked, a game was holding about 7 GB private memory and only about 1.9 GB was available, so the load was delayed until the game had closed. Whether the observed slowness is partly paging was not separately measured **[U]**.

A bf16 AgriParam load is therefore only viable with other large applications closed, and probably not alongside the IndicTrans2 worker.

## 7. Resolved, open and not done

**Resolved**
- Official weights are obtainable, integrity-checked and loadable on CPU in bf16 within 16 GB when other apps are closed.
- Custom code reviewed, with no security concerns found.
- `.venv-indic-test` (transformers 4.57.1) is sufficient to load the model; no new environment was required.
- `use_cache=True` is **not** compatible out of the box with the pinned code under 4.57.1.

**Open**
- ~~Incoherent output (section 5): root cause unknown.~~ **Explained in section 9**; not a code, dtype or tokenizer defect.
- `generate(use_cache=True)` remains incompatible. A manual tuple-cache loop works (section 9.3) but has not been turned into an integration approach. Speeds with that loop are measured on short contexts only; latency with a long RAG prompt is unmeasured.
- Production `.venv` (transformers 5.20.2) untested.
- Licence: **unresolved, and no licensing claim is made in this report**. The upstream repository has no LICENSE file and the sources conflict (the earlier audit's findings were not saved as a file; they are recorded in `docs/model_selection.md` and `docs/third_party_licenses.md`).

**Not done (out of scope or deliberately skipped):** performance optimisation, quantization, GPU use, integration with `RAGPipeline`, any change to `src/`, `app/`, `tests/`, `requirements.txt` or existing configuration, and any Git commit. Working-tree status was checked after the runs and is unchanged from the start of the session.

Scripts and raw result JSON for these runs (`smoke.py`, `smoke_result_run1.json`, `smoke_result_run2.json`, `diag_rope.py`, `diag_rope.json`) were saved to the Claude session scratchpad (temporary directory; not retained in the repository).

## 8. Suggested next steps (for your review, not started)

1. ~~Investigate the incoherent output~~ Done (section 9).
2. Decide how to handle the KV cache (see 9.3): your decision is needed.
3. Test the `<context>` evidence prompt on a few short RAG-style cases, in the same memory-aware way, before any integration decision.

## 9. Generation-correctness diagnosis (follow-up)

Scope kept as instructed: same pinned checkpoint, same `.venv-indic-test` (no installs), CPU only, one model instance at a time, upstream model files not patched, production `.venv` and the application untouched. The only new download was `README.md` (11,716 bytes, git blob `861299e…` matches the hub), needed to read the official example. Scripts and raw JSON are in the session scratchpad (paths at the end).

### 9.1 Official prompt format vs what I used

| Item | Official README (pinned revision) | Smoke test | Match |
|---|---|---|---|
| Prompt | `<user> {question} <assistant>`; with evidence `<context> {ctx} <user> {question} <assistant>` | `<user> Name two common insect pests of rice. <assistant>` | Yes |
| Tokenizer | `AutoTokenizer.from_pretrained(..., trust_remote_code=False)`; `tokenizer(prompt)` with no extra tokens | same | Yes |
| BOS | none added | none added | Yes |
| Chat template | `<user> {content} <assistant>` | `apply_chat_template` output identical to the manual prompt; ids identical **[M]** | Yes |
| Sampling | `do_sample=True, top_k=50, top_p=0.95, temperature=0.6, max_new_tokens=300, use_cache=False` | greedy, 64 tokens | **No** (greedy) |
| dtype | `bfloat16 if cuda else torch.bfloat32` | bf16 on CPU | The README's CPU branch is not usable: `torch.bfloat32` does not exist **[I]**, so the authors' CPU path was never exercised |

Tokenizer facts **[M]**: `PreTrainedTokenizerFast`; `len(tok)=256004` (matches `config.vocab_size=256004`); BPE with Metaspace pre-tokenizer, no post-processor (nothing is added automatically); special ids 0 `<pad>`, 2 `<s>` (BOS), 3 `</s>` (EOS, also the pad token), 256000–256003 `<context>`, `<user>`, `<assistant>`, `<system_prompt>`. Prompt tokens: `<user> ▁Name ▁two ▁common ▁insect ▁pests ▁of ▁rice . ▁ <assistant>`; decode round-trips exactly. `generation_config.json` only sets BOS 2 / EOS 3 (no sampling defaults). The checkpoint's 291 tensor names match the model's expected parameter names exactly (none missing or unexpected) **[M]**.

### 9.2 Is it dtype or an implementation defect? Evidence says no

**Plain-English sanity (bf16, single forward pass, no generation) [M]:**

| Test | Result |
|---|---|
| NLL of "The capital of France is Paris, and it is famous for the Eiffel Tower." (no BOS) | 3.52 nats (perplexity 33.8; uniform would be 12.45) |
| Same with BOS prepended | **7.91 nats (perplexity 2,732)**, so BOS is out-of-distribution for this checkpoint and must not be prepended |
| "The capital of France is" next token | `located` 0.292, `the` 0.130, `referred` 0.108, `Paris` 0.065 |

**Greedy and sampled generations, via the manual tuple-cache harness (section 9.3) [M]. Coherence is my reading; factual accuracy was not evaluated:**

| Prompt | Decode | Output |
|---|---|---|
| `The capital of France is` (plain) | greedy, 32 tok | `located in Paris, which is also the capital of France.  What is the population of France? The population of France is approximately 12` |
| `<user> What is the capital of France? <assistant>` | greedy, 32 tok | `The capital of France is Paris. It is located in the north-eastern part of the country and serves as the political, cultural, and economic center of France` |
| same | official sampling, seed 1, 30 tok | `The capital of France is Paris. It is the largest city in France and serves as the country's political, cultural, and economic center. ` |
| `<user> धान की फसल में तना छेदक कीट का नियंत्रण कैसे करें? <assistant>` | greedy, 32 tok | `तना छेदक कीट को फेरोमोन जाल का उपयोग करके नियंत्रित किया जा सकता है, जो नर पतंगों को` |
| `<user> Name two common insect pests of rice. <assistant>` | greedy, 12 tok | `Ebiwuka ebiyitibwa rice ` (Luganda "insects that are called …", identical to the earlier run) |
| same | official sampling, seed 1, 40 tok | `Ebiwuka ebimera by’ebimera by’ebimera by’ebimera by’ebimera by’ebimera by’ebimera by’eb` (repetition loop) |
| same | official sampling, seed 2 | `stem borer and leafhopper ` |

**Why the rice prompt failed under greedy decoding.** The first-token distribution is nearly flat (entropy 5.6 nats) with `E` at 0.1515 and `stem` at 0.1423. Greedy picks `E`, which starts the Luganda branch. So the earlier "garbage" was model behaviour on that prompt plus decoding choice, not corruption.

**FP32 reference [M], run by streaming.** A full FP32 load (11.4 GB) was not safe on this machine, so I ran the model's own unmodified decoder-layer classes one layer at a time in FP32, reading the original F32 shards (no rounding), for the last-position logits of three prompts, and compared with bf16:

| Prompt | argmax equal | max abs logit diff | KL(fp32 to bf16) | fp32 top tokens |
|---|---|---|---|---|
| rice (official format) | yes | 0.336 | 0.0025 nats | `E` 0.1485, `stem` 0.1449 (same near-tie as bf16) |
| plain France | yes | 0.666 | 0.0076 nats | `located` 0.280, `the` 0.128, `referred` 0.119 |
| chat France | yes | 0.366 | 0.0017 nats | `The` 0.550, `Paris` 0.336 |

FP32 produces the same argmax and the same near-tie, so **bf16 precision is not the cause**. Limits: this checks one forward pass per prompt, not full FP32 generation. The reference uses the same upstream model code, so it cannot detect a defect in that code. It is consistent with the code being correct, because plain-text perplexity and chat answers are sensible.

**Conclusion on the root cause of the incoherent output:** a property of the model on that prompt, amplified by greedy decoding. It is not a bug in loading, tokenizer, RoPE, weights or dtype. The BOS-prepended "punctuation loop" came from my diagnostic prepending BOS, which the checkpoint was not trained for (perplexity 2,732 vs 33.8).

### 9.3 Why `use_cache=True` fails (cause established, not patched)

**[M]** `generate()` in transformers 4.57.1 builds `DynamicCache(config=model.config)`, which has **32 pre-allocated layers whose key/value tensors are `None`**, and `bool(cache)` is `True`. The model's forward (`modeling_parambharatgen.py` lines 657–658) does `if past_key_values is not None: past_key_values_length = past_key_values[0][0].shape[2]`, written for a legacy tuple of tensors, so it dereferences `None`. I reproduced the identical `AttributeError: 'NoneType' object has no attribute 'shape'` by calling `forward()` with an empty `DynamicCache(config=...)` directly.

**The model's own tuple-cache path works [M]:** a manual loop that calls the unmodified `forward()` with `use_cache=True` and feeds the returned tuple back reproduced the earlier cache-off greedy output exactly (all 12 token ids identical) and is much faster. This loop is a test harness, not a model patch.

Options for your decision (none implemented):
1. Keep upstream files untouched and drive `forward()` with our own generation loop that uses the tuple cache (as the harness did). We would own sampling and stopping logic.
2. A small runtime adapter around the model that hands `forward()` `None` instead of an empty cache on the first step. This changes behaviour and needs your approval; its interaction with `generate()` is untested.
3. `use_cache=False` (official example). Works, but 0.2–0.4 tokens/s here and degrading as sequences grow.
4. The production `.venv` (transformers 5.20.2) was not tested. By static reading it has no tuple-indexing support on `DynamicCache`, so the same model code is expected to fail there too. Not run.

### 9.4 Memory and speed measurements (this follow-up)

| Measure | Value |
|---|---|
| bf16 load | 9.7 s; peak RSS 7.79 GB; peak commit 11.57 GB; steady RSS 4.4–4.5 GB **[M]** |
| System during bf16 generation | 2.8–3.1 GB available, 80–82% memory load **[M]** |
| Manual tuple-cache speed (short contexts, 12 threads, memory-pressured) | 12 tokens in 4.48 s = 2.68 tok/s (prefill of 11 tokens: 1.61 s); greedy 32-token runs 2.79–3.63 tok/s; sampled 2.35–3.36 tok/s **[M]** |
| Earlier cache-off speed | 0.2–0.4 tok/s **[M]** (section 5) |
| Long-prompt (RAG-sized) latency | **Not measured**; do not extrapolate from the short-context figures |
| FP32 streaming run | peak RSS **8.43 GB**, peak commit **13.87 GB**, system available fell to **0.45 GB (97% load)**. I had expected only a few GB; the memory-mapped shard pages stayed in the working set. It finished without a crash. I would not repeat it without closing other applications **[M]** |

### 9.5 Remaining items

- Cache decision (9.3) needs your direction.
- `<context>` (evidence) prompt format, abstention behaviour and groundedness: untested.
- Robustness: 2 of 4 rice decodes were degenerate. Behaviour across a realistic question set is unknown; no evaluation was run.
- Production `.venv` untested.
- Licence unresolved; no licensing claim made.

Scratchpad files (Claude session scratchpad; temporary, not retained): `tokinspect.py`, `diag2_bf16.py` / `diag2_bf16.json` / `logits_bf16.npz`, `diag3_fp32_stream.py` / `diag3_fp32.json`.

## 10. Test with realistic RAG evidence (official `<context>` prompt)

**Recommendation from this section: NOT YET SUITABLE for controlled integration testing.** See 10.7.

### 10.1 Method (all measured on the machine; nothing integrated)

- **Evidence source:** the existing, unmodified retrieval and gate (`build_pipeline()` from `app/bootstrap.py`, run read-only with the production interpreter and `PYTHONDONTWRITEBYTECODE=1`; no code or config changed, no retrieval tuning). It ran in its own process and exited before AgriParam loaded, so no two model processes ever coexisted. The same retrieval step as `RAGPipeline.answer()` was used: `search(top_k*20)`, then `relevant_evidence`, then the first 5 passages.
- **Cases:** three answerable English questions from `evaluation/test_cases.jsonl` whose gold chunk is in the retrieved set (`en_fert_02`, `en_irrig_02`, `en_crop_02`), the dataset's Hindi wording of one of them (`hi_irrig_02`), and one extra case (`en_fert_01`, explained in 10.3). Other candidates were screened out because the existing pipeline did not retrieve the gold chunk (`en_crop_03`) or abstained (`en_irrig_03`); no unsupported question was sent to the model.
- **Prompt:** exactly `<context> {evidence} <user> {question} <assistant>`, no BOS (asserted in code). Evidence = whole retrieved passages in rank order, whitespace-collapsed (no content change), up to a **1,500-token evidence budget** so prompt + 120 new tokens fit the 2,048 context. Passages beyond the budget were dropped (listed below).
- **Generation:** manual tuple-cache loop around the unmodified `forward()` (section 9.3), bf16, CPU, greedy (deterministic), `max_new_tokens=120`. One sampled run (official T=0.6, top-k 50, top-p 0.95, seed 1) for each core English case. bf16 model, one instance, 7.9 GB available at start; the script aborts if memory falls below 0.8 GB (it never did).

### 10.2 Retrieved evidence per case (exact chunk ids; full text is in the scratchpad JSON `rag_evidence.json`)

| Case | Question | Passages in prompt (rank order) | Dropped for budget | Prompt tokens |
|---|---|---|---|---|
| A `en_fert_02` | What basal fertilizer nutrients and quantities are recommended per hectare for soybean? | `tnau_agriculture::p112::c109`, `::p186::c183` (gold) | p372, p399, SOP p12 | 1,407 |
| B `en_irrig_02` | How should a ratoon sorghum crop be irrigated after the main crop is cut? | `tnau_agriculture::p85::c82` (gold), `tnau_horticulture::p271::c271`, `tnau_horticulture::p82::c80`, `tnau_agriculture::p319::c322` | `tnau_horticulture::p130::c128` | 1,463 |
| C `en_crop_02` | What seed rate and row spacing are recommended for line sowing of finger millet? | `tnau_agriculture::p111::c108` (gold), `::p112::c109` | p103, p281, p197 | 1,175 |
| H `hi_irrig_02` | मुख्य फसल की कटाई के बाद रैटून ज्वार की सिंचाई कैसे करनी चाहिए? | same English evidence as B | same as B | 1,472 |
| X `en_fert_01` (extra) | How much gypsum should be applied to groundnut, and when? | `tnau_agriculture::p199::c196`, `::p197::c194` | none | 1,276 |

Key sentences actually present in the supplied evidence **[M]**:
- A: "Apply 20 kg N and 80 kg P2O5 and 40 kg K2O per ha 40 kg of S as gypsum (220 kg/ha) as basal dressing. Soil application of 25 kg ZnSO4, 25 kg MnSO4/ha under irrigated condition if the soil is deficient."
- B: "Irrigate immediately after cutting the main crop. Irrigation should not be delayed for more than 24 hours after cutting. Irrigate on 3rd or 4th day after cutting. Subsequently irrigate once in 7 - 10 days. Stop irrigation on 70 - 80 days after ratooning." The horticulture passages in the same prompt (jasmine) also say "Pick the flowers from 3rd month onwards at 4 days interval".
- C: "Line sowing is ideal and seed drills giving spacing of 22.5 – 30 cm between rows should be used. Finger millet seeds are very small (400 seeds/g) and the recommended seed rate is 10 kg/ha." Also: "A plant population of 4 – 5 lakhs per ha is optimum".
- X: "Gypsum 400 kg/ha as soil application at 45th day after sowing" and "80 kg S as gypsum on 45 DAS"; "Zinc deficiency: Apply 25 kg ZnSO4/ha as basal".

### 10.3 Note on case X

I first labelled X a retrieval miss because the retrieved chunks (p197, p199) are not the gold chunk (p203). Inspecting the text shows the **answer is present in the supplied evidence** (400 kg/ha at 45th day after sowing); the same advice appears on several pages. The existing extractive pipeline **abstained** on this question even though the gate passed (the extractive generator found no usable sentences). With a generative model in the loop, passing the gate means the model *will* generate, so X shows what happens when the gate passes but the answer is buried in noisy passages.

### 10.4 Exact outputs and groundedness (my reading against the supplied evidence)

"Number found in evidence" is **not** a safe check: for every run below, every number in the output appears somewhere in the evidence, yet several answers are wrong because numbers are misattributed.

| Run | Exact output | Assessment |
|---|---|---|
| **A** greedy | `For soybean, apply 20 kg N and 80 kg P 2 O5 and 40 kg K 2 O per hectare as basal dressing. If the soil is deficient, apply 25 kg ZnSO4 and 25 kg MnSO4/ha. ` | **Mostly grounded, incomplete.** N, P2O5, K2O figures match the evidence. Omits the sulphur/gypsum part ("40 kg of S as gypsum (220 kg/ha)"). Drops the qualifier "under irrigated condition" for the Zn/Mn dose. No invented numbers. |
| A sampled (seed 1) | `For soybean, apply 20 kg N and 80 kg P 2 O5 and 40 kg K 2 O per hectare as basal dressing. If the soil is deficient, apply 25 kg ZnSO4 + 25 kg MnSO4/ha. ` | Same as greedy. |
| **B** greedy | `In the main crop, irrigate on 3rd day after cutting the main crop. For ratoon crops, irrigate once at 4 days interval. ` | **Incorrect, and agronomically misleading.** Evidence: irrigate immediately after cutting, again on the 3rd or 4th day, then once in 7–10 days, stop at 70–80 days. The "4 days interval" is borrowed from the jasmine flower-picking sentence, not from irrigation. Misses "immediately", "7–10 days" and the stop date. |
| B sampled (seed 1) | `In the main crop, harvest the crop when the grains turn yellow. In the ratoon crop, harvest pick the flowers from 3rd month onwards at 4 days interval. ` | **Not an answer to the question.** Mixes the sorghum harvest sentence with the jasmine harvest sentence. |
| **C** greedy | `The optimum plant population for rainfed millet is 4 – 5 lakhs pe r ha. For line sowing, the recommended spacing is 22.5 – 30 cm between rows. ` | **Partially correct.** Row spacing is right. **Does not give the seed rate (10 kg/ha)**, which was half the question. States population as the answer instead. |
| C sampled (seed 1) | `The recommended seed rate is 100 pe r ha, and the optimum plant population is 4 – 5 lakhs pe r ha. Line sowing with seed drills gives better plant population and higher or lower population than the optimum. ` | **Contains a wrong figure:** "seed rate is 100 per ha" versus 10 kg/ha in the evidence (tenfold error, unit dropped). The last sentence also garbles "higher or lower population than the optimum will reduce the yield". |
| **H** greedy (Hindi question, English evidence) | `After harvesting, the main crop, harvest pick the flowers from 3rd month onwards at 4 days interval. Pick the flowers from 3rd month onwards at 4 days interval. ` | **Failed.** Answered in English, not Hindi, and the content is the irrelevant jasmine sentence, repeated. |
| **X** greedy | `Apply 25 kg gypsum per hectare as basal application for calcareous soil. When soil test shows less than 1.2 ppm of zinc, apply 25 kg ZnSO4 per hectare as basal. For zinc deficiency, apply 25 kg ZnSO4 per hectare as basal. ` | **Incorrect, unsafe dosage.** The evidence says gypsum 400 kg/ha at 45 days after sowing. The model states "25 kg gypsum per hectare as basal" (about 16 times lower and the wrong timing), borrows the ZnSO4 25 kg figure, and misapplies the "calcareous soil" qualifier from a sulphur sentence. The rest repeats the zinc sentence. Does not answer the question. |

Existing extractive baseline for the same questions (same retrieval, unmodified pipeline) **[M]**: C answered with the exact seed rate and spacing sentence (correct and complete); A led with the correct fertilizer sentence followed by unrelated effluent text; B returned an irrelevant ratoon note (a failure of the extractive path, too); X abstained.

### 10.5 Hindi result

One Hindi test only (`hi_irrig_02`, English evidence, Hindi question). The model replied in English with irrelevant content (above). This is a single case and does not establish general Hindi behaviour. The deployed app translates Hindi questions to English before retrieval and the answer back afterwards; AgriParam was **not** tested inside that flow, and the IndicTrans2 worker was not run.

### 10.6 Measured latency and resources

| Run | Prompt tokens | Prefill (s) | Prefill tok/s | Decode tok/s | Generated | Total (s) |
|---|---:|---:|---:|---:|---:|---:|
| A greedy | 1,407 | 420.1 | 3.3 | 2.56 | 60 | 443.5 |
| B greedy | 1,463 | 304.2 | 4.8 | 2.62 | 33 | 316.9 |
| C greedy | 1,175 | 214.7 | 5.5 | 2.99 | 41 | 228.4 |
| H greedy | 1,472 | 301.4 | 4.9 | 2.65 | 39 | 316.1 |
| X greedy | 1,276 | 239.1 | 5.3 | 2.85 | 61 | 260.5 |
| A sampled | 1,407 | 280.6 | 5.0 | 2.73 | 60 | 302.6 |
| B sampled | 1,463 | 296.5 | 4.9 | 2.66 | 37 | 310.4 |
| C sampled | 1,175 | 210.0 | 5.6 | 3.01 | 48 | 226.0 |

- **Every answer took 226–443 s (about 4–7.5 minutes)**, dominated by prefill of the ~1.2–1.5 k-token evidence prompt (about 5 prompt tokens/s). Decode is 2.6–3.0 tokens/s. The first run's longer prefill (420 s) may include warm-up and paging; this was not isolated.
- Cause of the slow prefill was **not diagnosed**. It is consistent with CPU bf16 matmuls without native bf16 support plus memory pressure **[I]**; FP32 compute was not tested (out of scope and not memory-safe).
- If prefill scales linearly with prompt length, a ~400-token evidence budget would cost roughly 80 s **[I, extrapolation; not measured]**.
- Memory: load peak RSS 7.82 GB, peak commit 12.1 GB, steady RSS 4.7 GB; system availability fell to a minimum of 1.22 GB (during the Hindi run), memory load 77–82%. No crash, no abort, and the safety stop (0.8 GB) was never reached.

### 10.7 Remaining limitations and final recommendation

- **Groundedness is not reliable even when the gold evidence is in the prompt.** Of the five greedy cases: 1 mostly grounded but incomplete (A), 1 partly correct (C), 3 wrong or off-topic (B, H, X). Two outputs state wrong agronomic quantities that a farmer could act on (B irrigation interval; X gypsum 25 versus 400 kg/ha), and one sampled output has a tenfold seed-rate error (C).
- **Distractor sensitivity:** noisy, multi-crop passages (horticulture flower-harvest text, effluent text) leaked into answers. The 1,500-token budget forces whole-passage evidence, which includes much off-topic text.
- **Greedy and sampled decodes disagree** on 2 of 3 core cases, so outputs are not stable.
- **No safe automatic check exists yet:** "every number appears in the evidence" passes all wrong answers above. A claim-level verifier would be needed.
- **The existing extractive path is currently better** on exactly the cases that matter for factual quantities (C) and safer on X (it abstained).
- Latency (minutes per answer) is far outside interactive use.
- Not tested: more cases, shorter or reranked evidence, prompt variants, the `<system_prompt>` token, multi-turn, the full Hindi/Kannada translation flow, production `.venv` (transformers 5.20.2), and any cache approach other than the manual loop. Statistical conclusions cannot be drawn from five cases; this is a small qualitative probe.
- Licence: unresolved. No licensing claim is made.

**Final recommendation: NOT YET SUITABLE for controlled integration testing.** The model loads and runs, but with realistic evidence it produced wrong dosage and schedule statements in some cases, answered a Hindi question in English with irrelevant content, and takes minutes per answer. Integration should not begin until (a) the speed problem has a concrete path (for example a much smaller evidence budget or a different compute dtype, tested separately), (b) a claim-level groundedness check or a constrained, quote-only generation approach exists, and (c) a larger offline evaluation with predefined criteria shows it beats the extractive baseline. Whether to continue with AgriParam as the prescribed model, and how to document this limitation for the professor, is your decision.

Scratchpad files (Claude session scratchpad; temporary, not retained): `rag_retrieve.py`, `rag_evidence.json` (exact retrieved passage text), `rag_gen.py`, `rag_gen.json` (exact prompts' evidence, outputs, timings).

## 11. Final minimal-context diagnostic (gold chunk only)

**Verdict: STOP.** The decision criteria were not met. Minimal context did **not** materially improve accuracy: it changed which errors appear. One case improved, two got worse, and the Hindi answer was in Hindi but reversed one safety-relevant statement. No further AgriParam experiments were run, per the stop condition.

### 11.1 Protocol (fixed in advance, no tuning)

- Time limit: 45 minutes. The first budget (13:36 to 14:21) lapsed while waiting for memory to be freed. At 14:35 you chose a fresh 45-minute budget; this run started at 14:36 and the generation finished at 14:42 (about 6 minutes), inside that budget.
- Same pinned checkpoint and `.venv-indic-test`, bf16 on CPU, same manual tuple-cache harness, **greedy**, `max_new_tokens=120`, no BOS (asserted in code). No downloads, installs, retrieval changes, or application changes.
- Only the gold chunk was supplied as context (taken verbatim from `data/processed/chunks.jsonl`, whitespace-collapsed exactly as in section 10, no truncation). Prompt: `<context> {gold chunk} <user> {question} <assistant>`. No other passages.

### 11.2 Exact evidence chunks used (as placed in the prompt)

**A. `tnau_agriculture::p186::c183`** (700 evidence tokens, prompt 718 tokens):
```
175 the field stand. 3. SEED TREATMENT WITH BIOFERTILIZER a) Treat the seeds atleast 24 hours before sowing. Treat the seeds with 3 packets (600 g/ha) of Rhizobial culture (COS-1) and 3 packets (600 g/ha) of Phosphobacteria deve loped at TNAU using rice kanji as binder. If the seed treatment is not carried out apply 10 packets of Rhizobium (2000 g/ha) and 10 packets (2000 g) of Phosphobacteria with 25 kg of FYM and 25 kg of soil before sowing. Dry the bacterial culture treated seeds in shade for 15 minutes before sowing. 4. FERTILIZER APPLICATION i) Apply 20 kg N and 80 kg P 2 O5 and 40 kg K 2 O per ha 40 kg of S as gypsum (220 kg/ha) as basal dressing. Soil application of 25 kg ZnSO 4, 25 kg MnSO4/ha under irrigated condition if the soil is deficient. ii) Foliar spray of NAA 40 mg/litre and Sa licylic acid 100 mg/litre once at pre- flowering and another at 15 days thereafter iii). Foliar spray of DAP 20 g/litre or urea 20 g/litre once at flowering and another at 15 days thereafter iv). Foliar spraying of 1% FeSO4 + 0.1% citric acid thrice at 7-10 days interval. 5. SOWING Dibble the seeds at a depth of 2 - 3 cm adopting a spacing of 30 x 5 cm. In Erode district, Soybean + Castor (60 cm apart) cropping system gives high net return. 6. WATER MANAGEMENT Irrigate immediately after sowing. Give life irrigation on 3 rd day. Further irrigation at intervals of 7 - 10 and 10 - 15 days during summer and wi nter season respectively to be given depending on soil and weather conditions. Soyabean is very sensitive to excess moisture and the crop is affected, if water stagnates in the fields. The crop should not suffer due to water stress from flowering to maturity. To alleviate moisture stress spray of either Kaolin 3% or liquid para ffin at 1% on the foliage. In Erode district cultivate Soybean + Castor with irrigation at 0.60 IW/CPE ratio (once in 10 to 12 days) is recommended. 7. WEED MANAGEMENT i) Pendimethalin 1.0 litre /ha after sowi ng followed by one hand weeding on 30 days after sowing. ii) If herbicide spray is not given two ha nd weedings on 20 and 35 days after sowing may be given. iii) Early Post emergence application of Imazythypur @ 50 g / ha may be applied as post emergence on 20 DAS with one hand weeding on 30 days after sowing. 8 HARVESTING Yellowing of leaves and shedding, indicate the maturity of the crop. Cut the entire plant when most of the pods have turned yellow, drying and processing.
```

**B and Hindi. `tnau_agriculture::p85::c82`** (463 evidence tokens; prompt 484 tokens in English, 493 with the Hindi question):
```
73 will mitigate the ill effects. V. HARVESTING AND PROCESSING i. Consider the average duration of the crop and observe the crop. When the crop matures the leaves turn yellow and present a dried up appearance. ii. The grains are hard and firm. iii. At this stage, harvest the crop by cutting the earheads separately. iv. Cut the stalk after a week, allow it to dry and then stack. v. In the case of tall varieties, cut the stem at 10 to 15 cm above ground level and afterwards separate the earheads and stack the stalk. vi. Dry the earheads. vii. Thresh using a mechanical thresher or by drawing a stone roller over the earheads or by using cattle and dry the produce and store. RATOON SORGHUM CROP 1. RATOONING TECHNIQUE i. Harvest the main crop leaving 15 cm stubbles. ii. Remove the first formed two sprouts from the main crop and allow only the later formed two sprouts to grow. Allow two tillers per hill. 2. HOEING AND WEEDING i. Remove the weeds immediately after harvest of the main crop. ii. Hoe and weed twice on 15th and 30th day after cutting. 3. APPLICATION OF FERTILIZERS i. Apply 100 kg N/ha in two split doses. ii. Apply the first dose on 15 th day after cutting and the second on 45 th day after cutting. iii. Apply 50 kg P2 O5 /ha along with the application of N on 45th day. 4. WATER MANAGEMENT i. Irrigate immediately after cutting the main crop. ii. Irrigation should not be delayed fo r more than 24 hours after cutting. iii. Irrigate on 3rd or 4th day after cutting. iv. Subsequently irrigate once in 7 - 10 days. v. Stop irrigation on 70 - 80 days after ratooning. 5. HARVEST Harvest the crop when the grains turn yellow. NOTE: The duration of the ratoon crop is about 15 days less than the main crop.
```

**C. `tnau_agriculture::p111::c108`** (466 evidence tokens, prompt 486 tokens):
```
99 Season Finger millet is grown in different seasons in different parts of the country. As a rainfed crop, it is normally sown in June- July in Tamil Nadu. I t a l s o g r o w n i n w i n t e r s e a s o n ( r a b i ) b y planting in September – October in Tamil Nadu and as a summer irrigated crop by planting January – February. Tillage Fall ploughing is advantageous for moisture conservation. I n the month of April or May, one deep ploughing with mould board plough followed by ploughing with wooden plough twice is necessary. Before sowing secondary tillage with cultivator and multiple tooth hoe to prepare smooth seed bed is necessary. Seed rate and planting A plant population of 4 – 5 lakhs pe r ha is optimum for getting higher yields and higher or lower population than the optimum will reduce the yield. Line sowing is ideal and seed drills giving spacing of 22.5 – 30 cm between rows should be used. Finger millet seeds are very small (400 seeds/g) and the recommended seed rate is 10 kg/ha. Therefore, even when seed drill is used thinning within the row leaving a spacing of 7.5 – 10 cm between plants, must be followed. Sowing by seed-cum-fertilizer drill is advant ageous for line sowing besides efficient utilization of applied nutrients. Maintenance of optimum plant population is an important prerequisite for getting higher yield under rainfed conditions. Poor germination, often, is the result of inadequate moisture after sowing in low rainfall areas. Under these conditions, the adoption of a simple technique like seed hardening will not only improve germination and subsequent plant stand but also impart early seedling vigour and tolerance to drought. The procedure of seed hardening technique is as follows. 1. Sole seeds in water for 6 hours. Use one litre water for every kg seed for soaking. 2. Drain the water and keep the seeds in wet cloth bag tightly tied for two days. 3. At this stage, the seeds will show initial signs of germination. 4. Remove seeds from the wet cloth bag and dry them in shade on a dry cloth for 2 days. 5. Use the above hardened seeds for sowing.
```

The questions were the dataset wording: A "What basal fertilizer nutrients and quantities are recommended per hectare for soybean?", B "How should a ratoon sorghum crop be irrigated after the main crop is cut?", C "What seed rate and row spacing are recommended for line sowing of finger millet?", Hindi "मुख्य फसल की कटाई के बाद रैटून ज्वार की सिंचाई कैसे करनी चाहिए?".

### 11.3 Exact outputs and per-case accuracy

Numbers were checked against their crop, recommendation, unit and timing, not just for presence in the chunk.

**A. Soybean basal nutrients: INCORRECT (worse than before).**
Output: `The recommended basal dressing is 20 kg N and 80 kg P2O5 per hectare, along with 25 kg K2O. Additionally, 25 kg S is applied as gypsum (220 kg/ha) under irrigated conditions if the soil is deficient. `
- Evidence: 20 kg N, 80 kg P2O5, **40** kg K2O, **40** kg S as gypsum (220 kg/ha), as basal dressing. Separately: 25 kg ZnSO4 and 25 kg MnSO4/ha "under irrigated condition if the soil is deficient".
- Wrong: K2O stated as 25 (should be 40); S stated as 25 (should be 40). Both wrong values are the Zn/Mn "25" attached to the wrong nutrient. The "irrigated condition / soil is deficient" qualifier is moved onto the gypsum, and the ZnSO4/MnSO4 recommendation is dropped. A fertilizer rate error of this kind is actionable.
- Correct: N 20 and P2O5 80, 220 kg/ha gypsum.

**B. Ratoon sorghum irrigation: INCOMPLETE, no wrong claim (improved).**
Output: `Irrigate immediately after cutting the main crop. Delay for more than 24 hours is not recommended. Subsequent irrigation should be done once every 7-10 days. `
- Correct: immediately after cutting; not delayed beyond 24 hours; every 7–10 days.
- Missing: the irrigation on the 3rd or 4th day after cutting (so the schedule reads as if the second irrigation is the 7–10 day one) and "stop irrigation on 70–80 days after ratooning". Both are required recommendations in the gold evidence.

**C. Finger millet seed rate and spacing: INCORRECT (worse than before).**
Output: `A plant population of 4–5 lakhs per hectare is optimal for higher yields. Line sowing should maintain a spacing of 7.5–10 cm between plants within the row and 10 cm between rows. `
- Evidence: seed drills giving **22.5–30 cm between rows**; recommended **seed rate 10 kg/ha**; thinning to 7.5–10 cm between plants; population 4–5 lakhs/ha.
- Wrong: "10 cm between rows" (should be 22.5–30 cm). The seed rate (10 kg/ha) is not stated at all, though it was half the question. The plant-spacing and population statements are supported.

**Hindi (same B evidence, original Hindi question): IN HINDI, but INCORRECT in one important point.**
Output: `सिंचाई को 7-10 दिनों के अंतराल पर बनाए रखना चाहिए, लेकिन 24 घंटे से अधिक समय तक पानी देने से बचना चाहिए। `
- Language: the response is entirely in Hindi (Devanagari). (My automated "Devanagari letter ratio" printed 1.617 because `isalpha()` does not count combining vowel signs; the ratio is a flawed metric, and the text is visibly all Hindi script.)
- Meaning: "Irrigation should be kept at 7–10 day intervals, but avoid watering for more than 24 hours." The evidence says irrigation should **not be delayed** for more than 24 hours after cutting. The output reverses this into an instruction to avoid watering for over 24 hours. It also omits "irrigate immediately", the 3rd/4th day irrigation, and the stop date. Only the 7–10 day interval is preserved.

### 11.4 Comparison with earlier outputs and the extractive baseline

| Case | Previous realistic context (section 10, greedy) | Gold-only (this run) | Extractive baseline (existing pipeline) | Change |
|---|---|---|---|---|
| A soybean | Correct N, P2O5, K2O (20/80/40) and Zn/Mn dose with partial qualifier; omitted S/gypsum | K2O 25 and S 25 wrong; Zn/Mn dropped; qualifier misplaced | Led with the exact sentence "Apply 20 kg N and 80 kg P2O5 and 40 kg K2O per ha 40 kg of S as gypsum (220 kg/ha) as basal dressing", then unrelated effluent text | **Worse** |
| B ratoon sorghum | Wrong: "irrigate once at 4 days interval" (borrowed from a flower-picking sentence) | No wrong claim; omits day 3/4 irrigation and stop date | Irrelevant ratoon note (extractive path failed too) | **Improved** (but incomplete) |
| C finger millet | Row spacing 22.5–30 cm correct; seed rate omitted | Row spacing wrong (10 cm); seed rate omitted | Exact seed rate (10 kg/ha) and spacing (22.5–30 cm), correct and complete | **Worse** |
| Hindi sorghum | English reply, irrelevant (flower picking) | Hindi reply, relevant, but reverses the 24-hour rule | not available | Improved (language, topic); still unsafe in one claim |

Net: 1 of 3 English cases improved, 2 got worse; 0 of 3 are fully correct. The new errors use numbers that do appear in the chunk but are attached to the wrong item (25 kg from ZnSO4 placed on K2O and S; 10 from "7.5–10 cm" or "10 kg/ha" placed on row spacing), so a presence-of-number check would pass them.

### 11.5 Timing and memory (measured)

| Run | Prompt tokens | Prefill (s) | Decode tok/s | Generated tokens | Total (s) |
|---|---:|---:|---:|---:|---:|
| A | 718 | 112.6 | 3.63 | 61 | 129.4 |
| B | 484 | 64.1 | 4.21 | 37 | 72.9 |
| C | 486 | 64.9 | 4.26 | 46 | 75.7 |
| Hindi | 493 | 64.8 | 4.24 | 36 | 73.3 |

- Load 7.6 s. Peak RSS 8.80 GB, peak commit 11.57 GB, system availability fell from 8.59 GB to a minimum of 2.71 GB (memory load 76–78%). No crash, no memory-guard abort.
- Shorter prompts cut latency to about 1.2–2 minutes per answer (against 4–7.5 minutes before), at 6.4–7.5 prompt tokens/s in prefill. This is still far from interactive, and the faster time does not offset the accuracy result.

### 11.6 Decision

Criteria you set for proceeding, against the evidence:

| Criterion | Met? |
|---|---|
| All three English answers factually correct | **No** (A wrong, C wrong, B incomplete) |
| No unsupported or cross-topic recommendations | **No** (A and C attach evidence numbers to the wrong items) |
| Important values, units and conditions preserved | **No** (A moved a qualifier; B omitted the day 3/4 irrigation and stop date; C omitted the seed rate) |
| Meaningful improvement over the previous realistic-context results | **No** (1 improved, 2 worse) |

**Verdict: STOP.** In line with the stop condition, no further AgriParam experiments were run (no prompt engineering, sampling, quantization, model changes or downloads).

AgriParam therefore remains an **unmet professor requirement**: it can be loaded and run, but in these tests it did not produce reliable, evidence-grounded answers. Caveat on the strength of the evidence: three English cases plus one Hindi case, greedy decoding, one prompt format, bf16 on CPU. That is a small qualitative probe, not a statistical evaluation, but the pre-set criteria require every answer to be correct, and none was.

**Recommendation:** concentrate the remaining time on the working RAG + IndicTrans2 application: complete and run its tests, capture screenshots, write the report and presentation, assemble the evaluation evidence, and prepare the demo. The AgriParam investigation (provenance and hashes, code review, cache incompatibility, FP32 comparison, realistic-context and gold-only tests) is documented in this file and can be cited honestly as an attempted integration with its blockers. How to present the unmet requirement to the professor is your decision. No integration of AgriParam into the application was made. Licence status remains unresolved and no licensing claim is made.

Scratchpad files (Claude session scratchpad; temporary, not retained): `rag_gen_min.py`, `rag_gen_min.json` (exact prompts' evidence, outputs, timings).
