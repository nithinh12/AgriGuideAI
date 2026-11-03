# Third-party components: licenses and attribution

Scope: the models, the third-party code ported into this repository, the one
library that port depends on directly (`indic-nlp-library-itt`), the
knowledge-base sources, and the project's image asset. **This file does not
cover every dependency.** The other Python packages in `requirements.txt`
(and in the isolated `.venv-indic-test`) are installed from PyPI and are not
redistributed by this repository; their licences are listed in section 6 as
**not verified** and must be checked before any redistribution. Model-level
licensing is summarized in `docs/model_selection.md`.

Last verified: 2026-10-29 (AgriParam entry revised 2026-11-01; sections 1, 1a,
6 and 7 revised 2026-11-03).

---

## 1. IndicTransToolkit (processor pre/post-processing code)

- **Source**: https://github.com/VarunGumma/IndicTransToolkit (file:
  `IndicTransToolkit/processor.pyx`). The official package used for the
  WSL2 differential check was **IndicTransToolkit 1.1.1**. That is a separate
  package from `indic-nlp-library-itt` (0.1.1, section 1a); an earlier version
  of this file conflated the two. IndicTransToolkit is not installed in either
  project environment and is not a dependency of this project.
- **Author**: Varun Gumma
- **License**: MIT (LICENSE file fetched from the repository main branch on
  2026-10-29, reproduced below)
- **Requires verification:** the copyright line below reads "Copyright (c)
  Varun Gumma.", while the header of `src/indic_processor.py` records
  "Copyright (c) 2024 Varun Gumma". The upstream LICENSE was not re-fetched to
  resolve which is exact.
- **Use in this project**: `src/indic_processor.py` is a mechanical pure-Python
  port of the official Cython `IndicProcessor`, needed because Windows has no
  C compiler for the Cython extension. In the recorded differential run against
  the official compiled build (5 scenarios, 19 steps, `PYTHONHASHSEED=0`),
  every output step matched exactly (0 differences); one error step raised the
  same exception type (`ValueError`) with different message wording (Cython vs
  CPython), reported as a wording-only warning. See `tests/differential/`.

### MIT License (as recorded 2026-10-29)

```
MIT License

Copyright (c) Varun Gumma.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE
```

---

## 1a. indic-nlp-library-itt 0.1.1 (runtime dependency of the port)

- **What it is**: per its package metadata, a fork of the Indic NLP Library
  "specialized for IndicTrans2". It provides the `indicnlp` module imported by
  `src/indic_processor.py`. Pinned at 0.1.1 in `requirements.txt`.
- **License (from installed package files only)**: the package metadata of
  the installed 0.1.1 distribution (both `.venv` and `.venv-indic-test`,
  checked 2026-11-03) declares `License: MIT`, and its bundled `LICENSE` file
  is MIT text with "Copyright (c) 2013-present Anoop Kunchukuttan". The
  upstream repository was **not** checked. Treat this as requiring
  verification before redistribution.
- **Use in this project**: installed from PyPI; not redistributed or modified.

---

## 2. AI4Bharat IndicTrans2 (model checkpoints)

- **Repo**: https://github.com/AI4Bharat/IndicTrans2 — MIT license
- **Checkpoints used**: `ai4bharat/indictrans2-en-indic-dist-200M` and
  `ai4bharat/indictrans2-indic-en-dist-200M` (gated: auto — license accepted on
  Hugging Face; token kept in `.env`, never logged)
- **Checkpoint license**: MIT (per the repo license table: "Model
  checkpoints — MIT"), verified 2026-10-29 — see `docs/model_selection.md`

---

## 3. BharatGen AgriParam (LLM)

- **License: UNRESOLVED. No licence is claimed for AgriParam in this
  project.** An earlier version of this file stated Apache-2.0 on the basis
  of the Hugging Face metadata field alone; that statement is withdrawn. The
  sources conflict: the metadata declares `apache-2.0`, but the repository
  has no LICENSE file, the licence badge link in the model card did not
  resolve, the custom modeling file's header says MIT, and the parent
  Param-1 model's README carries MIT text together with research-only /
  not-for-production wording (see `docs/model_selection.md`; recorded in the
  2026-11-01 audit, not re-fetched when this was written). Resolve with
  BharatGen / the course staff before any redistribution or reuse.
- **Use in this project**: none in the running application. The official
  checkpoint was downloaded to the gitignored `.cache/` and evaluated
  locally on 2026-11-01, then **not integrated** because it failed the
  accuracy criteria; the professor's mandatory AgriParam requirement
  remains **unmet**. The weights are not redistributed by this project.

---

## 4. intfloat/multilingual-e5-small (embeddings)

- **License**: MIT, verified 2026-10-29 — see `docs/model_selection.md`
- **Use in this project**: multilingual (en/hi/kn) query/passage embeddings

---

## 5. Source documents (data/raw/)

- Credible agricultural sources only (ICAR, state agriculture universities,
  government agriculture departments); per-document provenance is recorded in
  `data/raw/sources.jsonl` and summarized in `data/README.md`.
- Text is extracted (pypdf) and used as retrieval evidence with citation; no
  document is redistributed by this project beyond short quoted excerpts shown
  with attribution.

---

## 6. Other Python dependencies (licences NOT verified)

Installed from PyPI at the versions pinned in `requirements.txt`; none is
redistributed or modified by this repository. **No licence has been verified
for any package in this section**; check each package's own metadata and
repository before redistribution.

`streamlit`, `sentence-transformers`, `faiss-cpu`, `transformers`, `torch`,
`pandas`, `numpy`, `pypdf`, `python-dotenv`, `PyYAML`, `rich`,
`huggingface_hub`, `pytest`, `sentencepiece`, `sacremoses`, `nltk`, `regex`,
and their transitive dependencies (for example `tqdm`, which
`src/indic_processor.py` imports). The isolated `.venv-indic-test` uses a
different set (see `docs/indictrans2_environment.md`), also not verified.

---

## 7. Project image asset

- **`assets/agriguide_background.webp`**: an AI-generated image created
  specifically for this project, as stated by the project owner. It is not
  taken from a stock-photo library or other external image source. The
  generating tool and its terms of use are not recorded in this repository.
  No third-party licence applies or is claimed.
