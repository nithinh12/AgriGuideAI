# Hindi and Kannada review worksheet

*Generated from `evaluation/test_cases.jsonl` (SHA-256 `658255aa660509748c069416af7361315c0512bdec0e3e9bc64c5e9ea6cdeffc`). Questions, gold terms and reference answers are copied exactly from the dataset; nothing was translated, rewritten, improved or validated. The English reference question and answer are the dataset's own fields. Review completed manually by the user in the Claude Code conversation: 9 corrections approved and applied to `evaluation/test_cases.jsonl` (SHA-256 after the corrections `acd6df127c140afe86854404bcd6caf629933583b175a09445d2f0c20359b36e`; current dataset SHA-256 `5e7491daac6240bf6a4c77f14014c399a7fcce2a8caa96f8c822dea08bbe0a5a` after a later `required_points` update for `irrig_02`/`fert_02` that changed no question text; the hash first quoted above is of the pre-correction dataset this worksheet was generated from), 23 questions approved unchanged. Where a case was corrected, the "Original question" line below still shows the pre-correction wording and the approved wording is under "Proposed corrected wording".*

Contents: Hindi 16 cases, Kannada 16 cases (32 total). Cases with `_alt` are alternative phrasings of the same intent.

**Review result:** 32 of 32 cases reviewed (Hindi 16, Kannada 16); 9 corrections approved (Hindi 5, Kannada 4); 23 approved unchanged. No reviewer name, credentials or date are recorded. **These are manual-review approvals, not native-speaker validation; native-speaker validation has not been established.**

---

## Hindi (16 cases)

| # | Case ID | Behaviour |
|---|---|---|
| 1 | `hi_irrig_01` | answer |
| 2 | `hi_irrig_01_alt` | answer |
| 3 | `hi_irrig_02` | answer |
| 4 | `hi_irrig_03` | answer |
| 5 | `hi_fert_01` | answer |
| 6 | `hi_fert_01_alt` | answer |
| 7 | `hi_fert_02` | answer |
| 8 | `hi_crop_01` | answer |
| 9 | `hi_crop_02` | answer |
| 10 | `hi_crop_03` | answer |
| 11 | `hi_hort_01` | answer |
| 12 | `hi_drone_01` | answer |
| 13 | `hi_unsup_ood_01` | abstain |
| 14 | `hi_unsup_absent_01` | abstain |
| 15 | `hi_unsup_current_01` | abstain |
| 16 | `hi_unsup_adjacent_01` | abstain |

### HI.1 `hi_irrig_01`

- **Expected behaviour:** answer
- **Original question (Hindi):** मूंगफली की सिंचाई के लिए कौन-कौन सी वृद्धि अवस्थाएँ महत्वपूर्ण हैं?
- **English reference question (dataset field):** Which growth stages of groundnut are critical for irrigation?
- **Reference answer (English):** Pegging, flowering and pod development are the critical growth phases of groundnut for irrigation; adequate soil moisture is essential during them.
- **Gold terms:** `Pegging, flowering and pod development phases are critical for irrigation`

**Review notes / corrections:**

> Reviewed manually; correction approved and applied to the dataset. The original wording above was replaced by the approved wording below.

**Proposed corrected wording (if any):**

> मूंगफली की सिंचाई के लिए कौन-कौन सी विकास अवस्थाएँ महत्वपूर्ण हैं?

### HI.2 `hi_irrig_01_alt`

- **Expected behaviour:** answer
- **Original question (Hindi):** मूंगफली की फसल को मिट्टी में पर्याप्त नमी की सबसे ज़्यादा ज़रूरत कब होती है?
- **English reference question (dataset field):** When does groundnut need adequate soil moisture the most?
- **Reference answer (English):** Pegging, flowering and pod development are the critical growth phases of groundnut for irrigation; adequate soil moisture is essential during them.
- **Gold terms:** `Pegging, flowering and pod development phases are critical for irrigation`

**Review notes / corrections:**

> Reviewed manually; approved unchanged. No correction.

**Proposed corrected wording (if any):**

> No change (original wording approved).

### HI.3 `hi_irrig_02`

- **Expected behaviour:** answer
- **Original question (Hindi):** मुख्य फसल की कटाई के बाद रैटून ज्वार की सिंचाई कैसे करनी चाहिए?
- **English reference question (dataset field):** How should a ratoon sorghum crop be irrigated after the main crop is cut?
- **Reference answer (English):** For a ratoon sorghum crop, irrigate immediately after cutting the main crop, irrigate again on the 3rd or 4th day after cutting, then once in 7-10 days, and stop irrigation 70-80 days after ratooning.
- **Gold terms:** `Irrigate immediately after cutting the main crop`

**Review notes / corrections:**

> Reviewed manually; correction approved and applied to the dataset. The original wording above was replaced by the approved wording below.

**Proposed corrected wording (if any):**

> मुख्य फसल की कटाई के बाद रैटून ज्वार की सिंचाई किस प्रकार करनी चाहिए?

### HI.4 `hi_irrig_03`

- **Expected behaviour:** answer
- **Original question (Hindi):** सोयाबीन के खेत में पानी रुकने के बारे में गाइड क्या कहती है?
- **English reference question (dataset field):** What does the guide say about water stagnation in soybean fields?
- **Reference answer (English):** Soybean is very sensitive to excess moisture, and the crop is affected if water stagnates in the fields.
- **Gold terms:** `very sensitive to excess moisture`

**Review notes / corrections:**

> Reviewed manually; correction approved and applied to the dataset. The original wording above was replaced by the approved wording below.

**Proposed corrected wording (if any):**

> सोयाबीन के खेतों में जलभराव के बारे में मार्गदर्शिका क्या कहती है?

### HI.5 `hi_fert_01`

- **Expected behaviour:** answer
- **Original question (Hindi):** मूंगफली में कितना जिप्सम डालना चाहिए और कब?
- **English reference question (dataset field):** How much gypsum should be applied to groundnut, and when?
- **Reference answer (English):** Apply gypsum at 400 kg/ha by the side of the groundnut plants on the 40th to 45th day of sowing.
- **Gold terms:** `Apply gypsum @ 400 kg/ha`

**Review notes / corrections:**

> Reviewed manually; correction approved and applied to the dataset. The original wording above was replaced by the approved wording below.

**Proposed corrected wording (if any):**

> मूंगफली की फसल में कितनी मात्रा में जिप्सम डालना चाहिए और कब?

### HI.6 `hi_fert_01_alt`

- **Expected behaviour:** answer
- **Original question (Hindi):** मूंगफली के लिए प्रति हेक्टेयर जिप्सम की कितनी मात्रा अनुशंसित है?
- **English reference question (dataset field):** What gypsum rate per hectare is recommended for groundnut?
- **Reference answer (English):** Apply gypsum at 400 kg/ha by the side of the groundnut plants on the 40th to 45th day of sowing.
- **Gold terms:** `Apply gypsum @ 400 kg/ha`

**Review notes / corrections:**

> Reviewed manually; approved unchanged. No correction.

**Proposed corrected wording (if any):**

> No change (original wording approved).

### HI.7 `hi_fert_02`

- **Expected behaviour:** answer
- **Original question (Hindi):** सोयाबीन के लिए प्रति हेक्टेयर आधार (बेसल) उर्वरक की कितनी मात्रा अनुशंसित है?
- **English reference question (dataset field):** What basal fertilizer nutrients and quantities are recommended per hectare for soybean?
- **Reference answer (English):** As basal dressing apply 20 kg N, 80 kg P2O5 and 40 kg K2O per hectare, and 40 kg of S as gypsum (220 kg/ha).
- **Gold terms:** `Apply 20 kg N and 80 kg P`

**Review notes / corrections:**

> Reviewed manually; correction approved and applied to the dataset. The original wording above was replaced by the approved wording below.

**Proposed corrected wording (if any):**

> सोयाबीन के लिए प्रति हेक्टेयर बेसल उर्वरक के रूप में कौन-कौन से पोषक तत्व और कितनी मात्रा अनुशंसित हैं?

### HI.8 `hi_crop_01`

- **Expected behaviour:** answer
- **Original question (Hindi):** TNAU मक्का संकर CO 6 और COBC 1 के लिए बीज दर कितनी अनुशंसित है?
- **English reference question (dataset field):** What seed rate is recommended for TNAU Maize Hybrid CO 6 and for COBC 1?
- **Reference answer (English):** The seed rate is 20 kg/ha for TNAU Maize Hybrid CO 6 (and CO 1) and 25 kg/ha for COBC 1.
- **Gold terms:** `adopt the seed rate of 20 kg/ha`

**Review notes / corrections:**

> Reviewed manually; approved unchanged. No correction.

**Proposed corrected wording (if any):**

> No change (original wording approved).

### HI.9 `hi_crop_02`

- **Expected behaviour:** answer
- **Original question (Hindi):** रागी की पंक्तिबद्ध बुवाई के लिए बीज दर और पंक्तियों के बीच की दूरी कितनी अनुशंसित है?
- **English reference question (dataset field):** What seed rate and row spacing are recommended for line sowing of finger millet?
- **Reference answer (English):** Line sowing is ideal, with seed drills giving 22.5-30 cm between rows; the recommended seed rate for finger millet is 10 kg/ha.
- **Gold terms:** `recommended seed rate is 10 kg/ha`

**Review notes / corrections:**

> Reviewed manually; approved unchanged. No correction.

**Proposed corrected wording (if any):**

> No change (original wording approved).

### HI.10 `hi_crop_03`

- **Expected behaviour:** answer
- **Original question (Hindi):** शुद्ध ज्वार की फसल के लिए गाइड में बीज दर और दूरी कितनी बताई गई है?
- **English reference question (dataset field):** For a pure crop of sorghum, what seed rate and spacing does the guide recommend?
- **Reference answer (English):** For a pure crop of sorghum, maintain a seed rate of 10 kg/ha and sow with 15 cm between seeds in rows 45 cm apart.
- **Gold terms:** `pure crop of sorghum, maintain the seed rate at 10kg/ha`

**Review notes / corrections:**

> Reviewed manually; approved unchanged. No correction.

**Proposed corrected wording (if any):**

> No change (original wording approved).

### HI.11 `hi_hort_01`

- **Expected behaviour:** answer
- **Original question (Hindi):** टमाटर की किस्मों PKM 1, Paiyur 1 और COTH 2 के लिए रोपण की दूरी कितनी अनुशंसित है?
- **English reference question (dataset field):** What planting spacing is recommended for tomato varieties PKM 1, Paiyur 1 and COTH 2?
- **Reference answer (English):** Tomato varieties PKM 1, Paiyur 1, COTH 2 and TNAU Tomato Hybrid CO 3 are planted at a spacing of 60 x 45 cm.
- **Gold terms:** `Spacing PKM 1, Paiyur 1, COTH 2`

**Review notes / corrections:**

> Reviewed manually; approved unchanged. No correction.

**Proposed corrected wording (if any):**

> No change (original wording approved).

### HI.12 `hi_drone_01`

- **Expected behaviour:** answer
- **Original question (Hindi):** यदि अगले एक-दो दिनों में भारी बारिश का पूर्वानुमान हो, तो क्या ड्रोन से कीटनाशक का छिड़काव करना चाहिए?
- **English reference question (dataset field):** Should pesticide be sprayed with a drone if heavy rain is forecast in the next one to two days?
- **Reference answer (English):** Do not spray if heavy rain is forecast in the next 1-2 days.
- **Gold terms:** `Do not spray if there is forecast of heavy rains`

**Review notes / corrections:**

> Reviewed manually; approved unchanged. No correction.

**Proposed corrected wording (if any):**

> No change (original wording approved).

### HI.13 `hi_unsup_ood_01`

- **Expected behaviour:** abstain
- **Original question (Hindi):** मैं गिटार बजाना जल्दी कैसे सीख सकता हूँ?
- **English reference question (dataset field):** How can I learn to play the guitar quickly?
- **Reference answer (English):** *none (unsupported case; the system is expected to abstain with no citations)*
- **Gold terms:** *none*

**Review notes / corrections:**

> Reviewed manually; approved unchanged. No correction.

**Proposed corrected wording (if any):**

> No change (original wording approved).

### HI.14 `hi_unsup_absent_01`

- **Expected behaviour:** abstain
- **Original question (Hindi):** केसर उगाने के लिए पौधों के बीच कितनी दूरी की सिफारिश की जाती है?
- **English reference question (dataset field):** What plant spacing is recommended for growing saffron?
- **Reference answer (English):** *none (unsupported case; the system is expected to abstain with no citations)*
- **Gold terms:** *none*

**Review notes / corrections:**

> Reviewed manually; approved unchanged. No correction.

**Proposed corrected wording (if any):**

> No change (original wording approved).

### HI.15 `hi_unsup_current_01`

- **Expected behaviour:** abstain
- **Original question (Hindi):** आज सेलम में मूंगफली का बाजार भाव क्या है?
- **English reference question (dataset field):** What is the market price of groundnut in Salem today?
- **Reference answer (English):** *none (unsupported case; the system is expected to abstain with no citations)*
- **Gold terms:** *none*

**Review notes / corrections:**

> Reviewed manually; approved unchanged. No correction.

**Proposed corrected wording (if any):**

> No change (original wording approved).

### HI.16 `hi_unsup_adjacent_01`

- **Expected behaviour:** abstain
- **Original question (Hindi):** ड्रोन से धान पर क्लोरएंट्रानिलिप्रोल का छिड़काव करने के बाद कटाई से पहले कितने दिन का प्रतीक्षा काल रखना चाहिए?
- **English reference question (dataset field):** What is the waiting period before harvest after spraying chlorantraniliprole on rice with a drone?
- **Reference answer (English):** *none (unsupported case; the system is expected to abstain with no citations)*
- **Gold terms:** *none*

**Review notes / corrections:**

> Reviewed manually; approved unchanged. No correction.

**Proposed corrected wording (if any):**

> No change (original wording approved).

---

## Kannada (16 cases)

| # | Case ID | Behaviour |
|---|---|---|
| 1 | `kn_irrig_01` | answer |
| 2 | `kn_irrig_01_alt` | answer |
| 3 | `kn_irrig_02` | answer |
| 4 | `kn_irrig_03` | answer |
| 5 | `kn_fert_01` | answer |
| 6 | `kn_fert_01_alt` | answer |
| 7 | `kn_fert_02` | answer |
| 8 | `kn_crop_01` | answer |
| 9 | `kn_crop_02` | answer |
| 10 | `kn_crop_03` | answer |
| 11 | `kn_hort_01` | answer |
| 12 | `kn_drone_01` | answer |
| 13 | `kn_unsup_ood_01` | abstain |
| 14 | `kn_unsup_absent_01` | abstain |
| 15 | `kn_unsup_current_01` | abstain |
| 16 | `kn_unsup_adjacent_01` | abstain |

### KN.1 `kn_irrig_01`

- **Expected behaviour:** answer
- **Original question (Kannada):** ಕಡಲೆಕಾಯಿ ಬೆಳೆಯ ನೀರಾವರಿಗೆ ಯಾವ ಬೆಳವಣಿಗೆಯ ಹಂತಗಳು ಮುಖ್ಯ?
- **English reference question (dataset field):** Which growth stages of groundnut are critical for irrigation?
- **Reference answer (English):** Pegging, flowering and pod development are the critical growth phases of groundnut for irrigation; adequate soil moisture is essential during them.
- **Gold terms:** `Pegging, flowering and pod development phases are critical for irrigation`

**Review notes / corrections:**

> Reviewed manually; correction approved and applied to the dataset. The original wording above was replaced by the approved wording below.

**Proposed corrected wording (if any):**

> ಕಡಲೆಕಾಯಿ ಬೆಳೆಗೆ ನೀರಾವರಿ ಅಗತ್ಯವಿರುವ ಪ್ರಮುಖ ಬೆಳವಣಿಗೆಯ ಹಂತಗಳು ಯಾವುವು?

### KN.2 `kn_irrig_01_alt`

- **Expected behaviour:** answer
- **Original question (Kannada):** ಕಡಲೆಕಾಯಿ ಬೆಳೆಗೆ ಮಣ್ಣಿನಲ್ಲಿ ಹೆಚ್ಚು ತೇವಾಂಶ ಯಾವಾಗ ಬೇಕಾಗುತ್ತದೆ?
- **English reference question (dataset field):** When does groundnut need adequate soil moisture the most?
- **Reference answer (English):** Pegging, flowering and pod development are the critical growth phases of groundnut for irrigation; adequate soil moisture is essential during them.
- **Gold terms:** `Pegging, flowering and pod development phases are critical for irrigation`

**Review notes / corrections:**

> Reviewed manually; approved unchanged. No correction.

**Proposed corrected wording (if any):**

> No change (original wording approved).

### KN.3 `kn_irrig_02`

- **Expected behaviour:** answer
- **Original question (Kannada):** ಮುಖ್ಯ ಬೆಳೆ ಕಟಾವು ಮಾಡಿದ ನಂತರ ರಟೂನ್ ಜೋಳಕ್ಕೆ ಹೇಗೆ ನೀರು ಹಾಯಿಸಬೇಕು?
- **English reference question (dataset field):** How should a ratoon sorghum crop be irrigated after the main crop is cut?
- **Reference answer (English):** For a ratoon sorghum crop, irrigate immediately after cutting the main crop, irrigate again on the 3rd or 4th day after cutting, then once in 7-10 days, and stop irrigation 70-80 days after ratooning.
- **Gold terms:** `Irrigate immediately after cutting the main crop`

**Review notes / corrections:**

> Reviewed manually; approved unchanged. No correction.

**Proposed corrected wording (if any):**

> No change (original wording approved).

### KN.4 `kn_irrig_03`

- **Expected behaviour:** answer
- **Original question (Kannada):** ಸೋಯಾಬೀನ್ ಹೊಲದಲ್ಲಿ ನೀರು ನಿಲ್ಲುವ ಬಗ್ಗೆ ಮಾರ್ಗದರ್ಶಿ ಏನು ಹೇಳುತ್ತದೆ?
- **English reference question (dataset field):** What does the guide say about water stagnation in soybean fields?
- **Reference answer (English):** Soybean is very sensitive to excess moisture, and the crop is affected if water stagnates in the fields.
- **Gold terms:** `very sensitive to excess moisture`

**Review notes / corrections:**

> Reviewed manually; correction approved and applied to the dataset. The original wording above was replaced by the approved wording below.

**Proposed corrected wording (if any):**

> ಸೋಯಾಬೀನ್ ಹೊಲಗಳಲ್ಲಿ ನೀರು ನಿಂತುಕೊಳ್ಳುವ ಬಗ್ಗೆ ಮಾರ್ಗದರ್ಶಿಯಲ್ಲಿ ಏನು ಹೇಳಲಾಗಿದೆ?

### KN.5 `kn_fert_01`

- **Expected behaviour:** answer
- **Original question (Kannada):** ಕಡಲೆಕಾಯಿಗೆ ಎಷ್ಟು ಜಿಪ್ಸಮ್ ಹಾಕಬೇಕು ಮತ್ತು ಯಾವಾಗ?
- **English reference question (dataset field):** How much gypsum should be applied to groundnut, and when?
- **Reference answer (English):** Apply gypsum at 400 kg/ha by the side of the groundnut plants on the 40th to 45th day of sowing.
- **Gold terms:** `Apply gypsum @ 400 kg/ha`

**Review notes / corrections:**

> Reviewed manually; correction approved and applied to the dataset. The original wording above was replaced by the approved wording below.

**Proposed corrected wording (if any):**

> ಕಡಲೆಕಾಯಿ ಬೆಳೆಗೆ ಎಷ್ಟು ಪ್ರಮಾಣದಲ್ಲಿ ಜಿಪ್ಸಮ್ ಹಾಕಬೇಕು ಮತ್ತು ಯಾವಾಗ ಹಾಕಬೇಕು?

### KN.6 `kn_fert_01_alt`

- **Expected behaviour:** answer
- **Original question (Kannada):** ಕಡಲೆಕಾಯಿಗೆ ಪ್ರತಿ ಹೆಕ್ಟೇರ್‌ಗೆ ಎಷ್ಟು ಜಿಪ್ಸಮ್ ಶಿಫಾರಸು ಮಾಡಲಾಗಿದೆ?
- **English reference question (dataset field):** What gypsum rate per hectare is recommended for groundnut?
- **Reference answer (English):** Apply gypsum at 400 kg/ha by the side of the groundnut plants on the 40th to 45th day of sowing.
- **Gold terms:** `Apply gypsum @ 400 kg/ha`

**Review notes / corrections:**

> Reviewed manually; approved unchanged. No correction.

**Proposed corrected wording (if any):**

> No change (original wording approved).

### KN.7 `kn_fert_02`

- **Expected behaviour:** answer
- **Original question (Kannada):** ಸೋಯಾಬೀನ್‌ಗೆ ಪ್ರತಿ ಹೆಕ್ಟೇರ್‌ಗೆ ಮೂಲ ಗೊಬ್ಬರದ ಪ್ರಮಾಣ ಎಷ್ಟು ಶಿಫಾರಸು ಮಾಡಲಾಗಿದೆ?
- **English reference question (dataset field):** What basal fertilizer nutrients and quantities are recommended per hectare for soybean?
- **Reference answer (English):** As basal dressing apply 20 kg N, 80 kg P2O5 and 40 kg K2O per hectare, and 40 kg of S as gypsum (220 kg/ha).
- **Gold terms:** `Apply 20 kg N and 80 kg P`

**Review notes / corrections:**

> Reviewed manually; correction approved and applied to the dataset. The original wording above was replaced by the approved wording below.

**Proposed corrected wording (if any):**

> ಸೋಯಾಬೀನ್ ಬೆಳೆಗೆ ಪ್ರತಿ ಹೆಕ್ಟೇರ್‌ಗೆ ಮೂಲ ಗೊಬ್ಬರವಾಗಿ ಯಾವ ಪೋಷಕಾಂಶಗಳನ್ನು ಎಷ್ಟು ಪ್ರಮಾಣದಲ್ಲಿ ಶಿಫಾರಸು ಮಾಡಲಾಗಿದೆ?

### KN.8 `kn_crop_01`

- **Expected behaviour:** answer
- **Original question (Kannada):** TNAU ಮೆಕ್ಕೆಜೋಳ ಹೈಬ್ರಿಡ್ CO 6 ಮತ್ತು COBC 1 ಗೆ ಶಿಫಾರಸು ಮಾಡಿದ ಬೀಜದ ದರ ಎಷ್ಟು?
- **English reference question (dataset field):** What seed rate is recommended for TNAU Maize Hybrid CO 6 and for COBC 1?
- **Reference answer (English):** The seed rate is 20 kg/ha for TNAU Maize Hybrid CO 6 (and CO 1) and 25 kg/ha for COBC 1.
- **Gold terms:** `adopt the seed rate of 20 kg/ha`

**Review notes / corrections:**

> Reviewed manually; approved unchanged. No correction.

**Proposed corrected wording (if any):**

> No change (original wording approved).

### KN.9 `kn_crop_02`

- **Expected behaviour:** answer
- **Original question (Kannada):** ರಾಗಿಯ ಸಾಲು ಬಿತ್ತನೆಗೆ ಶಿಫಾರಸು ಮಾಡಿದ ಬೀಜದ ದರ ಮತ್ತು ಸಾಲುಗಳ ನಡುವಿನ ಅಂತರ ಎಷ್ಟು?
- **English reference question (dataset field):** What seed rate and row spacing are recommended for line sowing of finger millet?
- **Reference answer (English):** Line sowing is ideal, with seed drills giving 22.5-30 cm between rows; the recommended seed rate for finger millet is 10 kg/ha.
- **Gold terms:** `recommended seed rate is 10 kg/ha`

**Review notes / corrections:**

> Reviewed manually; approved unchanged. No correction.

**Proposed corrected wording (if any):**

> No change (original wording approved).

### KN.10 `kn_crop_03`

- **Expected behaviour:** answer
- **Original question (Kannada):** ಶುದ್ಧ ಜೋಳದ ಬೆಳೆಗೆ ಮಾರ್ಗದರ್ಶಿಯಲ್ಲಿ ಬೀಜದ ದರ ಮತ್ತು ಅಂತರ ಎಷ್ಟು ಹೇಳಲಾಗಿದೆ?
- **English reference question (dataset field):** For a pure crop of sorghum, what seed rate and spacing does the guide recommend?
- **Reference answer (English):** For a pure crop of sorghum, maintain a seed rate of 10 kg/ha and sow with 15 cm between seeds in rows 45 cm apart.
- **Gold terms:** `pure crop of sorghum, maintain the seed rate at 10kg/ha`

**Review notes / corrections:**

> Reviewed manually; approved unchanged. No correction.

**Proposed corrected wording (if any):**

> No change (original wording approved).

### KN.11 `kn_hort_01`

- **Expected behaviour:** answer
- **Original question (Kannada):** ಟೊಮೆಟೊ ತಳಿಗಳಾದ PKM 1, Paiyur 1 ಮತ್ತು COTH 2 ಗೆ ಶಿಫಾರಸು ಮಾಡಿದ ನಾಟಿ ಅಂತರ ಎಷ್ಟು?
- **English reference question (dataset field):** What planting spacing is recommended for tomato varieties PKM 1, Paiyur 1 and COTH 2?
- **Reference answer (English):** Tomato varieties PKM 1, Paiyur 1, COTH 2 and TNAU Tomato Hybrid CO 3 are planted at a spacing of 60 x 45 cm.
- **Gold terms:** `Spacing PKM 1, Paiyur 1, COTH 2`

**Review notes / corrections:**

> Reviewed manually; approved unchanged. No correction.

**Proposed corrected wording (if any):**

> No change (original wording approved).

### KN.12 `kn_drone_01`

- **Expected behaviour:** answer
- **Original question (Kannada):** ಮುಂದಿನ ಒಂದು-ಎರಡು ದಿನಗಳಲ್ಲಿ ಭಾರಿ ಮಳೆಯ ಮುನ್ಸೂಚನೆ ಇದ್ದರೆ ಡ್ರೋನ್‌ನಿಂದ ಕೀಟನಾಶಕ ಸಿಂಪಡಿಸಬಹುದೇ?
- **English reference question (dataset field):** Should pesticide be sprayed with a drone if heavy rain is forecast in the next one to two days?
- **Reference answer (English):** Do not spray if heavy rain is forecast in the next 1-2 days.
- **Gold terms:** `Do not spray if there is forecast of heavy rains`

**Review notes / corrections:**

> Reviewed manually; approved unchanged. No correction.

**Proposed corrected wording (if any):**

> No change (original wording approved).

### KN.13 `kn_unsup_ood_01`

- **Expected behaviour:** abstain
- **Original question (Kannada):** ಗಿಟಾರ್ ಬಾರಿಸುವುದನ್ನು ಬೇಗ ಕಲಿಯುವುದು ಹೇಗೆ?
- **English reference question (dataset field):** How can I learn to play the guitar quickly?
- **Reference answer (English):** *none (unsupported case; the system is expected to abstain with no citations)*
- **Gold terms:** *none*

**Review notes / corrections:**

> Reviewed manually; approved unchanged. No correction.

**Proposed corrected wording (if any):**

> No change (original wording approved).

### KN.14 `kn_unsup_absent_01`

- **Expected behaviour:** abstain
- **Original question (Kannada):** ಕೇಸರಿ ಬೆಳೆಯಲು ಗಿಡಗಳ ನಡುವೆ ಎಷ್ಟು ಅಂತರ ಶಿಫಾರಸು ಮಾಡಲಾಗಿದೆ?
- **English reference question (dataset field):** What plant spacing is recommended for growing saffron?
- **Reference answer (English):** *none (unsupported case; the system is expected to abstain with no citations)*
- **Gold terms:** *none*

**Review notes / corrections:**

> Reviewed manually; approved unchanged. No correction.

**Proposed corrected wording (if any):**

> No change (original wording approved).

### KN.15 `kn_unsup_current_01`

- **Expected behaviour:** abstain
- **Original question (Kannada):** ಇಂದು ಸೇಲಂನಲ್ಲಿ ಕಡಲೆಕಾಯಿಯ ಮಾರುಕಟ್ಟೆ ಬೆಲೆ ಎಷ್ಟು?
- **English reference question (dataset field):** What is the market price of groundnut in Salem today?
- **Reference answer (English):** *none (unsupported case; the system is expected to abstain with no citations)*
- **Gold terms:** *none*

**Review notes / corrections:**

> Reviewed manually; approved unchanged. No correction.

**Proposed corrected wording (if any):**

> No change (original wording approved).

### KN.16 `kn_unsup_adjacent_01`

- **Expected behaviour:** abstain
- **Original question (Kannada):** ಡ್ರೋನ್ ಮೂಲಕ ಭತ್ತಕ್ಕೆ ಕ್ಲೋರಾಂಟ್ರಾನಿಲಿಪ್ರೋಲ್ ಸಿಂಪಡಿಸಿದ ನಂತರ ಕೊಯ್ಲಿಗೆ ಮೊದಲು ಎಷ್ಟು ದಿನ ಕಾಯಬೇಕು?
- **English reference question (dataset field):** What is the waiting period before harvest after spraying chlorantraniliprole on rice with a drone?
- **Reference answer (English):** *none (unsupported case; the system is expected to abstain with no citations)*
- **Gold terms:** *none*

**Review notes / corrections:**

> Reviewed manually; approved unchanged. No correction.

**Proposed corrected wording (if any):**

> No change (original wording approved).
