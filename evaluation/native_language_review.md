# Native-language review sheet — AgriGuide AI evaluation cases

*Prepared for human review. Source: `evaluation/test_cases.jsonl` (48 cases). Method: `docs/evaluation_methodology.md`.*

## Status of the wording (read first)

- **Manual review of all 32 Hindi and Kannada questions is complete** (16 Hindi, 16 Kannada), performed by the user in the Claude Code conversation. **9 wording corrections were approved and applied** to `evaluation/test_cases.jsonl` (Hindi 5, Kannada 4); **23 questions were approved unchanged**. The wording was originally AI-generated (Claude). No reviewer name, credentials or date are recorded, and this record does not claim that the reviewer is a certified or independent native speaker.
- The dataset fields `native_speaker_validated` (false) and `native_review_needed` (true) were **deliberately left unchanged**: the available record does not establish native-speaker status, so no native-speaker validation is claimed. Dataset SHA-256 history: `658255aa660509748c069416af7361315c0512bdec0e3e9bc64c5e9ea6cdeffc` (original), `acd6df127c140afe86854404bcd6caf629933583b175a09445d2f0c20359b36e` (after the 9 approved Hindi/Kannada corrections), `5e7491daac6240bf6a4c77f14014c399a7fcce2a8caa96f8c822dea08bbe0a5a` (current: after the 2026-11-01 update of `required_points` for the `irrig_02` and `fert_02` records; no question text changed in that step).
- **The English questions are AI-written** (by Claude). Only two English approvals are recorded: `en_crop_01` and `en_crop_02` were approved exactly as written by the project owner (decision given in the Claude Code conversation, 2026-11-01). **No approval is recorded in these files for the other 14 English questions**, so their review fields remain Pending; if they were reviewed elsewhere, that outcome has not been recorded here. `en_fert_03` does not exist and must not be created. Gold terms, reference answers, expected behaviours and evidence references were not changed by the manual review; the only dataset change after it was the `required_points` update described above.
- The Hindi and Kannada review-field tables below are filled only to the extent of the recorded decision (final approval, and correction or unchanged). Per-field judgements (natural wording / meaning / terminology) were not recorded separately.
- **"Approved" in this document means a manual review approval by the project owner. It does not mean native-speaker validation.** Native-speaker validation (a fluent speaker of that language, with status recorded, checking the question) has **not been established** for any Hindi or Kannada question, and no such claim is made anywhere in this project's records.

## What to check

For each language (English, Hindi, Kannada) and each case (for English, "meaning matches English intent" reads "meaning matches the intended agricultural question"):

1. **Natural wording** - would a farmer or extension worker actually phrase it this way? (Yes / Needs correction)
2. **Meaning matches English intent** - does it ask the same thing as the English reference question? (Yes / Partially / No)
3. **Agricultural terminology correct** - crop names, inputs and technical terms. Note that Latin-script tokens such as `CO 6`, `COBC 1`, `PKM 1` are variety names and should stay as written. (Yes / Needs correction)
4. **Reviewer comments** - including a proposed corrected wording, if any.
5. **Final approval** - Pending / Approved.

## Contents

| # | Intent | Type | Cases |
|---|---|---|---|
| 1 | `irrig_01` | answerable | 6 (incl. alternative phrasings) |
| 2 | `irrig_02` | answerable | 3 |
| 3 | `irrig_03` | answerable | 3 |
| 4 | `fert_01` | answerable | 6 (incl. alternative phrasings) |
| 5 | `fert_02` | answerable | 3 |
| 6 | `crop_01` | answerable | 3 |
| 7 | `crop_02` | answerable | 3 |
| 8 | `crop_03` | answerable | 3 |
| 9 | `hort_01` | answerable | 3 |
| 10 | `drone_01` | answerable | 3 |
| 11 | `unsup_ood_01` | unsupported | 3 |
| 12 | `unsup_absent_01` | unsupported | 3 |
| 13 | `unsup_current_01` | unsupported | 3 |
| 14 | `unsup_adjacent_01` | unsupported | 3 |

**Total: 48 cases** - English 16, Hindi 16, Kannada 16. Core cases: 42 (14 intents x 3 languages). Alternative-phrasing cases: 6.

## The four unsupported-question categories

Each category appears once per language (12 cases). The expected system behaviour is to **abstain, with no citations**. Reviewers should check that the Hindi and Kannada wording keeps the *same* kind of unsupported question, not that it accidentally becomes answerable.

| Category | `intent_id` | What makes it unsupported |
|---|---|---|
| 1. Out-of-domain | `unsup_ood_01` | Not an agricultural question; the knowledge base contains no guitar-learning content. |
| 2. Agricultural but absent from the knowledge base | `unsup_absent_01` | Agricultural, but saffron/crocus cultivation does not appear in the indexed documents. |
| 3. Current / local information | `unsup_current_01` | Asks for a live local market price; the documents are static 2020/2023 publications with no market prices. |
| 4. Topically adjacent but unsupported | `unsup_adjacent_01` | Shares crop (rice), method (drone) and the molecule (chlorantraniliprole, listed in the SOP's pesticide table) with real evidence, and 'waiting period' appears for other pesticides and crops, but no document gives a waiting period for this molecule on rice. |

## SPECIAL EVIDENCE REVIEW - the chlorantraniliprole waiting-period case

`unsup_adjacent_01` (English `en_unsup_adjacent_01`, Hindi `hi_unsup_adjacent_01`, Kannada `kn_unsup_adjacent_01`) is the most arguable label in the dataset. It is labelled **unsupported** because the indexed documents give no waiting period (pre-harvest interval) for chlorantraniliprole on rice, but it shares the crop (rice), the method (drone spraying), and the molecule with real evidence, and "waiting period" appears elsewhere for other pesticides.

What the dataset builder checked (script run over the 977 indexed chunks; **a reviewer should confirm this independently against the PDFs**, because it relies on text extraction):

- Chunks mentioning chlorantraniliprole: **34**. Of these, chunks that also contain waiting-period wording: **0**.
- Chunks with waiting-period wording at all: **5** (tnau_agriculture p376, tnau_agriculture p404, tnau_horticulture p19, tnau_horticulture p424, tnau_horticulture p425). Of these, chunks mentioning rice or paddy: **0**.

A reviewer should look at, in the source PDFs (`data/raw/`):

1. The drone SOP's pesticide table (Table-2, the crop-wise list of molecules, on pdf page 17; note the PDF's extracted text duplicates neighbouring pages) - confirm it lists molecules but **no waiting period**.
2. Every place the documents mention a waiting, pre-harvest or safe-waiting period (the pages listed above, including the horticulture produce appendix) - confirm none applies to chlorantraniliprole or to rice.
3. The wording itself in each language: Hindi *प्रतीक्षा काल* and Kannada *ಕಾಯಬೇಕು* must still ask about the **pre-harvest waiting period**, and *chlorantraniliprole* must stay recognisable as the same molecule.

**Addendum (2026-11-01 audit, `evaluation/EVALUATION_DATASET_AUDIT.md` AUD-10):** a text-layer search of the three PDFs found no waiting or pre-harvest interval for chlorantraniliprole or for rice/paddy. The list above is incomplete: the SOP (pdf pages 18 and 19, the same text as the heavy-rain guideline) also says "Minimum interval between application of chemical insecticide and harvest of maize corn should be 30 days." That interval is maize-specific, so abstention is still the intended behaviour, and the evaluation runner records any citation of it on this case as `forbidden_evidence`. The rendered SOP page 18 was viewed (it shows the maize sentence); the Table-2 pages (16/17) were not visually checked, so the decision below stays Pending.

| Reviewer decision on the label | |
|---|---|
| Evidence confirmed absent (unsupported label correct)? | **Pending** - Yes / No |
| Reviewer, date, comments | |

---

## Cases by intent

### 1. `irrig_01`

**Intent description:** Irrigation (groundnut): which growth phases are critical for irrigation.

- **Expected behaviour:** **answer** from the cited evidence
- **Gold document and page:** `tnau_agriculture`, PDF page 203
- **Required answer points** (matched case-insensitively in the English answer): `pegging`; `flowering`; `pod development`
- **Must-preserve numbers/units/technical terms:** none (no numbers or Latin-script terms)
- **Reference answer (English):** Pegging, flowering and pod development are the critical growth phases of groundnut for irrigation; adequate soil moisture is essential during them.
- **Evidence quote(s)** (verbatim from the indexed text, extraction artifacts kept): "Pegging, flowering and pod development phases are critical for irrigation during which period adequate soil moisture is essential."
- **Crop:** groundnut

| Case id | Language | Phrasing | Question | Wording status |
|---|---|---|---|---|
| `en_irrig_01` | English | primary | Which growth stages of groundnut are critical for irrigation? | AI-written, author review pending |
| `hi_irrig_01` | Hindi | primary | मूंगफली की सिंचाई के लिए कौन-कौन सी विकास अवस्थाएँ महत्वपूर्ण हैं? | Manually reviewed: corrected wording approved |
| `kn_irrig_01` | Kannada | primary | ಕಡಲೆಕಾಯಿ ಬೆಳೆಗೆ ನೀರಾವರಿ ಅಗತ್ಯವಿರುವ ಪ್ರಮುಖ ಬೆಳವಣಿಗೆಯ ಹಂತಗಳು ಯಾವುವು? | Manually reviewed: corrected wording approved |
| `en_irrig_01_alt` | English | alternative | When does groundnut need adequate soil moisture the most? | AI-written, author review pending |
| `hi_irrig_01_alt` | Hindi | alternative | मूंगफली की फसल को मिट्टी में पर्याप्त नमी की सबसे ज़्यादा ज़रूरत कब होती है? | Manually reviewed: approved unchanged |
| `kn_irrig_01_alt` | Kannada | alternative | ಕಡಲೆಕಾಯಿ ಬೆಳೆಗೆ ಮಣ್ಣಿನಲ್ಲಿ ಹೆಚ್ಚು ತೇವಾಂಶ ಯಾವಾಗ ಬೇಕಾಗುತ್ತದೆ? | Manually reviewed: approved unchanged |

*The alternative phrasing is a phrasing-sensitivity case: the same intent worded differently. Required points for the alternative phrasing: `pegging`; `flowering`; `pod development`.*

#### Review - English (irrig_01)

*English questions are AI-written (by Claude) and await author review. This is an author review of the English wording, not a native-language validation of translated text.*

Wording to review: `en_irrig_01` (primary); `en_irrig_01_alt` (alternative)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - **Pending** |
| Meaning matches intended agricultural question | ☐ Yes  ☐ Partially  ☐ No  - **Pending** |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - **Pending** |
| Reviewer comments / proposed correction | |
| Reviewer name, date | |
| **Final approval** | **Pending** (Pending / Approved) |

#### Review - Hindi (irrig_01)

Wording to review: `hi_irrig_01` (primary); `hi_irrig_01_alt` (alternative)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Meaning matches English intent | ☐ Yes  ☐ Partially  ☐ No  - Not recorded separately |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Reviewer comments / proposed correction | `hi_irrig_01`: correction approved and applied (approved wording: मूंगफली की सिंचाई के लिए कौन-कौन सी विकास अवस्थाएँ महत्वपूर्ण हैं?; pre-correction: मूंगफली की सिंचाई के लिए कौन-कौन सी वृद्धि अवस्थाएँ महत्वपूर्ण हैं?); `hi_irrig_01_alt`: approved unchanged |
| Reviewer name, date | Manual review by the user in the Claude Code conversation; no name, credentials or date recorded |
| **Final approval** | **Approved** |

#### Review - Kannada (irrig_01)

Wording to review: `kn_irrig_01` (primary); `kn_irrig_01_alt` (alternative)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Meaning matches English intent | ☐ Yes  ☐ Partially  ☐ No  - Not recorded separately |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Reviewer comments / proposed correction | `kn_irrig_01`: correction approved and applied (approved wording: ಕಡಲೆಕಾಯಿ ಬೆಳೆಗೆ ನೀರಾವರಿ ಅಗತ್ಯವಿರುವ ಪ್ರಮುಖ ಬೆಳವಣಿಗೆಯ ಹಂತಗಳು ಯಾವುವು?; pre-correction: ಕಡಲೆಕಾಯಿ ಬೆಳೆಯ ನೀರಾವರಿಗೆ ಯಾವ ಬೆಳವಣಿಗೆಯ ಹಂತಗಳು ಮುಖ್ಯ?); `kn_irrig_01_alt`: approved unchanged |
| Reviewer name, date | Manual review by the user in the Claude Code conversation; no name, credentials or date recorded |
| **Final approval** | **Approved** |

---

### 2. `irrig_02`

**Intent description:** Irrigation (ratoon sorghum): how to irrigate after the main crop is cut.

- **Expected behaviour:** **answer** from the cited evidence
- **Gold document and page:** `tnau_agriculture`, PDF page 85
- **Required answer points** (matched case-insensitively in the English answer): `immediately after cutting`; `3rd or 4th day`; `7 - 10`
- **Must-preserve numbers/units/technical terms:** `3`; `4`; `7`; `10`; `70`; `80`
- **Reference answer (English):** For a ratoon sorghum crop, irrigate immediately after cutting the main crop, irrigate again on the 3rd or 4th day after cutting, then once in 7-10 days, and stop irrigation 70-80 days after ratooning.
- **Evidence quote(s)** (verbatim from the indexed text, extraction artifacts kept): "Irrigate immediately after cutting the main crop." / "Irrigate on 3rd or 4th day after cutting." / "Subsequently irrigate once in 7 - 10 days." / "Stop irrigation on 70 - 80 days after ratooning."
- **Crop:** sorghum (ratoon)

| Case id | Language | Phrasing | Question | Wording status |
|---|---|---|---|---|
| `en_irrig_02` | English | primary | How should a ratoon sorghum crop be irrigated after the main crop is cut? | AI-written, author review pending |
| `hi_irrig_02` | Hindi | primary | मुख्य फसल की कटाई के बाद रैटून ज्वार की सिंचाई किस प्रकार करनी चाहिए? | Manually reviewed: corrected wording approved |
| `kn_irrig_02` | Kannada | primary | ಮುಖ್ಯ ಬೆಳೆ ಕಟಾವು ಮಾಡಿದ ನಂತರ ರಟೂನ್ ಜೋಳಕ್ಕೆ ಹೇಗೆ ನೀರು ಹಾಯಿಸಬೇಕು? | Manually reviewed: approved unchanged |

#### Review - English (irrig_02)

*English questions are AI-written (by Claude) and await author review. This is an author review of the English wording, not a native-language validation of translated text.*

Wording to review: `en_irrig_02` (primary)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - **Pending** |
| Meaning matches intended agricultural question | ☐ Yes  ☐ Partially  ☐ No  - **Pending** |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - **Pending** |
| Reviewer comments / proposed correction | |
| Reviewer name, date | |
| **Final approval** | **Pending** (Pending / Approved) |

#### Review - Hindi (irrig_02)

Wording to review: `hi_irrig_02` (primary)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Meaning matches English intent | ☐ Yes  ☐ Partially  ☐ No  - Not recorded separately |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Reviewer comments / proposed correction | `hi_irrig_02`: correction approved and applied (approved wording: मुख्य फसल की कटाई के बाद रैटून ज्वार की सिंचाई किस प्रकार करनी चाहिए?; pre-correction: मुख्य फसल की कटाई के बाद रैटून ज्वार की सिंचाई कैसे करनी चाहिए?) |
| Reviewer name, date | Manual review by the user in the Claude Code conversation; no name, credentials or date recorded |
| **Final approval** | **Approved** |

#### Review - Kannada (irrig_02)

Wording to review: `kn_irrig_02` (primary)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Meaning matches English intent | ☐ Yes  ☐ Partially  ☐ No  - Not recorded separately |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Reviewer comments / proposed correction | `kn_irrig_02`: approved unchanged |
| Reviewer name, date | Manual review by the user in the Claude Code conversation; no name, credentials or date recorded |
| **Final approval** | **Approved** |

---

### 3. `irrig_03`

**Intent description:** Irrigation (soybean): what the guide says about water stagnation / excess moisture.

- **Expected behaviour:** **answer** from the cited evidence
- **Gold document and page:** `tnau_agriculture`, PDF page 186
- **Required answer points** (matched case-insensitively in the English answer): `sensitive to excess moisture`; `water stagnates`
- **Must-preserve numbers/units/technical terms:** none (no numbers or Latin-script terms)
- **Reference answer (English):** Soybean is very sensitive to excess moisture, and the crop is affected if water stagnates in the fields.
- **Evidence quote(s)** (verbatim from the indexed text, extraction artifacts kept): "Soyabean is very sensitive to excess moisture and the crop is affected, if water stagnates in the fields."
- **Crop:** soybean

| Case id | Language | Phrasing | Question | Wording status |
|---|---|---|---|---|
| `en_irrig_03` | English | primary | What does the guide say about water stagnation in soybean fields? | AI-written, author review pending |
| `hi_irrig_03` | Hindi | primary | सोयाबीन के खेतों में जलभराव के बारे में मार्गदर्शिका क्या कहती है? | Manually reviewed: corrected wording approved |
| `kn_irrig_03` | Kannada | primary | ಸೋಯಾಬೀನ್ ಹೊಲಗಳಲ್ಲಿ ನೀರು ನಿಂತುಕೊಳ್ಳುವ ಬಗ್ಗೆ ಮಾರ್ಗದರ್ಶಿಯಲ್ಲಿ ಏನು ಹೇಳಲಾಗಿದೆ? | Manually reviewed: corrected wording approved |

#### Review - English (irrig_03)

*English questions are AI-written (by Claude) and await author review. This is an author review of the English wording, not a native-language validation of translated text.*

Wording to review: `en_irrig_03` (primary)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - **Pending** |
| Meaning matches intended agricultural question | ☐ Yes  ☐ Partially  ☐ No  - **Pending** |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - **Pending** |
| Reviewer comments / proposed correction | |
| Reviewer name, date | |
| **Final approval** | **Pending** (Pending / Approved) |

#### Review - Hindi (irrig_03)

Wording to review: `hi_irrig_03` (primary)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Meaning matches English intent | ☐ Yes  ☐ Partially  ☐ No  - Not recorded separately |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Reviewer comments / proposed correction | `hi_irrig_03`: correction approved and applied (approved wording: सोयाबीन के खेतों में जलभराव के बारे में मार्गदर्शिका क्या कहती है?; pre-correction: सोयाबीन के खेत में पानी रुकने के बारे में गाइड क्या कहती है?) |
| Reviewer name, date | Manual review by the user in the Claude Code conversation; no name, credentials or date recorded |
| **Final approval** | **Approved** |

#### Review - Kannada (irrig_03)

Wording to review: `kn_irrig_03` (primary)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Meaning matches English intent | ☐ Yes  ☐ Partially  ☐ No  - Not recorded separately |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Reviewer comments / proposed correction | `kn_irrig_03`: correction approved and applied (approved wording: ಸೋಯಾಬೀನ್ ಹೊಲಗಳಲ್ಲಿ ನೀರು ನಿಂತುಕೊಳ್ಳುವ ಬಗ್ಗೆ ಮಾರ್ಗದರ್ಶಿಯಲ್ಲಿ ಏನು ಹೇಳಲಾಗಿದೆ?; pre-correction: ಸೋಯಾಬೀನ್ ಹೊಲದಲ್ಲಿ ನೀರು ನಿಲ್ಲುವ ಬಗ್ಗೆ ಮಾರ್ಗದರ್ಶಿ ಏನು ಹೇಳುತ್ತದೆ?) |
| Reviewer name, date | Manual review by the user in the Claude Code conversation; no name, credentials or date recorded |
| **Final approval** | **Approved** |

---

### 4. `fert_01`

**Intent description:** Fertilizer (groundnut): gypsum dose and timing.

- **Expected behaviour:** **answer** from the cited evidence
- **Gold document and page:** `tnau_agriculture`, PDF page 203
- **Required answer points** (matched case-insensitively in the English answer): `400 kg/ha`; `40th to 45th day`
- **Must-preserve numbers/units/technical terms:** `400`; `kg/ha`; `40`; `45`
- **Reference answer (English):** Apply gypsum at 400 kg/ha by the side of the groundnut plants on the 40th to 45th day of sowing.
- **Evidence quote(s)** (verbatim from the indexed text, extraction artifacts kept): "Apply gypsum @ 400 kg/ha by the side of the plants on the 40th to 45th day of sowing."
- **Crop:** groundnut

| Case id | Language | Phrasing | Question | Wording status |
|---|---|---|---|---|
| `en_fert_01` | English | primary | How much gypsum should be applied to groundnut, and when? | AI-written, author review pending |
| `hi_fert_01` | Hindi | primary | मूंगफली की फसल में कितनी मात्रा में जिप्सम डालना चाहिए और कब? | Manually reviewed: corrected wording approved |
| `kn_fert_01` | Kannada | primary | ಕಡಲೆಕಾಯಿ ಬೆಳೆಗೆ ಎಷ್ಟು ಪ್ರಮಾಣದಲ್ಲಿ ಜಿಪ್ಸಮ್ ಹಾಕಬೇಕು ಮತ್ತು ಯಾವಾಗ ಹಾಕಬೇಕು? | Manually reviewed: corrected wording approved |
| `en_fert_01_alt` | English | alternative | What gypsum rate per hectare is recommended for groundnut? | AI-written, author review pending |
| `hi_fert_01_alt` | Hindi | alternative | मूंगफली के लिए प्रति हेक्टेयर जिप्सम की कितनी मात्रा अनुशंसित है? | Manually reviewed: approved unchanged |
| `kn_fert_01_alt` | Kannada | alternative | ಕಡಲೆಕಾಯಿಗೆ ಪ್ರತಿ ಹೆಕ್ಟೇರ್‌ಗೆ ಎಷ್ಟು ಜಿಪ್ಸಮ್ ಶಿಫಾರಸು ಮಾಡಲಾಗಿದೆ? | Manually reviewed: approved unchanged |

*The alternative phrasing is a phrasing-sensitivity case: the same intent worded differently. Required points for the alternative phrasing: `400 kg/ha`.*

#### Review - English (fert_01)

*English questions are AI-written (by Claude) and await author review. This is an author review of the English wording, not a native-language validation of translated text.*

Wording to review: `en_fert_01` (primary); `en_fert_01_alt` (alternative)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - **Pending** |
| Meaning matches intended agricultural question | ☐ Yes  ☐ Partially  ☐ No  - **Pending** |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - **Pending** |
| Reviewer comments / proposed correction | |
| Reviewer name, date | |
| **Final approval** | **Pending** (Pending / Approved) |

#### Review - Hindi (fert_01)

Wording to review: `hi_fert_01` (primary); `hi_fert_01_alt` (alternative)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Meaning matches English intent | ☐ Yes  ☐ Partially  ☐ No  - Not recorded separately |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Reviewer comments / proposed correction | `hi_fert_01`: correction approved and applied (approved wording: मूंगफली की फसल में कितनी मात्रा में जिप्सम डालना चाहिए और कब?; pre-correction: मूंगफली में कितना जिप्सम डालना चाहिए और कब?); `hi_fert_01_alt`: approved unchanged |
| Reviewer name, date | Manual review by the user in the Claude Code conversation; no name, credentials or date recorded |
| **Final approval** | **Approved** |

#### Review - Kannada (fert_01)

Wording to review: `kn_fert_01` (primary); `kn_fert_01_alt` (alternative)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Meaning matches English intent | ☐ Yes  ☐ Partially  ☐ No  - Not recorded separately |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Reviewer comments / proposed correction | `kn_fert_01`: correction approved and applied (approved wording: ಕಡಲೆಕಾಯಿ ಬೆಳೆಗೆ ಎಷ್ಟು ಪ್ರಮಾಣದಲ್ಲಿ ಜಿಪ್ಸಮ್ ಹಾಕಬೇಕು ಮತ್ತು ಯಾವಾಗ ಹಾಕಬೇಕು?; pre-correction: ಕಡಲೆಕಾಯಿಗೆ ಎಷ್ಟು ಜಿಪ್ಸಮ್ ಹಾಕಬೇಕು ಮತ್ತು ಯಾವಾಗ?); `kn_fert_01_alt`: approved unchanged |
| Reviewer name, date | Manual review by the user in the Claude Code conversation; no name, credentials or date recorded |
| **Final approval** | **Approved** |

---

### 5. `fert_02`

**Intent description:** Fertilizer (soybean): basal fertilizer nutrients and quantities per hectare.

- **Expected behaviour:** **answer** from the cited evidence
- **Gold document and page:** `tnau_agriculture`, PDF page 186
- **Required answer points** (matched case-insensitively in the English answer): `20 kg N`; `80 kg P`; `40 kg K`
- **Must-preserve numbers/units/technical terms:** `20`; `80`; `40`; `220`; `kg`
- **Reference answer (English):** As basal dressing apply 20 kg N, 80 kg P2O5 and 40 kg K2O per hectare, and 40 kg of S as gypsum (220 kg/ha).
- **Evidence quote(s)** (verbatim from the indexed text, extraction artifacts kept): "Apply 20 kg N and 80 kg P 2 O5 and 40 kg K 2 O per ha 40 kg of S as gypsum (220 kg/ha) as basal dressing."
- **Crop:** soybean

| Case id | Language | Phrasing | Question | Wording status |
|---|---|---|---|---|
| `en_fert_02` | English | primary | What basal fertilizer nutrients and quantities are recommended per hectare for soybean? | AI-written, author review pending |
| `hi_fert_02` | Hindi | primary | सोयाबीन के लिए प्रति हेक्टेयर बेसल उर्वरक के रूप में कौन-कौन से पोषक तत्व और कितनी मात्रा अनुशंसित हैं? | Manually reviewed: corrected wording approved |
| `kn_fert_02` | Kannada | primary | ಸೋಯಾಬೀನ್ ಬೆಳೆಗೆ ಪ್ರತಿ ಹೆಕ್ಟೇರ್‌ಗೆ ಮೂಲ ಗೊಬ್ಬರವಾಗಿ ಯಾವ ಪೋಷಕಾಂಶಗಳನ್ನು ಎಷ್ಟು ಪ್ರಮಾಣದಲ್ಲಿ ಶಿಫಾರಸು ಮಾಡಲಾಗಿದೆ? | Manually reviewed: corrected wording approved |

#### Review - English (fert_02)

*English questions are AI-written (by Claude) and await author review. This is an author review of the English wording, not a native-language validation of translated text.*

Wording to review: `en_fert_02` (primary)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - **Pending** |
| Meaning matches intended agricultural question | ☐ Yes  ☐ Partially  ☐ No  - **Pending** |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - **Pending** |
| Reviewer comments / proposed correction | |
| Reviewer name, date | |
| **Final approval** | **Pending** (Pending / Approved) |

#### Review - Hindi (fert_02)

**Resolved:** the original Hindi wording asked for "how much basal fertilizer" (singular quantity). A corrected wording that asks for the nutrients and their quantities was approved and is now in the dataset (see the final approval below).

Wording to review: `hi_fert_02` (primary)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Meaning matches English intent | ☐ Yes  ☐ Partially  ☐ No  - Not recorded separately |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Reviewer comments / proposed correction | `hi_fert_02`: correction approved and applied (approved wording: सोयाबीन के लिए प्रति हेक्टेयर बेसल उर्वरक के रूप में कौन-कौन से पोषक तत्व और कितनी मात्रा अनुशंसित हैं?; pre-correction: सोयाबीन के लिए प्रति हेक्टेयर आधार (बेसल) उर्वरक की कितनी मात्रा अनुशंसित है?) |
| Reviewer name, date | Manual review by the user in the Claude Code conversation; no name, credentials or date recorded |
| **Final approval** | **Approved** |

#### Review - Kannada (fert_02)

**Resolved:** the original Kannada wording asked for "the basal fertilizer quantity" (singular quantity). A corrected wording that asks for the nutrients and their quantities was approved and is now in the dataset (see the final approval below).

Wording to review: `kn_fert_02` (primary)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Meaning matches English intent | ☐ Yes  ☐ Partially  ☐ No  - Not recorded separately |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Reviewer comments / proposed correction | `kn_fert_02`: correction approved and applied (approved wording: ಸೋಯಾಬೀನ್ ಬೆಳೆಗೆ ಪ್ರತಿ ಹೆಕ್ಟೇರ್‌ಗೆ ಮೂಲ ಗೊಬ್ಬರವಾಗಿ ಯಾವ ಪೋಷಕಾಂಶಗಳನ್ನು ಎಷ್ಟು ಪ್ರಮಾಣದಲ್ಲಿ ಶಿಫಾರಸು ಮಾಡಲಾಗಿದೆ?; pre-correction: ಸೋಯಾಬೀನ್‌ಗೆ ಪ್ರತಿ ಹೆಕ್ಟೇರ್‌ಗೆ ಮೂಲ ಗೊಬ್ಬರದ ಪ್ರಮಾಣ ಎಷ್ಟು ಶಿಫಾರಸು ಮಾಡಲಾಗಿದೆ?) |
| Reviewer name, date | Manual review by the user in the Claude Code conversation; no name, credentials or date recorded |
| **Final approval** | **Approved** |

---

### 6. `crop_01`

**Intent description:** Crop management (maize): seed rate for named hybrid and variety.

- **Expected behaviour:** **answer** from the cited evidence
- **Gold document and page:** `tnau_agriculture`, PDF page 119
- **Required answer points** (matched case-insensitively in the English answer): `20 kg/ha`; `25 kg`
- **Must-preserve numbers/units/technical terms:** `20`; `25`; `kg/ha`; `CO 6`; `COBC 1`
- **Reference answer (English):** The seed rate is 20 kg/ha for TNAU Maize Hybrid CO 6 (and CO 1) and 25 kg/ha for COBC 1.
- **Evidence quote(s)** (verbatim from the indexed text, extraction artifacts kept): "adopt the seed rate of 20 kg/ha for CO 1 and TNAU Maize Hybrid CO 6 and 25 kg /ha for COBC 1."
- **Crop:** maize

| Case id | Language | Phrasing | Question | Wording status |
|---|---|---|---|---|
| `en_crop_01` | English | primary | What seed rate is recommended for TNAU Maize Hybrid CO 6 and for COBC 1? | AI-written; approved as written (owner decision recorded 2026-11-01) |
| `hi_crop_01` | Hindi | primary | TNAU मक्का संकर CO 6 और COBC 1 के लिए बीज दर कितनी अनुशंसित है? | Manually reviewed: approved unchanged |
| `kn_crop_01` | Kannada | primary | TNAU ಮೆಕ್ಕೆಜೋಳ ಹೈಬ್ರಿಡ್ CO 6 ಮತ್ತು COBC 1 ಗೆ ಶಿಫಾರಸು ಮಾಡಿದ ಬೀಜದ ದರ ಎಷ್ಟು? | Manually reviewed: approved unchanged |

#### Review - English (crop_01)

*English questions are AI-written (by Claude) and await author review. This is an author review of the English wording, not a native-language validation of translated text.*

Wording to review: `en_crop_01` (primary)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - **Pending** |
| Meaning matches intended agricultural question | ☐ Yes  ☐ Partially  ☐ No  - **Pending** |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - **Pending** |
| Reviewer comments / proposed correction | Approved exactly as written; the question must not be rewritten |
| Reviewer name, date | Decision by the project owner in the Claude Code conversation, 2026-11-01; no name recorded |
| **Final approval** | **Approved** (as written) |

#### Review - Hindi (crop_01)

Wording to review: `hi_crop_01` (primary)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Meaning matches English intent | ☐ Yes  ☐ Partially  ☐ No  - Not recorded separately |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Reviewer comments / proposed correction | `hi_crop_01`: approved unchanged |
| Reviewer name, date | Manual review by the user in the Claude Code conversation; no name, credentials or date recorded |
| **Final approval** | **Approved** |

#### Review - Kannada (crop_01)

Wording to review: `kn_crop_01` (primary)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Meaning matches English intent | ☐ Yes  ☐ Partially  ☐ No  - Not recorded separately |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Reviewer comments / proposed correction | `kn_crop_01`: approved unchanged |
| Reviewer name, date | Manual review by the user in the Claude Code conversation; no name, credentials or date recorded |
| **Final approval** | **Approved** |

---

### 7. `crop_02`

**Intent description:** Crop management (finger millet): seed rate and row spacing for line sowing.

- **Expected behaviour:** **answer** from the cited evidence
- **Gold document and page:** `tnau_agriculture`, PDF page 111
- **Required answer points** (matched case-insensitively in the English answer): `22.5`; `30 cm`; `10 kg/ha`
- **Must-preserve numbers/units/technical terms:** `22.5`; `30`; `10`; `kg/ha`; `cm`
- **Reference answer (English):** Line sowing is ideal, with seed drills giving 22.5-30 cm between rows; the recommended seed rate for finger millet is 10 kg/ha.
- **Evidence quote(s)** (verbatim from the indexed text, extraction artifacts kept): "Line sowing is ideal and seed drills giving spacing of 22.5 – 30 cm between rows should be used." / "Finger millet seeds are very small (400 seeds/g) and the recommended seed rate is 10 kg/ha."
- **Crop:** finger millet

| Case id | Language | Phrasing | Question | Wording status |
|---|---|---|---|---|
| `en_crop_02` | English | primary | What seed rate and row spacing are recommended for line sowing of finger millet? | AI-written; approved as written (owner decision recorded 2026-11-01) |
| `hi_crop_02` | Hindi | primary | रागी की पंक्तिबद्ध बुवाई के लिए बीज दर और पंक्तियों के बीच की दूरी कितनी अनुशंसित है? | Manually reviewed: approved unchanged |
| `kn_crop_02` | Kannada | primary | ರಾಗಿಯ ಸಾಲು ಬಿತ್ತನೆಗೆ ಶಿಫಾರಸು ಮಾಡಿದ ಬೀಜದ ದರ ಮತ್ತು ಸಾಲುಗಳ ನಡುವಿನ ಅಂತರ ಎಷ್ಟು? | Manually reviewed: approved unchanged |

#### Review - English (crop_02)

*English questions are AI-written (by Claude) and await author review. This is an author review of the English wording, not a native-language validation of translated text.*

Wording to review: `en_crop_02` (primary)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - **Pending** |
| Meaning matches intended agricultural question | ☐ Yes  ☐ Partially  ☐ No  - **Pending** |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - **Pending** |
| Reviewer comments / proposed correction | Approved exactly as written; the question must not be rewritten |
| Reviewer name, date | Decision by the project owner in the Claude Code conversation, 2026-11-01; no name recorded |
| **Final approval** | **Approved** (as written) |

#### Review - Hindi (crop_02)

Wording to review: `hi_crop_02` (primary)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Meaning matches English intent | ☐ Yes  ☐ Partially  ☐ No  - Not recorded separately |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Reviewer comments / proposed correction | `hi_crop_02`: approved unchanged |
| Reviewer name, date | Manual review by the user in the Claude Code conversation; no name, credentials or date recorded |
| **Final approval** | **Approved** |

#### Review - Kannada (crop_02)

Wording to review: `kn_crop_02` (primary)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Meaning matches English intent | ☐ Yes  ☐ Partially  ☐ No  - Not recorded separately |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Reviewer comments / proposed correction | `kn_crop_02`: approved unchanged |
| Reviewer name, date | Manual review by the user in the Claude Code conversation; no name, credentials or date recorded |
| **Final approval** | **Approved** |

---

### 8. `crop_03`

**Intent description:** Crop management (sorghum): seed rate and spacing for a pure crop.

- **Expected behaviour:** **answer** from the cited evidence
- **Gold document and page:** `tnau_agriculture`, PDF page 82
- **Required answer points** (matched case-insensitively in the English answer): `10kg/ha`; `15 cm`; `45 cm`
- **Must-preserve numbers/units/technical terms:** `10`; `15`; `45`; `kg/ha`; `cm`
- **Reference answer (English):** For a pure crop of sorghum, maintain a seed rate of 10 kg/ha and sow with 15 cm between seeds in rows 45 cm apart.
- **Evidence quote(s)** (verbatim from the indexed text, extraction artifacts kept): "In the case of pure crop of sorghum, maintain the seed rate at 10kg/ha." / "In the case of pure crop of sorghum, sow the seeds with a spacing of 15 cm between seeds in the rows which are 45 cm apart."
- **Crop:** sorghum

| Case id | Language | Phrasing | Question | Wording status |
|---|---|---|---|---|
| `en_crop_03` | English | primary | For a pure crop of sorghum, what seed rate and spacing does the guide recommend? | AI-written, author review pending |
| `hi_crop_03` | Hindi | primary | शुद्ध ज्वार की फसल के लिए गाइड में बीज दर और दूरी कितनी बताई गई है? | Manually reviewed: approved unchanged |
| `kn_crop_03` | Kannada | primary | ಶುದ್ಧ ಜೋಳದ ಬೆಳೆಗೆ ಮಾರ್ಗದರ್ಶಿಯಲ್ಲಿ ಬೀಜದ ದರ ಮತ್ತು ಅಂತರ ಎಷ್ಟು ಹೇಳಲಾಗಿದೆ? | Manually reviewed: approved unchanged |

#### Review - English (crop_03)

*English questions are AI-written (by Claude) and await author review. This is an author review of the English wording, not a native-language validation of translated text.*

Wording to review: `en_crop_03` (primary)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - **Pending** |
| Meaning matches intended agricultural question | ☐ Yes  ☐ Partially  ☐ No  - **Pending** |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - **Pending** |
| Reviewer comments / proposed correction | |
| Reviewer name, date | |
| **Final approval** | **Pending** (Pending / Approved) |

#### Review - Hindi (crop_03)

**Note:** the "direct-sown" phrase was removed (the English now reads "for a pure crop of sorghum ... recommend"). Resolved by the manual review: "शुद्ध ज्वार की फसल" and "बताई गई है" were approved unchanged (a manual-review approval, not a native-speaker validation).

Wording to review: `hi_crop_03` (primary)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Meaning matches English intent | ☐ Yes  ☐ Partially  ☐ No  - Not recorded separately |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Reviewer comments / proposed correction | `hi_crop_03`: approved unchanged |
| Reviewer name, date | Manual review by the user in the Claude Code conversation; no name, credentials or date recorded |
| **Final approval** | **Approved** |

#### Review - Kannada (crop_03)

**Note:** the "direct-sown" phrase was removed (the English now reads "for a pure crop of sorghum ... recommend"). Resolved by the manual review: "ಶುದ್ಧ ಜೋಳದ ಬೆಳೆ" and "ಹೇಳಲಾಗಿದೆ" were approved unchanged (a manual-review approval, not a native-speaker validation).

Wording to review: `kn_crop_03` (primary)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Meaning matches English intent | ☐ Yes  ☐ Partially  ☐ No  - Not recorded separately |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Reviewer comments / proposed correction | `kn_crop_03`: approved unchanged |
| Reviewer name, date | Manual review by the user in the Claude Code conversation; no name, credentials or date recorded |
| **Final approval** | **Approved** |

---

### 9. `hort_01`

**Intent description:** Horticulture (tomato): planting spacing for named varieties.

- **Expected behaviour:** **answer** from the cited evidence
- **Gold document and page:** `tnau_horticulture`, PDF page 72
- **Required answer points** (matched case-insensitively in the English answer): `60 x 45 cm`
- **Must-preserve numbers/units/technical terms:** `60`; `45`; `cm`; `PKM 1`; `Paiyur 1`; `COTH 2`
- **Reference answer (English):** Tomato varieties PKM 1, Paiyur 1, COTH 2 and TNAU Tomato Hybrid CO 3 are planted at a spacing of 60 x 45 cm.
- **Evidence quote(s)** (verbatim from the indexed text, extraction artifacts kept): "Spacing PKM 1, Paiyur 1, COTH 2, TNAU Tomato Hybrid CO 3 : 60 x 45 cm"
- **Crop:** tomato

| Case id | Language | Phrasing | Question | Wording status |
|---|---|---|---|---|
| `en_hort_01` | English | primary | What planting spacing is recommended for tomato varieties PKM 1, Paiyur 1 and COTH 2? | AI-written, author review pending |
| `hi_hort_01` | Hindi | primary | टमाटर की किस्मों PKM 1, Paiyur 1 और COTH 2 के लिए रोपण की दूरी कितनी अनुशंसित है? | Manually reviewed: approved unchanged |
| `kn_hort_01` | Kannada | primary | ಟೊಮೆಟೊ ತಳಿಗಳಾದ PKM 1, Paiyur 1 ಮತ್ತು COTH 2 ಗೆ ಶಿಫಾರಸು ಮಾಡಿದ ನಾಟಿ ಅಂತರ ಎಷ್ಟು? | Manually reviewed: approved unchanged |

#### Review - English (hort_01)

*English questions are AI-written (by Claude) and await author review. This is an author review of the English wording, not a native-language validation of translated text.*

Wording to review: `en_hort_01` (primary)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - **Pending** |
| Meaning matches intended agricultural question | ☐ Yes  ☐ Partially  ☐ No  - **Pending** |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - **Pending** |
| Reviewer comments / proposed correction | |
| Reviewer name, date | |
| **Final approval** | **Pending** (Pending / Approved) |

#### Review - Hindi (hort_01)

Wording to review: `hi_hort_01` (primary)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Meaning matches English intent | ☐ Yes  ☐ Partially  ☐ No  - Not recorded separately |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Reviewer comments / proposed correction | `hi_hort_01`: approved unchanged |
| Reviewer name, date | Manual review by the user in the Claude Code conversation; no name, credentials or date recorded |
| **Final approval** | **Approved** |

#### Review - Kannada (hort_01)

Wording to review: `kn_hort_01` (primary)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Meaning matches English intent | ☐ Yes  ☐ Partially  ☐ No  - Not recorded separately |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Reviewer comments / proposed correction | `kn_hort_01`: approved unchanged |
| Reviewer name, date | Manual review by the user in the Claude Code conversation; no name, credentials or date recorded |
| **Final approval** | **Approved** |

---

### 10. `drone_01`

**Intent description:** Drone safety: whether to spray when heavy rain is forecast.

- **Expected behaviour:** **answer** from the cited evidence
- **Gold document and page:** `tn_crop_sop_2023`, PDF page 18 and 19
- **Required answer points** (matched case-insensitively in the English answer): `do not spray`; `heavy rain`; `1-2 days`
- **Must-preserve numbers/units/technical terms:** `1-2`
- **Reference answer (English):** Do not spray if heavy rain is forecast in the next 1-2 days.
- **Evidence quote(s)** (verbatim from the indexed text, extraction artifacts kept): "Do not spray if there is forecast of heavy rains in next 1-2 days."
- **Crop:** (general)

| Case id | Language | Phrasing | Question | Wording status |
|---|---|---|---|---|
| `en_drone_01` | English | primary | Should pesticide be sprayed with a drone if heavy rain is forecast in the next one to two days? | AI-written, author review pending |
| `hi_drone_01` | Hindi | primary | यदि अगले एक-दो दिनों में भारी बारिश का पूर्वानुमान हो, तो क्या ड्रोन से कीटनाशक का छिड़काव करना चाहिए? | Manually reviewed: approved unchanged |
| `kn_drone_01` | Kannada | primary | ಮುಂದಿನ ಒಂದು-ಎರಡು ದಿನಗಳಲ್ಲಿ ಭಾರಿ ಮಳೆಯ ಮುನ್ಸೂಚನೆ ಇದ್ದರೆ ಡ್ರೋನ್‌ನಿಂದ ಕೀಟನಾಶಕ ಸಿಂಪಡಿಸಬಹುದೇ? | Manually reviewed: approved unchanged |

#### Review - English (drone_01)

*English questions are AI-written (by Claude) and await author review. This is an author review of the English wording, not a native-language validation of translated text.*

Wording to review: `en_drone_01` (primary)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - **Pending** |
| Meaning matches intended agricultural question | ☐ Yes  ☐ Partially  ☐ No  - **Pending** |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - **Pending** |
| Reviewer comments / proposed correction | |
| Reviewer name, date | |
| **Final approval** | **Pending** (Pending / Approved) |

#### Review - Hindi (drone_01)

Wording to review: `hi_drone_01` (primary)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Meaning matches English intent | ☐ Yes  ☐ Partially  ☐ No  - Not recorded separately |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Reviewer comments / proposed correction | `hi_drone_01`: approved unchanged |
| Reviewer name, date | Manual review by the user in the Claude Code conversation; no name, credentials or date recorded |
| **Final approval** | **Approved** |

#### Review - Kannada (drone_01)

Wording to review: `kn_drone_01` (primary)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Meaning matches English intent | ☐ Yes  ☐ Partially  ☐ No  - Not recorded separately |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Reviewer comments / proposed correction | `kn_drone_01`: approved unchanged |
| Reviewer name, date | Manual review by the user in the Claude Code conversation; no name, credentials or date recorded |
| **Final approval** | **Approved** |

---

### 11. `unsup_ood_01`  -  UNSUPPORTED CATEGORY

**Intent description:** UNSUPPORTED - out of domain: a question that is not about agriculture.

- **Expected behaviour:** **abstain** (insufficient evidence, no citations)
- **Gold document/page:** none (unsupported by design). Unsupported type: `out_of_domain`.
- **Why unsupported:** Not an agricultural question; the knowledge base contains no guitar-learning content.

| Case id | Language | Phrasing | Question | Wording status |
|---|---|---|---|---|
| `en_unsup_ood_01` | English | primary | How can I learn to play the guitar quickly? | AI-written, author review pending |
| `hi_unsup_ood_01` | Hindi | primary | मैं गिटार बजाना जल्दी कैसे सीख सकता हूँ? | Manually reviewed: approved unchanged |
| `kn_unsup_ood_01` | Kannada | primary | ಗಿಟಾರ್ ಬಾರಿಸುವುದನ್ನು ಬೇಗ ಕಲಿಯುವುದು ಹೇಗೆ? | Manually reviewed: approved unchanged |

#### Review - English (unsup_ood_01)

*English questions are AI-written (by Claude) and await author review. This is an author review of the English wording, not a native-language validation of translated text.*

Wording to review: `en_unsup_ood_01` (primary)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - **Pending** |
| Meaning matches intended agricultural question | ☐ Yes  ☐ Partially  ☐ No  - **Pending** |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - **Pending** |
| Reviewer comments / proposed correction | |
| Reviewer name, date | |
| **Final approval** | **Pending** (Pending / Approved) |

#### Review - Hindi (unsup_ood_01)

Wording to review: `hi_unsup_ood_01` (primary)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Meaning matches English intent | ☐ Yes  ☐ Partially  ☐ No  - Not recorded separately |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Reviewer comments / proposed correction | `hi_unsup_ood_01`: approved unchanged |
| Reviewer name, date | Manual review by the user in the Claude Code conversation; no name, credentials or date recorded |
| **Final approval** | **Approved** |

#### Review - Kannada (unsup_ood_01)

Wording to review: `kn_unsup_ood_01` (primary)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Meaning matches English intent | ☐ Yes  ☐ Partially  ☐ No  - Not recorded separately |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Reviewer comments / proposed correction | `kn_unsup_ood_01`: approved unchanged |
| Reviewer name, date | Manual review by the user in the Claude Code conversation; no name, credentials or date recorded |
| **Final approval** | **Approved** |

---

### 12. `unsup_absent_01`  -  UNSUPPORTED CATEGORY

**Intent description:** UNSUPPORTED - agricultural question absent from the knowledge base (saffron).

- **Expected behaviour:** **abstain** (insufficient evidence, no citations)
- **Gold document/page:** none (unsupported by design). Unsupported type: `agricultural_absent_from_kb`.
- **Why unsupported:** Agricultural, but saffron/crocus cultivation does not appear in the indexed documents.

| Case id | Language | Phrasing | Question | Wording status |
|---|---|---|---|---|
| `en_unsup_absent_01` | English | primary | What plant spacing is recommended for growing saffron? | AI-written, author review pending |
| `hi_unsup_absent_01` | Hindi | primary | केसर उगाने के लिए पौधों के बीच कितनी दूरी की सिफारिश की जाती है? | Manually reviewed: approved unchanged |
| `kn_unsup_absent_01` | Kannada | primary | ಕೇಸರಿ ಬೆಳೆಯಲು ಗಿಡಗಳ ನಡುವೆ ಎಷ್ಟು ಅಂತರ ಶಿಫಾರಸು ಮಾಡಲಾಗಿದೆ? | Manually reviewed: approved unchanged |

#### Review - English (unsup_absent_01)

*English questions are AI-written (by Claude) and await author review. This is an author review of the English wording, not a native-language validation of translated text.*

Wording to review: `en_unsup_absent_01` (primary)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - **Pending** |
| Meaning matches intended agricultural question | ☐ Yes  ☐ Partially  ☐ No  - **Pending** |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - **Pending** |
| Reviewer comments / proposed correction | |
| Reviewer name, date | |
| **Final approval** | **Pending** (Pending / Approved) |

#### Review - Hindi (unsup_absent_01)

Wording to review: `hi_unsup_absent_01` (primary)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Meaning matches English intent | ☐ Yes  ☐ Partially  ☐ No  - Not recorded separately |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Reviewer comments / proposed correction | `hi_unsup_absent_01`: approved unchanged |
| Reviewer name, date | Manual review by the user in the Claude Code conversation; no name, credentials or date recorded |
| **Final approval** | **Approved** |

#### Review - Kannada (unsup_absent_01)

Wording to review: `kn_unsup_absent_01` (primary)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Meaning matches English intent | ☐ Yes  ☐ Partially  ☐ No  - Not recorded separately |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Reviewer comments / proposed correction | `kn_unsup_absent_01`: approved unchanged |
| Reviewer name, date | Manual review by the user in the Claude Code conversation; no name, credentials or date recorded |
| **Final approval** | **Approved** |

---

### 13. `unsup_current_01`  -  UNSUPPORTED CATEGORY

**Intent description:** UNSUPPORTED - current/local information unavailable in the documents (today's local market price).

- **Expected behaviour:** **abstain** (insufficient evidence, no citations)
- **Gold document/page:** none (unsupported by design). Unsupported type: `current_or_local_information`.
- **Why unsupported:** Asks for a live local market price; the documents are static 2020/2023 publications with no market prices.

| Case id | Language | Phrasing | Question | Wording status |
|---|---|---|---|---|
| `en_unsup_current_01` | English | primary | What is the market price of groundnut in Salem today? | AI-written, author review pending |
| `hi_unsup_current_01` | Hindi | primary | आज सेलम में मूंगफली का बाजार भाव क्या है? | Manually reviewed: approved unchanged |
| `kn_unsup_current_01` | Kannada | primary | ಇಂದು ಸೇಲಂನಲ್ಲಿ ಕಡಲೆಕಾಯಿಯ ಮಾರುಕಟ್ಟೆ ಬೆಲೆ ಎಷ್ಟು? | Manually reviewed: approved unchanged |

#### Review - English (unsup_current_01)

*English questions are AI-written (by Claude) and await author review. This is an author review of the English wording, not a native-language validation of translated text.*

Wording to review: `en_unsup_current_01` (primary)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - **Pending** |
| Meaning matches intended agricultural question | ☐ Yes  ☐ Partially  ☐ No  - **Pending** |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - **Pending** |
| Reviewer comments / proposed correction | |
| Reviewer name, date | |
| **Final approval** | **Pending** (Pending / Approved) |

#### Review - Hindi (unsup_current_01)

Wording to review: `hi_unsup_current_01` (primary)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Meaning matches English intent | ☐ Yes  ☐ Partially  ☐ No  - Not recorded separately |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Reviewer comments / proposed correction | `hi_unsup_current_01`: approved unchanged |
| Reviewer name, date | Manual review by the user in the Claude Code conversation; no name, credentials or date recorded |
| **Final approval** | **Approved** |

#### Review - Kannada (unsup_current_01)

Wording to review: `kn_unsup_current_01` (primary)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Meaning matches English intent | ☐ Yes  ☐ Partially  ☐ No  - Not recorded separately |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Reviewer comments / proposed correction | `kn_unsup_current_01`: approved unchanged |
| Reviewer name, date | Manual review by the user in the Claude Code conversation; no name, credentials or date recorded |
| **Final approval** | **Approved** |

---

### 14. `unsup_adjacent_01`  -  UNSUPPORTED CATEGORY

**Intent description:** UNSUPPORTED - topically adjacent but unsupported (waiting period for a drone-sprayed molecule on rice). SPECIAL EVIDENCE REVIEW.

- **Expected behaviour:** **abstain** (insufficient evidence, no citations)
- **Gold document/page:** none (unsupported by design). Unsupported type: `adjacent_but_unsupported`.
- **Why unsupported:** Shares crop (rice), method (drone) and the molecule (chlorantraniliprole, listed in the SOP's pesticide table) with real evidence, and 'waiting period' appears for other pesticides and crops, but no document gives a waiting period for this molecule on rice.

| Case id | Language | Phrasing | Question | Wording status |
|---|---|---|---|---|
| `en_unsup_adjacent_01` | English | primary | What is the waiting period before harvest after spraying chlorantraniliprole on rice with a drone? | AI-written, author review pending |
| `hi_unsup_adjacent_01` | Hindi | primary | ड्रोन से धान पर क्लोरएंट्रानिलिप्रोल का छिड़काव करने के बाद कटाई से पहले कितने दिन का प्रतीक्षा काल रखना चाहिए? | Manually reviewed: approved unchanged |
| `kn_unsup_adjacent_01` | Kannada | primary | ಡ್ರೋನ್ ಮೂಲಕ ಭತ್ತಕ್ಕೆ ಕ್ಲೋರಾಂಟ್ರಾನಿಲಿಪ್ರೋಲ್ ಸಿಂಪಡಿಸಿದ ನಂತರ ಕೊಯ್ಲಿಗೆ ಮೊದಲು ಎಷ್ಟು ದಿನ ಕಾಯಬೇಕು? | Manually reviewed: approved unchanged |

#### Review - English (unsup_adjacent_01)

*English questions are AI-written (by Claude) and await author review. This is an author review of the English wording, not a native-language validation of translated text.*

Wording to review: `en_unsup_adjacent_01` (primary)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - **Pending** |
| Meaning matches intended agricultural question | ☐ Yes  ☐ Partially  ☐ No  - **Pending** |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - **Pending** |
| Reviewer comments / proposed correction | |
| Reviewer name, date | |
| **Final approval** | **Pending** (Pending / Approved) |

#### Review - Hindi (unsup_adjacent_01)

Wording to review: `hi_unsup_adjacent_01` (primary)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Meaning matches English intent | ☐ Yes  ☐ Partially  ☐ No  - Not recorded separately |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Reviewer comments / proposed correction | `hi_unsup_adjacent_01`: approved unchanged |
| Reviewer name, date | Manual review by the user in the Claude Code conversation; no name, credentials or date recorded |
| **Final approval** | **Approved** |

#### Review - Kannada (unsup_adjacent_01)

Wording to review: `kn_unsup_adjacent_01` (primary)

| Field | Decision |
|---|---|
| Natural wording | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Meaning matches English intent | ☐ Yes  ☐ Partially  ☐ No  - Not recorded separately |
| Agricultural terminology correct | ☐ Yes  ☐ Needs correction  - Not recorded separately |
| Reviewer comments / proposed correction | `kn_unsup_adjacent_01`: approved unchanged |
| Reviewer name, date | Manual review by the user in the Claude Code conversation; no name, credentials or date recorded |
| **Final approval** | **Approved** |

---

## Review summary

| Language | Cases | Approved | Needs correction | Pending |
|---|---|---|---|---|
| English (author review) | 16 | 2 (`en_crop_01`, `en_crop_02`) | 0 | 14 |
| Hindi | 16 | 16 (5 after correction, 11 unchanged) | 0 | 0 |
| Kannada | 16 | 16 (4 after correction, 12 unchanged) | 0 | 0 |
| **Total** | **48** | **34** | **0** | **14** (English, no approval recorded) |

| Review blocks | Count |
|---|---|
| English | 14 (one per intent; covers 16 cases) |
| Hindi | 14 (one per intent; covers 16 cases) |
| Kannada | 14 (one per intent; covers 16 cases) |
| **Total** | **42** (covers 48 cases) |

*Hindi and Kannada counts reflect the completed manual review (approved corrections are already applied to the dataset, so none remain open); English remains pending. A block that covers an alternative phrasing is approved or not as a whole; if the two phrasings differ, record that in the comments.*

