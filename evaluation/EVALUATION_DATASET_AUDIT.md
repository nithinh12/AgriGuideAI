# Evaluation dataset consistency audit

*Read-only audit of `evaluation/test_cases.jsonl` (SHA-256 `acd6df127c140afe86854404bcd6caf629933583b175a09445d2f0c20359b36e`, verified before and after the audit). Nothing in the dataset, corpus, code or other docs was modified; this file is the only thing created. No formal evaluation was run. The dataset is **not frozen**.*

## 1. Scope, method and limits

**Audited:** all 48 cases (16 English, 16 Hindi, 16 Kannada) = 14 intents x 3 languages + 2 alternative phrasings x 3 languages.

**Source of truth:** the three PDFs in `data/raw/` (`tnau_agriculture.pdf` 460 pp, `tnau_horticulture.pdf` 442 pp, `tn_crop_sop_2023.pdf` 36 pp) and the indexed chunks in `data/processed/chunks.jsonl` (977 chunks).

**Checks actually executed**

| # | Check | Result |
|---|---|---|
| 1 | Every `gold_chunk_ids` entry exists in the index; chunk `doc_id` = `gold_doc_id`; chunk page is in `gold_pages` | Pass for all 12 answerable English cases (Hindi/Kannada copies are identical) |
| 2 | Every `evidence_quotes` string occurs verbatim (whitespace-normalised) in the cited chunk **and** on the cited PDF page, re-extracted independently with `pypdf` | Pass. Quotes occur only on the cited page(s); the drone sentence occurs on SOP pp. 18 and 19 (duplicated text layer) |
| 3 | Every `gold_terms` string is a substring of the cited chunk text (case-sensitive) | Pass |
| 4 | Every `required_points` item occurs in the cited chunk (case-insensitive) | Pass |
| 5 | Every `required_points` item occurs in `reference_answer` | **Fails for two items** (see AUD-03) |
| 6 | Every `must_preserve` item occurs in `reference_answer` | Pass |
| 7 | Reference-answer numbers and terms agree with the source text | Pass for all 12 (differences are omissions, listed below) |
| 8 | Hindi/Kannada records differ from their English twin only in `id`, `language`, `question`, `authoring`, `native_review_needed`, `notes` | Pass for all 32 (gold, reference, terms, behaviour, evidence are identical to English) |
| 9 | `english_reference_question` equals the English question for every Hindi/Kannada case | Pass for all 32 |
| 10 | Competing statements elsewhere in the three PDFs for each answerable intent (full-text search) | Done; findings AUD-06, AUD-07, AUD-08, AUD-16 |
| 11 | Unsupported cases: full-text search of all three PDFs for saffron, crocus, guitar, prices, waiting/pre-harvest intervals, chlorantraniliprole | Done; see section 5 |
| 12 | Overlap with the 40-case development set (`retrieval_relevance_cases.jsonl`): same gold page and similar wording | No same-page overlap. One topical neighbour (AUD-15) |

**Limits (stated so nothing is over-claimed)**

- Text was re-extracted with `pypdf`, the same kind of text layer the index was built from. **Page images could not be rendered** (`pdftoppm` is not installed, so the PDF viewer failed). Anything that depends on printed layout (table columns, which of two duplicated pages physically carries a sentence, what a table row label refers to) is marked *manual review*.
- Hindi and Kannada semantic checks are my reading of the wording against the English reference. **They are not native-speaker validation**, and nothing here claims it.
- Text search cannot see content that exists only as an image in the PDFs.
- No agricultural value was inferred or invented. Where the source is ambiguous, the case is marked *manual review* and no value is proposed.

## 2. Summary numbers

| Measure | Count |
|---|---|
| Total cases audited | **48** |
| Cases with no case-specific issue | **21** (`irrig_01` x6, `crop_01` x3, `crop_02` x3, `unsup_ood_01` x3, `unsup_absent_01` x3, `unsup_current_01` x3) |
| Cases with at least one case-specific issue | **27** |
| of which require a correction or a design decision before freeze | 24 (`irrig_02` x3, `irrig_03` x3, `fert_01` x6, `fert_02` x3, `crop_03` x3, `hort_01` x3, `drone_01` x3) |
| of which are documentation/observation only (label is correct) | 3 (`unsup_adjacent_01` x3) |
| Issues with severity **Critical** | 0 |
| **High** | 1 (global, process: English wording review not done) |
| **Medium** | 9 |
| **Low** | 5 |

No factual error was found in any reference answer: every reference answer is supported by its cited source text. The problems are incomplete or inconsistent gold metadata, undefined matching rules, extra valid evidence the gold labels do not list, and unfinished review/metadata steps.

Global issues (AUD-01, AUD-02, AUD-11) apply to whole groups of cases and are not counted in the per-case figures above.

## 3. Per-case status

`OK` = no case-specific issue. Issue IDs refer to section 4.

| Intent | en | hi | kn | Result |
|---|---|---|---|---|
| `irrig_01` groundnut critical stages | OK | OK (corrected) | OK (corrected) | no issues |
| `irrig_01_alt` | OK | OK (unchanged) | OK (unchanged) | no issues |
| `irrig_02` ratoon sorghum irrigation | AUD-03, AUD-04 | AUD-03, AUD-04 | AUD-03, AUD-04 | correction/decision |
| `irrig_03` soybean water stagnation | AUD-07 (Low) | AUD-07 (Medium) | AUD-07 (Low) | manual review |
| `fert_01` groundnut gypsum | AUD-06 | AUD-06 | AUD-06 | manual review |
| `fert_01_alt` | AUD-06, AUD-12 | AUD-06, AUD-12 | AUD-06, AUD-12 | manual review |
| `fert_02` soybean basal fertilizer | AUD-05, AUD-16 | AUD-05, AUD-16 | AUD-05, AUD-16 | correction/decision |
| `crop_01` maize seed rate | OK | OK | OK | no issues (see AUD-11 for units) |
| `crop_02` finger millet | OK | OK | OK | no issues (see AUD-11 for units) |
| `crop_03` pure sorghum | AUD-03, AUD-14 | AUD-03, AUD-14 | AUD-03, AUD-14 | correction/decision |
| `hort_01` tomato spacing | AUD-08 | AUD-08 | AUD-08 | manual review (Low) |
| `drone_01` heavy-rain spraying | AUD-09 | AUD-09 | AUD-09 | manual review |
| `unsup_ood_01` | OK | OK | OK | abstain label correct |
| `unsup_absent_01` | OK | OK | OK | abstain label correct |
| `unsup_current_01` | OK | OK | OK | abstain label correct |
| `unsup_adjacent_01` | AUD-10 | AUD-10 | AUD-10 | abstain label correct; documentation gap |

## 4. Issues

Each issue gives: cases, severity, field, what the source supports, why the data is inconsistent, proposed correction. Any change to `test_cases.jsonl` changes its hash, so corrections must be made together, before freeze, followed by re-validation and re-recording of the hash.

### AUD-01 - English wording review not done (global)
- **Cases:** all 16 English cases.
- **Severity:** High (blocks freeze; not a data error).
- **Field:** `authoring` = "ai-written (Claude); author review pending"; the English review blocks in `evaluation/native_language_review.md` are all Pending.
- **Source supports:** n/a (process).
- **Inconsistency:** the Hindi/Kannada questions were reviewed and corrected, but the English questions, which every Hindi/Kannada case is judged against, were not. Evaluation methodology requires the file be frozen only after review.
- **Proposed correction:** the author reviews the 16 English questions and records the outcome. No wording change is proposed by this audit. This audit's findings on English semantics (all 16 are consistent with their evidence) can inform that review but do not replace it.

### AUD-02 - Hindi/Kannada metadata does not record the completed manual review (global)
- **Cases:** all 32 Hindi/Kannada cases.
- **Severity:** Medium.
- **Fields:** `authoring` ("ai-written (Claude), not natively validated"), `native_review_needed` (true), `notes` ("... not validated by a native speaker; flagged for native review"), `native_speaker_validated` (false).
- **Source supports:** n/a (process). The manual review is recorded only in the two review documents, not in the dataset.
- **Inconsistency:** the dataset still reads as if no review happened. The earlier decision to keep `native_speaker_validated: false` is still correct, since no native-speaker status has been established.
- **Proposed correction:** a decision for the project owner. Either leave the fields as they are and state in the report that the review record lives in the two review documents, or add a field such as `manual_review` (values and wording chosen by the owner) before freeze. Do not set `native_speaker_validated: true` unless that status is actually established.

### AUD-03 - Required-point matching rule undefined; two required points/gold terms do not match the reference answer's own spelling
- **Cases:** `en/hi/kn_irrig_02`, `en/hi/kn_crop_03`.
- **Severity:** Medium.
- **Fields:** `irrig_02.required_points[2]` = `"7 - 10"`; `crop_03.required_points[0]` = `"10kg/ha"` and `crop_03.gold_terms[0]` = `"pure crop of sorghum, maintain the seed rate at 10kg/ha"`.
- **Source supports:** p. 85 "Subsequently irrigate once in 7 - 10 days"; p. 82 "maintain the seed rate at 10kg/ha". The three strings are verbatim from the source.
- **Inconsistency:** `reference_answer` writes "7-10" and "10 kg/ha", so these required points are not substrings of the dataset's own reference answer. The methodology says required points are matched "case-insensitively, digits normalised" but no matcher exists yet (`evaluation/run_evaluation.py` is not written), and "digits normalised" does not say whether spaces around hyphens or between number and unit are normalised. `gold_terms` matching against chunk text works only because the source has the same quirky spacing.
- **Proposed correction (evidence-justified):** do not change the source-verbatim strings. Specify in the runner and in `docs/evaluation_methodology.md` that matching ignores whitespace around hyphens and between a number and its unit (so "7 - 10", "7-10", "10kg/ha", "10 kg/ha" are equal), and add a unit test using these two cases. Alternatively align the reference answer to the source spelling. Choose one before freeze.

### AUD-04 - Ratoon sorghum irrigation: required points cover only part of the schedule
- **Cases:** `en/hi/kn_irrig_02`.
- **Severity:** Medium.
- **Fields:** `required_points`, `gold_terms` vs `reference_answer`, `must_preserve`.
- **Source supports (p. 85, WATER MANAGEMENT):** "Irrigate immediately after cutting the main crop. Irrigation should not be delayed for more than 24 hours after cutting. Irrigate on 3rd or 4th day after cutting. Subsequently irrigate once in 7 - 10 days. Stop irrigation on 70 - 80 days after ratooning." The reference answer is faithful to this (it omits the 24-hour sentence).
- **Inconsistency:** the questions (including the corrected Hindi "किस प्रकार करनी चाहिए" and Kannada "ಹೇಗೆ ... ಹಾಯಿಸಬೇಕು") ask for the whole schedule. `must_preserve` includes `70` and `80` and the reference answer states the stop date, but `required_points` has only three of the five steps and no stop-irrigation point, so an answer that omits the stopping rule would still score full coverage. `gold_terms` only anchors the first step.
- **Proposed correction:** add `"70 - 80"` (verbatim source) to `required_points`; add the 24-hour step only if the author wants it required. This is a design decision about how complete an answer must be, so it is flagged for the author rather than applied.

### AUD-05 - Soybean basal fertilizer: sulphur/gypsum part not in required points
- **Cases:** `en/hi/kn_fert_02`.
- **Severity:** Medium.
- **Fields:** `required_points`, `gold_terms` vs `reference_answer`, `must_preserve`.
- **Source supports (p. 186, "FERTILIZER APPLICATION i"):** "Apply 20 kg N and 80 kg P 2 O5 and 40 kg K 2 O per ha 40 kg of S as gypsum (220 kg/ha) as basal dressing." The source has no punctuation between "per ha" and "40 kg of S", so reading the 40 kg S as per hectare is an interpretation (the reference answer makes it; it is the natural reading but the printed layout was not checked).
- **Inconsistency:** the questions (EN, and corrected HI/KN "which nutrients and how much") ask for the nutrients and quantities. The reference answer and `must_preserve` include the sulphur/gypsum figures (`220`), but `required_points` has only N, P and K, so a partial answer scores full coverage.
- **Proposed correction:** add `"40 kg of S"` (verbatim source substring) to `required_points` if the sulphur figure is meant to be required; otherwise remove `220` from `must_preserve` so the metadata agrees. Manual review of the rendered page is advised for the "per ha" reading.

### AUD-06 - Groundnut gypsum: two more valid statements on pages not listed as gold
- **Cases:** `en/hi/kn_fert_01`, `en/hi/kn_fert_01_alt`.
- **Severity:** Medium.
- **Fields:** `gold_pages` (`[203]`), `gold_chunk_ids` (`tnau_agriculture::p203::c201`), `gold_terms`, `required_points` (`"40th to 45th day"`).
- **Source supports:** the gold statement on p. 203 ("Apply gypsum @ 400 kg/ha by the side of the plants on the 40th to 45th day of sowing"). The corpus also contains, in groundnut sections:
  - p. 197 (chunk `tnau_agriculture::p197::c194`, "Sulphur deficiency: Gypsum 400 kg/ha as soil application at 45th day after sowing"; the page also contains groundnut seed rate and "groundnut ring mosaic").
  - p. 208 (chunk `tnau_agriculture::p208::c206`, "Apply gypsum @ 400 kg / ha at peg formation stage and at earthing"; the page mentions "increase the seed yield in groundnut", so it appears to be a seed-production or related section; confirm in the rendered page).
- **Inconsistency:** the rate (400 kg/ha) is the same everywhere, so the answer is not contradictory, but the timing wording differs ("40th to 45th day", "45th day", "peg formation stage and at earthing"). A correct answer citing p. 197 or p. 208 would be recorded as *document-only* (page outside `gold_pages`), and on p. 208 the spacing "@ 400 kg / ha" does not match the gold term "Apply gypsum @ 400 kg/ha". For the "and when" questions (EN, corrected HI/KN) the required timing point `40th to 45th day` exists only on p. 203. The p. 203 page also contains caveats the reference omits ("Avoid gypsum in calciferous soils"; "Application of gypsum at the rate of 50 % basal ... reduces Khadhasty malady and pod scab nematode", whose meaning is unclear). These are omissions, not contradictions.
- **Proposed correction:** manual review. Options for the author: (a) accept p. 197 and p. 208 as acceptable additional evidence for the rate (add their chunk ids/pages to the gold set and relax the `gold_terms` match), keeping the timing point tied to p. 203; or (b) keep the single-page gold and document that citations to p. 197/208 will count as document-only. No new value is proposed.

### AUD-07 - Soybean "water stagnation": Hindi wording maps to a different soybean sentence
- **Cases:** `hi_irrig_03` (Medium); `en_irrig_03`, `kn_irrig_03` (Low).
- **Severity:** Medium for Hindi, Low for English/Kannada.
- **Fields:** `question` (hi), `gold_pages`/`gold_chunk_ids`/`reference_answer` (all three).
- **Source supports:** p. 186 (gold): "Soyabean is very sensitive to excess moisture and the crop is affected, if water stagnates in the fields." **p. 185 (chunk `tnau_agriculture::p185::c182`, soybean climate requirement):** "It can withstand short periods of waterlogging and short drought."
- **Inconsistency:** the approved Hindi question uses "जलभराव" (waterlogging) while the English reference question and gold evidence are about *water stagnation*. A system answering the Hindi question from the p. 185 waterlogging sentence would give a source-supported answer that differs from, and is in tension with, the p. 186 gold statement, and would be scored as a wrong-page citation. The Kannada wording ("ನೀರು ನಿಂತುಕೊಳ್ಳುವ", water standing) and the English wording ("stagnation") follow p. 186 more closely, but the same tension exists for any soybean water question.
- **Proposed correction:** manual review by the project owner. The user has approved the current Hindi wording, so this audit does not change it. Options: (a) keep the wording and record p. 185 as a known competing statement, scoring it as document-only; (b) revisit the Hindi wording; (c) accept both statements and list p. 185 as alternate evidence with an adjusted reference answer. No value is invented in any option.

### AUD-08 - Tomato spacing: duplicated "CO 3" label, drip layout, and corroborating table
- **Cases:** `en/hi/kn_hort_01`.
- **Severity:** Low.
- **Fields:** `reference_answer`, `question`.
- **Source supports (p. 72, layout extraction):** two lines: "PKM 1, Paiyur 1, COTH 2, TNAU Tomato Hybrid CO 3 : 60 x 45 cm" and "CO 3 : 45 x 30 cm". The question asks only about PKM 1, Paiyur 1 and COTH 2, which the first line gives as 60 x 45 cm. The same page then gives other spacings for drip layout (e.g. "90 x 60 x 60 cm in the paired row system"). A table on p. 377 (hybrids) also lists COTH 1, COTH 2 and TNAU Tomato Hybrid CO3 at 60X45.
- **Inconsistency:** the reference answer also asserts that "TNAU Tomato Hybrid CO 3" is planted at 60 x 45 cm, while the page prints a second "CO 3" line with 45 x 30 cm; what the second "CO 3" refers to is not stated in the text and is not inferred here. The question has no "ridge and furrow" qualifier, so the drip-layout spacing is a possible competing reading.
- **Proposed correction:** manual review of the rendered page. If "CO 3" cannot be resolved, drop the CO 3 clause from the reference answer (the question does not ask for it). The 60 x 45 cm answer for the three named varieties is supported and unaffected.

### AUD-09 - Drone SOP: duplicated page text; physical page cannot be determined here
- **Cases:** `en/hi/kn_drone_01`.
- **Severity:** Medium (manual review; the answer itself is correct).
- **Fields:** `gold_pages` (`[18, 19]`), `gold_chunk_ids` (`tn_crop_sop_2023::p18::c27`, `::p19::c28`).
- **Source supports:** "Do not spray if there is forecast of heavy rains in next 1-2 days." The identical sentence, and identical surrounding text, is extracted for both PDF page 18 and page 19. The reference answer is faithful. The sentence belongs to the SOP's "General Guidelines for pest management in crops", not to a drone-specific heading.
- **Inconsistency:** the methodology says allowed pages are decided from the *rendered* page, not extracted text. That could not be done in this audit. Both pages are currently allowed, which is the safe choice, but it has not been confirmed which page prints it (SOP pages 16 and 17 show the same duplication for Table-2).
- **Proposed correction:** none to the data. Render the SOP pages 18 to 20 and confirm; keep `[18, 19]` unless the render shows otherwise.

### AUD-10 - "Adjacent" abstention case: label correct, but the recorded evidence check is incomplete
- **Cases:** `en/hi/kn_unsup_adjacent_01`.
- **Severity:** Medium (documentation); the abstain label itself is supported.
- **Fields:** `notes`; the "SPECIAL EVIDENCE REVIEW" section of `evaluation/native_language_review.md`.
- **Source supports:** no waiting or pre-harvest interval for chlorantraniliprole, and none for rice or paddy, in any of the three PDFs (text layer). Chlorantraniliprole appears for rice only as a drone phytotoxicity-tested molecule (SOP pp. 16/17, Table-2) and as an insecticide dose (about 150 ml or g per ha, agriculture pp. 64 to 66). Waiting-period wording exists only for other products (mango, brinjal and other horticulture produce in the horticulture appendix, dichlorvos safe waiting period on agriculture p. 376, herbicide waiting period on p. 404).
- **Inconsistency:** the recorded check lists five waiting-period chunks and says none concerns rice. It does not mention a sixth statement in the SOP, in the **same chunks that `drone_01` uses as gold** (`p18::c27`, `p19::c28`): "Minimum interval between application of chemical insecticide and harvest of maize corn should be 30 days." This is a harvest interval for **maize** only, so abstention is still the correct behaviour. But it is a realistic way for a system to answer the rice question wrongly, which makes this a valid hard negative and means a "30 days" answer would be a false answer with a quantity, i.e. the critical-failure class in the methodology. The independent confirmation (`Evidence confirmed absent?`) is still *Pending* in the review document.
- **Proposed correction:** no label change. Update the evidence note to include this sentence, and have a reviewer confirm the absence visually in the PDF.

### AUD-11 - `must_preserve` Latin units for Hindi/Kannada (global design check)
- **Cases:** the Hindi and Kannada versions of `fert_01`, `fert_01_alt`, `fert_02`, `crop_01`, `crop_02`, `crop_03` (units `kg/ha`, `kg`, `cm`); the same fields on the English cases are fine.
- **Severity:** Medium (cannot be verified without running the translator, which this audit must not do).
- **Field:** `must_preserve`.
- **Inconsistency:** the methodology's "must-preserve survival" check will look for Latin-script units in the translated answer. If the translator renders "kg/ha" or "cm" in Devanagari/Kannada script, a correct translation would be scored as a loss. Numbers and variety names (`CO 6`, `PKM 1`) are not affected.
- **Proposed correction:** manual review. Decide before freeze whether units belong in `must_preserve` for hi/kn, or whether the check should accept localized unit forms. No dataset change proposed.

### AUD-12 - Alternative gypsum question carries timing numbers it does not ask for
- **Cases:** `en/hi/kn_fert_01_alt`.
- **Severity:** Low.
- **Field:** `must_preserve` (`40`, `45`) vs `required_points` (`400 kg/ha` only).
- **Inconsistency:** the alternative questions ask only for the rate per hectare ("What gypsum rate per hectare is recommended"), so an answer containing only the rate is complete, but a translation of such an answer would fail `must_preserve` items 40 and 45.
- **Proposed correction:** set `must_preserve` for the alternative cases to `["400", "kg/ha"]`, or accept the difference as intended. Decision for the author.

### AUD-14 - Pure sorghum: one chunk mixes transplanted and direct-sown spacing
- **Cases:** `en/hi/kn_crop_03`.
- **Severity:** Low.
- **Source supports:** p. 82 gives "Spacing: 45 x 15 cm, Population 15/m2" for the transplanted crop and, for the direct-sown pure crop, "seed rate at 10kg/ha" and "15 cm between seeds in the rows which are 45 cm apart". The reference answer matches the direct-sown wording.
- **Inconsistency:** the question has no "direct-sown" qualifier (it was removed deliberately, per the review notes). The numbers happen to be consistent, so a transplanted-crop answer would not give contradictory figures, but the seed rate of 10 kg/ha belongs only to the direct-sown clause.
- **Proposed correction:** none required. Noted for the failure analysis.

### AUD-15 - Adjacent case is thematically close to a development-set case
- **Cases:** `en/hi/kn_unsup_adjacent_01`.
- **Severity:** Low.
- **Observation:** `retrieval_relevance_cases.jsonl` (the development set used for tuning) includes a waiting-period case for mango (`horticulture_07`, page 424). The final adjacent case is a different crop and molecule, so there is no direct leakage, but the gate was tuned with waiting-period wording in view. Disclose when reporting.

### AUD-16 - Soybean fertilizer text also appears for a different crop
- **Cases:** `en/hi/kn_fert_02`.
- **Severity:** Low (information; no dataset change).
- **Observation:** the identical dose "Apply 20 kg N and 80 kg P2O5 and 40 kg K2O per ha 40 kg of S as gypsum (220 kg/ha) ... as basal dressing" appears on p. 183 (chunk `tnau_agriculture::p183::c180`), which is in the field lab-lab (mochai) section, not soybean. Gold pages `[186]` correctly exclude it. A system citing p. 183 for a soybean question is citing a different crop with the same numbers, which the methodology counts under wrong-evidence, so the runner should key on page, not on the numbers alone.

## 5. Unsupported cases (do they genuinely require abstention?)

| Intent | Evidence | Verdict |
|---|---|---|
| `unsup_ood_01` (guitar) | Not agricultural; the word "guitar" does not occur in any PDF | Abstain is correct |
| `unsup_absent_01` (saffron spacing) | "saffron" and "crocus" do not occur in the text layer of any PDF. "kesar"/"kesari" occur only in unrelated names (carrot variety Pusa Kesar, hort. p. 142; Arka Kesar, p. 289; kesari halwa, p. 407) | Abstain is correct. Text layer only; image-only content was not checked |
| `unsup_current_01` (groundnut price in Salem today) | The corpus is static (2020 and 2023 publications) and contains no market prices. "market price" occurs once, in a generic phrase about fruit (hort. p. 51) | Abstain is correct (live information) |
| `unsup_adjacent_01` (chlorantraniliprole waiting period, rice, drone) | See AUD-10: no waiting period for this molecule or crop; a maize-only 30-day interval exists in the SOP | Abstain is correct; hard negative |

Hindi and Kannada versions of all four keep the same kind of question (guitar learning, saffron spacing, today's price in Salem, pre-harvest waiting period for rice after drone-sprayed chlorantraniliprole). None became answerable in my reading, which is not native-speaker validation.

## 6. Corrected Hindi/Kannada questions against their gold data

| Case | Still tests the intended concept? | Consistent with gold terms and required points? |
|---|---|---|
| `hi_irrig_01`, `kn_irrig_01` | Yes: growth stages critical for groundnut irrigation | Yes (gold term and required points match p. 203) |
| `hi_irrig_02`, `kn_irrig_02` (kn unchanged) | Yes: how to irrigate ratoon sorghum after cutting | Partly: required points incomplete (AUD-04), formatting (AUD-03) |
| `hi_irrig_03`, `kn_irrig_03` | Yes for Kannada; Hindi "जलभराव" (waterlogging) is looser than "water stagnation" | Partly (AUD-07) |
| `hi_fert_01`, `kn_fert_01` | Yes: how much gypsum and when (matches English "how much ... and when") | Yes for rate and timing from p. 203; extra valid pages exist (AUD-06) |
| `hi_fert_02`, `kn_fert_02` | Yes: which nutrients and how much, per hectare | Partly: sulphur/gypsum not in required points (AUD-05) |

The 23 unchanged questions were not modified and were read against the English reference as well; no mismatch of crop, quantity or topic was found, apart from the points above.

## 7. Prioritized list of corrections and decisions

All of these are for the project owner to decide; none has been applied.

1. **AUD-01** (High): review the 16 English questions. Blocks freeze.
2. **AUD-03**: define whitespace/hyphen/unit normalisation for `required_points`, record it in the methodology and test it, or align spellings (two affected cases: `irrig_02`, `crop_03`).
3. **AUD-04**: decide whether `irrig_02` must require the stop-irrigation step; add `"70 - 80"` if so.
4. **AUD-05**: decide whether `fert_02` must require the sulphur/gypsum part; add `"40 kg of S"` if so, otherwise drop `220` from `must_preserve`.
5. **AUD-06**: decide how to treat the groundnut gypsum statements on p. 197 and p. 208.
6. **AUD-07**: decide how to handle the p. 185 soybean waterlogging sentence versus the Hindi wording.
7. **AUD-09, AUD-10**: render the SOP pages (18 to 20 and 16/17) and confirm duplication and the absence of any rice/chlorantraniliprole interval; update the evidence note for AUD-10.
8. **AUD-02**: decide how the completed manual review is recorded in the dataset itself.
9. **AUD-11**: decide how unit tokens are scored for Hindi/Kannada.
10. **AUD-08, AUD-12, AUD-14, AUD-15, AUD-16** (Low): optional tidy-ups and disclosures.

After any change: update the hash everywhere it is recorded (`evaluation/hi_kn_review_worksheet.md` and `evaluation/native_language_review.md` quote the current hash), re-run the validation, and only then freeze.

## 8. Readiness for formal evaluation

**Not ready to freeze yet.** The dataset is structurally sound (48 valid records, 16 per language, every gold chunk, page, quote and gold term traces to the PDFs, and no reference answer states anything the sources do not support), and the four abstention labels are supported by the text of the three PDFs. No Critical issue was found.

What remains unresolved before freeze:
- The English wording review (AUD-01).
- A decision on how required points are matched and completed (AUD-03, AUD-04, AUD-05).
- Decisions on extra valid evidence and competing statements (AUD-06, AUD-07).
- Visual confirmation of the duplicated SOP pages and of the adjacent-case absence (AUD-09, AUD-10), which could not be rendered here.
- How the completed Hindi/Kannada review is recorded in the dataset (AUD-02), and how units are scored (AUD-11).

## 9. Resolution status (addendum, 2026-11-01)

*The audit above described the dataset at SHA-256 `acd6df127c140afe86854404bcd6caf629933583b175a09445d2f0c20359b36e` and is left unchanged. This addendum records what was decided or done afterwards. Dataset SHA-256 now: `5e7491daac6240bf6a4c77f14014c399a7fcce2a8caa96f8c822dea08bbe0a5a`.*

| Item | Status |
|---|---|
| AUD-01 English review | **Still open.** `en_crop_01` and `en_crop_02` were approved as written. No approval is recorded in these files for the other 14 English questions. |
| AUD-02 metadata | Open. The dataset has no field for the completed manual review; docs now state that review approval is not native-speaker validation. |
| AUD-03 matching rule | **Resolved in code**: formatting-only normalisation in `evaluation/scoring.py`, documented in `docs/evaluation_methodology.md`, tested. |
| AUD-04 `irrig_02` | **Resolved**: all four steps required; `required_points` updated (en/hi/kn). |
| AUD-05 `fert_02` | **Resolved**: complete basal recommendation required; `required_points` updated (en/hi/kn). |
| AUD-06 `fert_01` | **Documented, not resolved**: p203 primary; p197 and p208 recorded as related (`evaluation/related_evidence.json`), not merged, not counted as exact. |
| AUD-07 `irrig_03` | **Documented, not resolved**: p186 primary; p185 recorded as related, not interchangeable. The Hindi "जलभराव" wording was not changed. |
| AUD-09 drone pages | **Inspected on rendered pages**: the guideline is physically on PDF page 18 (printed page 7); PDF page 19 (printed page 8) shows only the Ready-Reckoner table and its text layer duplicates page 18. `gold_pages` stays `[18, 19]` with page 19 noted as a text-layer duplicate. |
| AUD-10 adjacent case | Abstention preserved; maize interval recorded as forbidden evidence. Visual check of the Table-2 pages (16/17) not done. |
| AUD-11 units | Open. Must-preserve is reported but not used as a pass condition. |
| AUD-08, 12, 14, 15, 16 (Low) | Not changed. |
