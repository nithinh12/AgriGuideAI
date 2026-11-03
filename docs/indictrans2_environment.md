# Isolated IndicTrans2 environment (`.venv-indic-test`)

> **WARNING: RECONSTRUCTED, NOT VERIFIED BY A CLEAN INSTALLATION.**
> The recreation steps below were written by reading the *existing*
> `.venv-indic-test` (its `pip freeze`) and the worker/translator code. **No
> new environment was created and nothing was installed to test them.** They
> may need adjustment the first time someone follows them from an empty
> directory. Only the "Recorded versions" and "Runtime behaviour" sections
> describe something that was observed or read from the code.

*Written 2026-11-01. **Nothing was installed, upgraded or downgraded while
writing this page.** The package list is the recorded output of
`.\.venv-indic-test\Scripts\python.exe -m pip freeze` taken on 2026-11-01.*

## Why two environments

The production `.venv` (transformers 5.20.2) cannot load the IndicTrans2
checkpoints: their remote code fails with `No module named
'transformers.onnx'`. With transformers 4.57.1 the checkpoints load, but their
modeling code fails with the default key/value cache, so translation runs with
`use_cache=False`. The two environments are therefore never merged. Hindi and
Kannada questions are translated by a worker process
(`python -m src.translation_worker`) started with the isolated interpreter by
`src/translation_client.py`. English never touches it.

## Recorded versions

- Python 3.10.11 (the production `.venv` is also 3.10.11)
- `torch==2.14.1+cpu` (CPU build; the GPU is not used)
- `transformers==4.57.1`, `tokenizers==0.22.2`, `huggingface_hub==0.36.2`,
  `safetensors==0.8.0`
- `sentencepiece==0.2.2`, `sacremoses==0.2.0`, `indic-nlp-library-itt==0.1.1`,
  `nltk==3.10.4`, `regex==2026.9.29`, `numpy==2.2.6`, `pandas==2.3.3`

Packages imported directly by the project code in this environment:
`torch`, `transformers` (`src/translator.py`), `regex`, `tqdm`, `sacremoses` and
`indicnlp` (from `indic-nlp-library-itt`) (`src/indic_processor.py`).
`sentencepiece` is needed by the checkpoints' own tokenizer. The environment
also contains Sphinx-related packages. They were not removed, and it has not
been checked whether they are required transitively by
`indic-nlp-library-itt`, so keep them when recreating the environment.

<details>
<summary>Full recorded <code>pip freeze</code> (2026-11-01)</summary>

```
alabaster==1.0.0
babel==2.18.0
certifi==2026.10.23
charset-normalizer==3.5.2
click==8.5.0
cloudpickle==3.1.2
colorama==0.4.6
defusedxml==0.7.1
docutils==0.21.2
filelock==4.1.0
fsspec==2026.9.0
huggingface_hub==0.36.2
idna==3.20
imagesize==2.0.1
indic-nlp-library-itt==0.1.1
Jinja2==3.1.6
joblib==1.6.0
MarkupSafe==3.0.4
Morfessor==2.0.6
mpmath==1.3.0
networkx==3.4.2
nltk==3.10.4
numpy==2.2.6
packaging==26.3
pandas==2.3.3
Pygments==2.21.0
python-dateutil==3.0.0
pytz==2026.6
PyYAML==6.0.3
regex==2026.9.29
requests==2.34.2
sacremoses==0.2.0
safetensors==0.8.0
sentencepiece==0.2.2
six==1.17.0
snowballstemmer==3.1.1
Sphinx==8.1.3
sphinx-argparse==0.6.1
sphinx_rtd_theme==3.1.0
sphinxcontrib-applehelp==2.0.0
sphinxcontrib-devhelp==2.0.0
sphinxcontrib-htmlhelp==2.1.0
sphinxcontrib-jquery==4.1
sphinxcontrib-jsmath==2.0.0
sphinxcontrib-qthelp==2.0.0
sphinxcontrib-serializinghtml==2.0.0
sympy==1.14.0
tokenizers==0.22.2
tomli==2.5.0
torch==2.14.1+cpu
tqdm==4.70.1
transformers==4.57.1
typing_extensions==4.16.0
tzdata==2026.6
urllib3==2.8.0
```

</details>

## Recreating the environment (RECONSTRUCTED, UNVERIFIED procedure)

Run from the repository root in PowerShell.

1. Create the environment with Python 3.10:
   `py -3.10 -m venv .venv-indic-test`
2. Install the CPU build of torch (same command as in `requirements.txt`):
   `.\.venv-indic-test\Scripts\python.exe -m pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu`
3. Install the remaining packages at the versions in the freeze above (save
   every line except `torch==2.14.1+cpu` to a text file and pass it with
   `-m pip install -r <file>`). Do not let pip choose newer versions:
   transformers must stay at 4.57.1.
4. Obtain the two checkpoints into the project cache
   `.cache\huggingface\hub` (gitignored). They are gated (`gated: auto`): create
   a Hugging Face token, accept the licence on both model pages, and keep the
   token in `.env` only (it is never passed to the worker).
   - `ai4bharat/indictrans2-en-indic-dist-200M`; snapshot present in the
     development cache: `2cfd0a20057756d756bf3e53528f492afc52f91a` (12
     required files, 1,106,584,395 bytes, per the Milestone 2 record)
   - `ai4bharat/indictrans2-indic-en-dist-200M`; snapshot present in the
     development cache: `d66a2122ad6d28184f3dc3797b652bd80ae3f65f` (11
     required files, 921,510,585 bytes, per the Milestone 2 record)

   The code does **not** pin a revision. `src/translator.py` loads each
   checkpoint by repository id with `cache_dir=.cache/huggingface/hub`,
   `local_files_only=True` and `trust_remote_code=True`, so it uses whichever
   snapshot is in the cache. A fresh download may therefore fetch a newer
   revision than the two above; compare hashes if exact reproduction matters.

   The exact download command used in Milestone 2 was not saved as a script.
   The sizes and safetensors hashes were checked against the Hub manifest at
   the time (see `MILESTONE_PROGRESS.md`, Milestone 2 tasks 2 and 3). The worker
   itself runs **offline**, so the download must be done beforehand.
5. Check without changing anything:
   - `.\.venv-indic-test\Scripts\python.exe -m pip freeze` and compare with the
     list above.
   - `.\.venv-indic-test\Scripts\python.exe -c "import torch, transformers; print(torch.__version__, transformers.__version__)"`
     should print `2.14.1+cpu 4.57.1`.
6. Start the app (`.venv\Scripts\streamlit run app/streamlit_app.py`), pick
   Hindi or Kannada and ask a question. The first one loads both models (about
   35 to 65 seconds measured on the development machine) and the worker then
   holds about 1.85 GB of RAM.

## Runtime behaviour the code relies on

- The interpreter is `.venv-indic-test\Scripts\python.exe`, or the path in the
  environment variable `AGRIGUIDE_TRANSLATOR_PYTHON`. The client starts it as
  `<python> -X utf8 -m src.translation_worker` with the repository root as the
  working directory (`src/translation_client.py`).
- The worker inherits the parent's environment with every variable whose name
  contains `TOKEN`, `SECRET`, `PASSWORD` or `API_KEY` (case-insensitive)
  removed. It then forces `PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8`,
  `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`. `HF_HOME` and `HF_HUB_CACHE`
  default to the project `.cache\huggingface` (and its `hub` folder) **only if
  they are not already set** in the parent environment; an existing value is
  kept. The worker also applies `setdefault` for the two offline flags.
- `src/translator.py` sets `HF_MODULES_CACHE` to
  `.cache\huggingface\modules` before importing transformers, so the checkpoints'
  custom code is materialised inside the project.
- The worker builds the translator with `use_cache=False` and
  `local_files_only=True`; beam search uses `num_beams=5` and generation
  `max_length=256`. An input longer than 256 encoded tokens is rejected rather
  than truncated, and the user is told the translation failed.

## Not yet documented or verified

- A from-scratch run of the steps above.
- A scripted, hash-checked checkpoint download.
- Which of the Sphinx-related packages are strictly required.
