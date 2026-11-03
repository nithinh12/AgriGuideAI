"""Mocked tests for the IndicTrans2 wrapper; no checkpoints are downloaded."""

import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence

import pytest
import torch

from src.translator import (
    EN_INDIC_CHECKPOINT,
    INDIC_EN_CHECKPOINT,
    INDIC_TRANS2_CACHE,
    INDIC_TRANS2_MODULES_CACHE,
    IndicTrans2Translator,
    TranslatorInferenceError,
    TranslatorModelLoadError,
    UnsupportedLanguageError,
)
import src.translator as translator_module


class FakeBatch(dict):
    def to(self, device):
        assert device == "cpu"
        return self


class FakeTokenizer:
    def __init__(self, decoded: Sequence[str], encoded_length: int = 8):
        self.decoded = list(decoded)
        self.encoded_length = encoded_length
        self.prepared = []
        self.decode_args = None

    def __call__(self, texts, **kwargs):
        assert kwargs["truncation"] is False
        self.prepared = list(texts)
        return FakeBatch(input_ids=torch.ones((len(texts), self.encoded_length), dtype=torch.long))

    def batch_decode(self, generated, **kwargs):
        self.decode_args = kwargs
        return self.decoded


class FakeModel:
    def __init__(self, fail=False):
        self.fail = fail
        self.generate_args = None

    def generate(self, **kwargs):
        self.generate_args = kwargs
        if self.fail:
            raise RuntimeError("simulated generation error")
        return torch.zeros((kwargs["input_ids"].shape[0], 2), dtype=torch.long)


class FakeProcessor:
    def __init__(self):
        self.calls = []
        self._placeholder_entity_maps = None

    def preprocess_batch(self, batch, src_lang, tgt_lang, visualize=False):
        self.calls.append(("pre", src_lang, tgt_lang, list(batch)))
        return ["{} {} {}".format(src_lang, tgt_lang, item) for item in batch]

    def postprocess_batch(self, batch, lang, visualize=False, num_return_sequences=1):
        self.calls.append(("post", lang, list(batch)))
        return list(batch)


def make_translator(outputs, fail_direction=None, encoded_length=8, use_cache=True):
    processor = FakeProcessor()
    loaded = {}
    calls = []

    def loader(checkpoint, local_files_only):
        calls.append((checkpoint, local_files_only))
        direction = "en_indic" if checkpoint == EN_INDIC_CHECKPOINT else "indic_en"
        decoded = outputs[direction].pop(0)
        tokenizer = FakeTokenizer(decoded, encoded_length=encoded_length)
        model = FakeModel(fail=(direction == fail_direction))
        loaded.setdefault(direction, []).append((tokenizer, model))
        return tokenizer, model

    translator = IndicTrans2Translator(
        processor=processor,
        model_loader=loader,
        use_cache=use_cache,
    )
    return translator, processor, calls, loaded


@pytest.mark.parametrize(
    "source,target,direction,expected",
    [
        ("en", "hi", "en_indic", "हिंदी"),
        ("en", "kn", "en_indic", "ಕನ್ನಡ"),
        ("hi", "en", "indic_en", "English"),
        ("kn", "en", "indic_en", "English"),
    ],
)
def test_direct_language_pairs_use_prescribed_checkpoint(source, target, direction, expected):
    outputs = {"en_indic": [], "indic_en": []}
    outputs[direction].append([expected])
    translator, processor, calls, loaded = make_translator(outputs)

    assert translator.translate("sample sentence", source, target) == expected
    expected_checkpoint = EN_INDIC_CHECKPOINT if direction == "en_indic" else INDIC_EN_CHECKPOINT
    assert calls == [(expected_checkpoint, True)]
    assert processor.calls[0][1:3] == (
        {"en": "eng_Latn", "hi": "hin_Deva", "kn": "kan_Knda"}[source],
        {"en": "eng_Latn", "hi": "hin_Deva", "kn": "kan_Knda"}[target],
    )
    model = loaded[direction][0][1]
    assert model.generate_args["num_beams"] == 5
    assert model.generate_args["use_cache"] is True
    assert "flash_attn" not in model.generate_args


def test_use_cache_defaults_to_true_and_preserves_default_translation_behavior():
    outputs = {"en_indic": [["हिंदी"]], "indic_en": []}
    translator, _, _, loaded = make_translator(outputs)

    assert translator._use_cache is True
    assert translator.translate("sample sentence", "en", "hi") == "हिंदी"
    assert loaded["en_indic"][0][1].generate_args["use_cache"] is True


def test_explicit_use_cache_false_is_preserved_and_forwarded():
    outputs = {"en_indic": [["हिंदी"]], "indic_en": []}
    translator, _, _, loaded = make_translator(outputs, use_cache=False)

    assert translator._use_cache is False
    assert translator.translate("sample sentence", "en", "hi") == "हिंदी"
    assert loaded["en_indic"][0][1].generate_args["use_cache"] is False


@pytest.mark.parametrize("source,target", [("hi", "kn"), ("kn", "hi")])
def test_indic_to_indic_uses_english_pivot(source, target):
    outputs = {"en_indic": [["local translation"]], "indic_en": [["English pivot"]]}
    translator, processor, calls, _ = make_translator(outputs)

    assert translator.translate("ಸ್ಥಳೀಯ ಪಠ್ಯ", source, target) == "local translation"
    assert calls == [(INDIC_EN_CHECKPOINT, True), (EN_INDIC_CHECKPOINT, True)]
    assert [(call[1], call[2]) for call in processor.calls if call[0] == "pre"] == [
        ({"hi": "hin_Deva", "kn": "kan_Knda"}[source], "eng_Latn"),
        ("eng_Latn", {"hi": "hin_Deva", "kn": "kan_Knda"}[target]),
    ]


def test_batch_input_and_language_aliases():
    outputs = {"en_indic": [["अनुवाद एक", "अनुवाद दो"]], "indic_en": []}
    translator, _, _, _ = make_translator(outputs)
    assert translator.translate_batch(["one", "two"], "eng_Latn", "hin_Deva") == [
        "अनुवाद एक",
        "अनुवाद दो",
    ]


def test_empty_and_identity_translation_do_not_load_models():
    translator, _, calls, _ = make_translator({"en_indic": [], "indic_en": []})
    assert translator.translate_batch([], "en", "hi") == []
    assert translator.translate_batch(["unchanged"], "hi", "hin_Deva") == ["unchanged"]
    assert calls == []


def test_invalid_language_fails_before_checkpoint_load():
    translator, _, calls, _ = make_translator({"en_indic": [], "indic_en": []})
    with pytest.raises(UnsupportedLanguageError, match="Unsupported language"):
        translator.translate("text", "ta", "en")
    assert calls == []


def test_missing_checkpoint_is_reported_without_network_download():
    def missing_loader(checkpoint, local_files_only):
        assert local_files_only is True
        raise OSError("not found in local cache")

    translator = IndicTrans2Translator(processor=FakeProcessor(), model_loader=missing_loader)
    with pytest.raises(TranslatorModelLoadError, match="Could not load prescribed IndicTrans2 checkpoint"):
        translator.translate("text", "en", "hi")


def test_default_loader_requests_local_cpu_model_without_acceleration(monkeypatch):
    calls = []

    class Model:
        device = None
        evaluated = False

        def to(self, device):
            self.device = device
            return self

        def eval(self):
            self.evaluated = True
            return self

    model = Model()
    tokenizer_object = object()

    class Factory:
        @staticmethod
        def from_pretrained(checkpoint, **kwargs):
            calls.append((checkpoint, kwargs))
            return tokenizer_object if len(calls) == 1 else model

    # The module-level factories are patched so this check cannot access the
    # network or inspect a real checkpoint.
    monkeypatch.setattr(translator_module, "AutoTokenizer", Factory)
    monkeypatch.setattr(translator_module, "AutoModelForSeq2SeqLM", Factory)
    tokenizer, loaded_model = translator_module._default_model_loader(EN_INDIC_CHECKPOINT, True)

    assert tokenizer is tokenizer_object
    assert loaded_model.device == "cpu"
    assert loaded_model.evaluated is True
    assert len(calls) == 2
    assert all(call[0] == EN_INDIC_CHECKPOINT for call in calls)
    assert all(call[1]["local_files_only"] is True for call in calls)
    assert all(call[1]["trust_remote_code"] is True for call in calls)
    assert all(call[1]["cache_dir"] == str(INDIC_TRANS2_CACHE) for call in calls)
    assert all("attn_implementation" not in call[1] for call in calls)


def test_transformers_custom_code_cache_is_set_before_import_in_fresh_process():
    project_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env.pop("HF_MODULES_CACHE", None)
    code = (
        "import os, sys; "
        "assert 'transformers' not in sys.modules; "
        "import src.translator as t; "
        "import transformers.utils.hub as h; "
        "assert os.environ['HF_MODULES_CACHE'] == str(t.INDIC_TRANS2_MODULES_CACHE); "
        "assert h.HF_MODULES_CACHE == str(t.INDIC_TRANS2_MODULES_CACHE); "
        "print(h.HF_MODULES_CACHE)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(project_root),
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == str(INDIC_TRANS2_MODULES_CACHE)


def test_inference_error_is_wrapped_and_placeholder_queue_is_cleared():
    processor = FakeProcessor()

    class Queue:
        def __init__(self):
            self.items = ["stale"]

        def empty(self):
            return not self.items

        def get_nowait(self):
            return self.items.pop(0)

    processor._placeholder_entity_maps = Queue()
    translator = IndicTrans2Translator(
        processor=processor,
        model_loader=lambda checkpoint, local: (FakeTokenizer(["unused"]), FakeModel(fail=True)),
    )
    with pytest.raises(TranslatorInferenceError, match="translation failed"):
        translator.translate("text", "en", "hi")
    assert processor._placeholder_entity_maps.empty()


def test_long_encoded_input_is_rejected_instead_of_truncated():
    translator, _, _, _ = make_translator(
        {"en_indic": [["unused"]], "indic_en": []}, encoded_length=300
    )
    with pytest.raises(TranslatorInferenceError, match="Split it into shorter sentences"):
        translator.translate("long input", "en", "hi")


def test_real_processor_restores_protected_measurement_with_mocked_model():
    tokenizer = FakeTokenizer(["< ID1 > < ID2 > < ID3 >"])
    model = FakeModel()
    translator = IndicTrans2Translator(
        protected_terms=("wheat",),
        model_loader=lambda checkpoint, local: (tokenizer, model),
    )

    result = translator.translate("Apply 50-60 kg/ha to wheat.", "en", "hi")
    assert "50-60" in result
    assert "wheat" in result
    assert "kg/ha" in result
    assert "50-60" not in tokenizer.prepared[0]
    assert "wheat" not in tokenizer.prepared[0]
    assert tokenizer.decode_args["skip_special_tokens"] is True

