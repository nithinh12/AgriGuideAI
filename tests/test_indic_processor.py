# -*- coding: utf-8 -*-
"""Tests for src/indic_processor.py — the pure-Python Windows port of the official
IndicTransToolkit IndicProcessor (MIT, Copyright (c) Varun Gumma).

All expected values were observed by executing the code on 2026-10-29. The same
cases are cross-checked against the official Cython build (WSL2) by
tests/differential/run_processor_cases.py + compare_processor_runs.py.

Official behaviors documented here but intentionally NOT executed:
  * postprocess_batch with an empty placeholder queue blocks forever — the
    official source calls queue.Queue.get() with no timeout. Never call it out
    of sequence (every postprocess test below first queues the needed maps).
  * preprocess_batch with a src_lang lacking "_" SIGSEGVs in the official Cython
    build (verified 2026-10-29 in WSL2); the shim raises IndexError instead —
    a safe divergence on invalid input only (asserted below).
  * non-string input raises TypeError in BOTH the official build (verified,
    WSL2) and this shim.
"""

import pytest

from src.indic_processor import IndicProcessor


@pytest.fixture
def ip() -> IndicProcessor:
    """Fresh processor per test — the placeholder queue is FIFO and must start empty."""
    return IndicProcessor(inference=True)


def _has_devanagari(s: str) -> bool:
    return any("ऀ" <= c <= "ॿ" for c in s)


def _has_kannada(s: str) -> bool:
    return any("ಀ" <= c <= "೿" for c in s)


class TestLanguageCodes:
    def test_source_tag_prefix(self, ip):
        out = ip.preprocess_batch(["Hello world."], "eng_Latn", "hin_Deva")
        assert out == ["eng_Latn hin_Deva Hello world ."]

    def test_is_target_omits_prefix(self, ip):
        out = ip.preprocess_batch(["Hello world."], "eng_Latn", "hin_Deva", is_target=True)
        assert out == ["Hello world ."]

    def test_default_tgt_lang_is_none(self, ip):
        # Official behavior: tgt_lang defaults to None and shows up in the tag.
        out = ip.preprocess_batch(["Hello world."], "eng_Latn")
        assert out == ["eng_Latn None Hello world ."]


class TestEmptyInput:
    def test_empty_batch(self, ip):
        assert ip.preprocess_batch([], "eng_Latn", "hin_Deva") == []
        assert ip.postprocess_batch([], lang="hin_Deva") == []

    def test_empty_string_sentence(self, ip):
        # Trailing space comes from the official f-string tag construction.
        out = ip.preprocess_batch([""], "eng_Latn", "hin_Deva")
        assert out == ["eng_Latn hin_Deva "]
        post = ip.postprocess_batch(out, lang="eng_Latn")
        assert len(post) == 1 and isinstance(post[0], str)


class TestEnHiRoundtrip:
    def test_english_range_wrapped_then_restored(self, ip):
        src = "Apply 50-60 kg nitrogen to wheat."
        pre = ip.preprocess_batch([src], "eng_Latn", "hin_Deva")[0]
        assert pre.startswith("eng_Latn hin_Deva ")
        assert "50-60" not in pre          # wrapped into a placeholder
        assert "< ID1 >" in pre            # Moses splits <ID1> into < ID1 >
        body = pre.split("hin_Deva ", 1)[1]
        out = ip.postprocess_batch([body], lang="hin_Deva")[0]
        assert out == "Apply 50-60 kg nitrogen to wheat."  # observed

    def test_hindi_digits_normalized_and_restored(self, ip):
        pre = ip.preprocess_batch(
            ["गेहूँ में १००-१५० किग्रा यूरिया डालें।"], "hin_Deva", "eng_Latn"
        )[0]
        assert pre.startswith("hin_Deva eng_Latn ")
        assert "100-150" not in pre        # wrapped
        assert "< ID1 >" in pre
        body = pre.split("eng_Latn ", 1)[1]
        out = ip.postprocess_batch([body], lang="hin_Deva")[0]
        assert "100-150" in out
        assert out.startswith("गेहूँ में")


class TestKannadaPivot:
    def test_kn_source_transliterates_to_devanagari(self, ip):
        out = ip.preprocess_batch(
            ["ಬಿತ್ತನೆಯ ೫೦-೬೦ ದಿನಗಳಲ್ಲಿ ನೀರಿಡಬೇಕು।"], "kan_Knda", "eng_Latn"
        )[0]
        assert out.startswith("kan_Knda eng_Latn ")
        # Official design: Kannada source is transliterated to the Devanagari pivot.
        assert _has_devanagari(out)
        assert not _has_kannada(out)
        assert "< ID1 >" in out            # 50-60 wrapped as placeholder

    def test_kn_target_output_restored_keeps_kannada(self, ip):
        ip.preprocess_batch(
            ["ಬಿತ್ತನೆಯ ೫೦-೬೦ ದಿನಗಳಲ್ಲಿ ನೀರಿಡಬೇಕು।"], "kan_Knda", "eng_Latn"
        )  # queues the source placeholder map
        out = ip.postprocess_batch(
            ["ಬಿತ್ತನೆಯ <ID1> ದಿನಗಳಲ್ಲಿ ನೀರಿಡಬೇಕು।"], lang="kan_Knda"
        )[0]
        assert out == "ಬಿತ್ತನೆಯ 50-60 ದಿನಗಳಲ್ಲಿ ನೀರಿಡಬೇಕು।"  # observed
        assert _has_kannada(out)


class TestNumbersAndQuantities:
    def test_indic_digits_become_ascii(self, ip):
        hi = ip.preprocess_batch(["गेहूँ में १५० किग्रा।"], "hin_Deva", "eng_Latn")[0]
        assert "150" in hi and "१५०" not in hi
        kn = ip.preprocess_batch(["೧೨೩ ಕಿಗ್ರಾ"], "kan_Knda", "eng_Latn")[0]
        assert "123" in kn and "೧೨೩" not in kn
        en = ip.preprocess_batch(["123 kg"], "eng_Latn", "hin_Deva")[0]
        assert "123" in en

    def test_agri_quantities_partial_wrap_and_restore(self, ip):
        pre = ip.preprocess_batch(
            ["Apply 150 kg/ha nitrogen at 50-60 days."], "eng_Latn", "hin_Deva"
        )[0]
        assert "150 kg" in pre             # plain quantity stays literal
        assert "50-60" not in pre          # range becomes placeholder
        assert "< ID1 >" in pre
        body = pre.split("hin_Deva ", 1)[1]
        restored = ip.postprocess_batch([body], lang="hin_Deva")[0]
        assert "150 kg" in restored
        assert "50-60 days" in restored

    def test_percent_normalized_not_wrapped(self, ip):
        # '5 %' is normalized to '5%' by the punct rules; Moses tokenization
        # then renders percent with a space (observed: '5 %' / '25 %').
        p1 = ip.preprocess_batch(["Mix 5 % Captan fungicide."], "eng_Latn", "hin_Deva")[0]
        assert "5 %" in p1 and "<" not in p1
        p2 = ip.preprocess_batch(["Spray 25% neem oil on cotton."], "eng_Latn", "hin_Deva")[0]
        assert "25 %" in p2 and "<" not in p2


class TestUnicode:
    def test_punctuation_normalized(self, ip):
        out = ip.preprocess_batch(
            ["Quoted \u201cWheat\u201d \u2014 irrigate at tillering\u2026"],
            "eng_Latn", "hin_Deva", is_target=True,
        )[0]
        assert out == 'Quoted " Wheat " - irrigate at tillering ...'  # observed
        assert "\u2014" not in out and "\u201c" not in out


class TestErrorHandling:
    def test_target_lang_without_underscore_raises_valueerror(self, ip):
        # A map must be queued first: the official postprocess pops before it
        # validates the language code (and an empty queue would block forever).
        ip.preprocess_batch(["Hello."], "eng_Latn", "hin_Deva")
        with pytest.raises(ValueError):
            ip.postprocess_batch(["x"], lang="hin")

    def test_source_lang_without_underscore_raises_indexerror(self, ip):
        # The official Cython build SIGSEGVs on this input (verified, WSL2);
        # the shim must fail safe instead.
        with pytest.raises(IndexError):
            ip.preprocess_batch(["x"], "hin", "eng_Latn")

    def test_non_string_input_raises_typeerror(self, ip):
        # The official build raises TypeError on this too (verified, WSL2).
        with pytest.raises(TypeError):
            ip.preprocess_batch([None], "eng_Latn", "hin_Deva")


class TestQueueAccounting:
    def test_postprocess_consumes_one_map_per_input(self, ip):
        ip.preprocess_batch(
            ["A 50-60 day cycle.", "Spray 25% solution."], "eng_Latn", "hin_Deva"
        )
        assert not ip._placeholder_entity_maps.empty()
        out = ip.postprocess_batch(
            ["A <ID1> day cycle.", "Spray solution."], lang="eng_Latn"
        )
        assert "50-60" in out[0]
        assert out[1] == "Spray solution."
        # Private check documents FIFO accounting: 2 in, 2 out (leak = bug).
        assert ip._placeholder_entity_maps.empty()

    def test_num_return_sequences_shares_one_map(self, ip):
        ip.preprocess_batch(["Nitrogen dose 50-60 kg/ha."], "eng_Latn", "hin_Deva")
        out = ip.postprocess_batch(
            ["Nitrogen dose <ID1> kg/ha.", "Nitrogen dose <ID1> kg/ha also."],
            lang="eng_Latn",
            num_return_sequences=2,
        )
        assert len(out) == 2
        assert all("50-60" in s for s in out)
        assert ip._placeholder_entity_maps.empty()
