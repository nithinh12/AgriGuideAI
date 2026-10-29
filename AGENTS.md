# AGENTS.md — Rules for AI coding agents on AgriGuide AI

Project: AgriGuide AI — trilingual Indian agricultural advisory RAG assistant.
Academic mini-project (CS3235 CIE3). Deadline: **2026-11-06 10:00 AM**.

## Hard rules

1. **Prescribed models.** The professor requires BharatGen **AgriParam**
   (`bharatgenai/AgriParam`) and AI4Bharat **IndicTrans2**. Do not silently
   substitute alternatives. If one cannot be integrated, state the exact
   blocker and investigate compliant options before changing the design.
2. **Never fabricate.** No invented documents, citations, sources, evaluation
   numbers, test results, or model capabilities. Only report results that were
   actually executed and observed.
3. **No secrets in code or logs.** `HF_TOKEN` and similar go in `.env`
   (gitignored) only. Never print tokens.
4. **Respect the machine.** CPU-first (16 GB RAM; RTX 3050 has only 4 GB VRAM
   and is not used for inference). Do not download large checkpoints before
   compatibility/licensing checks are documented in `docs/model_selection.md`.
5. **Stay inside** `D:\AgriGuideAI` unless explicitly authorized otherwise.
6. **Inspect before you overwrite.** Preserve any existing user work.
7. **Ask before** destructive operations, major environment changes, paid API
   calls, or unexpected large downloads.
8. **No unrelated installs.** Do not duplicate or add packages without need;
   update `requirements.txt` when you do.
9. **Copyright.** Use credible agricultural sources (ICAR, state agriculture
   universities, government agriculture departments). Record provenance for
   every document (see `data/README.md`). Respect licensing and permitted use.

## Engineering standards

- Keep modules separated by pipeline stage (loader, chunker, embeddings,
  retriever, translator, llm_service, rag_pipeline, source_formatter).
- Deterministic configurations where appropriate (see `SEED` in config).
- Log failures with actionable messages; handle errors explicitly.
- Prefer small, verifiable changes over large untested passes.
- Run relevant checks (`pytest`, smoke scripts) and report **actual** results.
- Define evaluation criteria before running evaluation; keep results
  reproducible.

## Workflow expectations

- Explain the objective of a change before making it.
- Report what was checked and what remains unresolved after each step.
- Do not mark a phase complete without evidence (command output, test run).
- Update docs (`model_selection.md`, `architecture.md`, README status) when
  decisions change.
