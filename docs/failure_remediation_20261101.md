# Failure remediation after the 2026-11-01 evaluation

Scope: targeted fixes for failures recorded in the baseline evaluation run of
2026-11-01 (run `20261101T154404Z`; its results file was left unchanged and is
a local run output, not tracked in this repository). The system is still
**extractive RAG**: no LLM, no AgriParam, no new dependency, no model or
dataset download, IndicTrans2 environment untouched. Pre-change copies of the
modified files were kept locally as a development backup (not tracked).

## Caveat that applies to every number below

These fixes were designed by reading the 48 failing cases, so the 48-case set is
**no longer an independent test** for the changed code. A re-run measures
"after tuning on this set". The 40-case development set was replayed as a
regression guard, but it too has informed earlier tuning. `evaluation/related_evidence.json`,
the dataset and the approved question wording were not changed.

## Root causes and fixes

| # | Recorded failure | Root cause (confirmed by inspecting scores, passages, gate decisions) | Fix |
|---|---|---|---|
| 1 | Groundnut over-abstentions (`irrig_01_alt`, `fert_01`) and wrong-document answers | The crop check required the crop word *inside the chunk*. The gold groundnut chunk (p203) starts mid-section ("12. EARTHING UP"), and PDF extraction even split "Gr oundnut". Heading was in the previous chunk. | `FaissRetriever.crop_context`: a chunk that names **no** crop inherits the crops of the directly preceding chunk (same document, same or previous page, one hop). Reported in `AnswerResult.warnings` when used. |
| 2 | Right passage, right sentence discarded (`irrig_03`, `fert_01`, `irrig_02`) | Term overlap had no inflection/synonym handling: cutting/cut, applied/apply, stagnation/stagnates, phases/stages, peanut/groundnut, soyabean/soybean, hectare/ha, plus "how much", "most/more" counted as required evidence terms. | Explicit variant table in `content_terms`; quantity/degree words made stop words. A general `-ing` stemmer was tried and **rejected** (it made "standing water" match "crop stand"); "distance" -> "spacing" was rejected too (it blurred buffer distance from ponds with plant spacing; an existing test caught it). |
| 3 | Sorghum questions answered from another crop's sowing text (`crop_03`) | Sorghum was not in the crop table, so the crop was never enforced. | Added sorghum to `_CROP_ALIASES`. |
| 4 | False accepts `en_unsup_absent_01` (saffron), `hi/kn_unsup_adjacent_01` | A question term absent from the whole knowledge base (saffron; the misspelled "Chlorentraniliprol") was optional: common words ("spacing", "days", "harvesting", "long") satisfied the "at least 2 specific terms" rule. | If the question has a term that occurs in **no** indexed chunk, a passage must cover >= 50% of the IDF-weighted discriminating terms (`UNKNOWN_TERM_MIN_COVERAGE`); otherwise it is rejected with a reason naming the unknown terms. |
| 5 | Right passage ranked 8th and cut by top-5 (`crop_01`, `hort_01` hi/kn, `fert_01_alt`) | Accepted passages stayed in fusion order, so a 119-word disease-table run-on outranked the passage covering every discriminating term. | Stable sort of accepted passages by weighted coverage of discriminating terms (ties keep fusion order). Acceptance is unchanged. |
| 6 | Only the first item of a list quoted (`irrig_02`, `crop_02` hi/kn) | Each sentence had to match >= 2 question terms alone, but list items 2..n share one. | `ExtractiveEvidenceGenerator` appends verbatim neighbours of the **best-ranked** sentence (same chunk, gap <= 2, shares a question term, not a 60+ word run-on) within 8 sentences / 120 words. Continuations never start an answer. |
| 7 | Translation timeouts `hi_hort_01`, `kn_hort_01` | Not start-up (both models were resident from earlier cases). Recorded time per word rises steeply with sentence length (~0.2-0.4 s/word up to ~35 words, 0.8-0.9 s/word at 66-123 words); the 106-word PDF table row exceeded the 300 s request limit. The worker runs with `use_cache=False`, which is a plausible contributor, but that was **not** isolated by experiment. | `split_for_translation`: sentences over 40 words are translated as clause-sized units (cut at punctuation/capitalised tokens, never next to a number, unit or "x"; rejoined text has exactly the same words). Timeout unchanged. |

Scoring/report additions (reported metrics only; pass rules unchanged): strict
pass with all must-preserve items, translated answers containing placeholder
markup, and a Must-preserve column in the per-case table.

## Evidence

* **English-side replay** (a local development script, not tracked): the
  recorded English question of every case (including the recorded Hindi/Kannada
  machine translations) through the pipeline, scored with `evaluation/scoring.py`.
  Not the official evaluation; translation not exercised. The baseline replay
  reproduced the recorded run exactly (17/48, 27/36 answered, 8 full coverage,
  12 exact citations, same 3 false accepts).

| Replay | Baseline | After |
|---|---|---|
| Strict pass | 17/48 | 38/48 |
| Answerable answered | 27/36 | 32/36 |
| Full required-point coverage | 8/36 | 26/36 |
| Cases with an exact citation | 12/36 | 27/36 |
| Unsupported false answers | 3/12 | 0/12 |
| Dev set: answerable answered with gold evidence | 19/27 | 21/27 |
| Dev set: unsupported answered | 0/13 | 0/13 |

* **Targeted real-translation run** (12 affected hi/kn cases, 660 s; results
  file kept locally, not tracked): 11 pass, 1 fails
  (`hi_irrig_01_alt`). Both timeout cases pass (hi 133 s, kn 96 s, cold start
  included); `hi/kn_unsup_adjacent_01`, `hi/kn_unsup_absent_01` abstain with no
  citations.

## Trade-offs and regressions (not hidden)

* `hi_irrig_01_alt` / `kn_irrig_01_alt` went from an honest abstention to an
  answer that is on-crop and on-moisture but does not state *when* groundnut needs
  water (2/3 points by overlap, no gold citation). Still a strict FAIL either way.
* `hi_irrig_02` went from 0/4 to 0/4 but now quotes harvest steps: its machine
  translation says "after harvesting", not "after cutting".
* `kn_fert_02` changed from a wrong-page answer to an abstention.
* The unknown-term rule is conservative: a legitimate question containing a word
  the corpus never uses (a place name, a rare synonym) now needs strong coverage
  of its other terms and may abstain. No answerable case in the 48 + 40 sets was
  lost to it that was passing before.
* Crop-context inheritance can attribute a chunk to the wrong crop when a section
  heading for a crop missing from the crop table sits on the previous page. It
  is limited to one hop, never overrides a crop the chunk names, and is flagged
  in `warnings`.

## Remaining failures and known limitations

* **Paraphrase gaps (lexical matching):** "important" vs "critical"; "planting
  distance" vs "spacing"; "waterlogging"/"standing water" vs "water stagnation";
  Kannada "rattune corn" for "ratoon sorghum" (maize is not sorghum, so the
  abstention is correct). `hi/kn_irrig_01` still quote drone-SOP text.
* **Unresolved translation defect (not fixed, outside the allowed scope):**
  IndicProcessor `<ID n>` placeholders are sometimes rendered in the target script
  and not restored, leaving e.g. `10 <ಐ. ಡಿ. 2>` in the Kannada answer. Recorded
  run: 1 of 20 translated answers (`kn_crop_03`, which still passed). Targeted
  run: 3 of the 7 Kannada answers (`kn_hort_01`, `kn_crop_02`, `kn_crop_03`), none
  of the Hindi ones. It is now reported by the scorer but not part of the pass rule.
* **Automatic must-preserve matching cannot see localised units** (`cm` ->
  Hindi/Kannada word, `kg/ha` -> `ಕೆ. ಜಿ.`), nor "CO 6" vs "CO-6" style variants, so
  Hindi/Kannada must-preserve misses can be translation, not loss of the fact.
  Required points are checked on the English answer, so translation fidelity itself
  is not scored.
* Same-chunk wrong-section answers remain possible whenever the question has few
  or no discriminating terms.
