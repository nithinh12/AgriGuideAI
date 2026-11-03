"""Tests for the Hindi/Kannada flow, the translation worker protocol and its client."""

from __future__ import annotations

import io
import json
import sys
import textwrap
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.streamlit_app import (
    LANGUAGE_OPTIONS,
    render_multilingual_result,
    submit_multilingual_question,
)
from src.multilingual_flow import answer_multilingual
from src.rag_pipeline import ABSTAIN_MESSAGE, AnswerResult
from src.translation_client import SubprocessTranslator, TranslationError
from src.translation_worker import handle_request, serve

HINDI_Q = "गेहूं की सिंचाई कब करनी चाहिए?"
KANNADA_Q = "ಗೋಧಿಗೆ ಯಾವಾಗ ನೀರಾವರಿ ಮಾಡಬೇಕು?"
ENGLISH_Q = "When should wheat be irrigated?"
ENGLISH_A = "Wheat irrigation is required at tillering and flowering stages."
HINDI_A = "गेहूं की सिंचाई कल्ले निकलने और फूल आने की अवस्था में आवश्यक है।"
KANNADA_A = "ಗೋಧಿಗೆ ಕವಲೊಡೆಯುವ ಮತ್ತು ಹೂಬಿಡುವ ಹಂತಗಳಲ್ಲಿ ನೀರಾವರಿ ಅಗತ್ಯ."


def _citation(page=17):
    return SimpleNamespace(
        doc_id="tnau_agriculture",
        title="Crop Production Guide — Agriculture 2020",
        organization="Tamil Nadu Agricultural University",
        page_number=page,
        excerpt=ENGLISH_A,
        url="https://example.org/agriculture.pdf",
        score=0.82,
    )


def _answered():
    return AnswerResult(
        question=ENGLISH_Q,
        mode="answered",
        answer_kind="extractive_evidence",
        answer_text=ENGLISH_A,
        sources=(_citation(),),
    )


class ScriptedTranslator:
    """Returns canned translations keyed by (source, target)."""

    def __init__(self, outputs):
        self.outputs = outputs
        self.calls = []

    def translate(self, text, source, target):
        return self.translate_batch([text], source, target)[0]

    def translate_batch(self, texts, source, target):
        self.calls.append((list(texts), source, target))
        result = self.outputs[(source, target)]
        if isinstance(result, Exception):
            raise result
        return [result] * len(texts) if isinstance(result, str) else list(result)


# --------------------------------------------------------------------------
# Flow
# --------------------------------------------------------------------------


def test_english_question_uses_rag_directly_and_never_touches_the_translator():
    translator = Mock()
    ask = Mock(return_value=_answered())

    result = answer_multilingual(ask, translator, "  " + ENGLISH_Q + "  ", "en")

    ask.assert_called_once_with(ENGLISH_Q)
    assert translator.mock_calls == []
    assert result.status == "english"
    assert result.english_result.answer_text == ENGLISH_A
    assert result.translated_answer is None


@pytest.mark.parametrize(
    "language,question,answer",
    [("hi", HINDI_Q, HINDI_A), ("kn", KANNADA_Q, KANNADA_A)],
)
def test_indic_question_is_translated_answered_in_english_and_translated_back(
    language, question, answer
):
    translator = ScriptedTranslator({(language, "en"): ENGLISH_Q, ("en", language): answer})
    ask = Mock(return_value=_answered())

    result = answer_multilingual(ask, translator, question, language)

    ask.assert_called_once_with(ENGLISH_Q)  # the existing English RAG saw English
    assert result.status == "translated"
    assert result.translated_answer == answer
    assert result.english_question == ENGLISH_Q
    assert result.original_question == question
    assert translator.calls[0] == ([question], language, "en")
    assert translator.calls[1] == ([ENGLISH_A], "en", language)


def test_citations_are_preserved_exactly_and_not_translated():
    original = _answered()
    translator = ScriptedTranslator({("hi", "en"): ENGLISH_Q, ("en", "hi"): HINDI_A})

    result = answer_multilingual(Mock(return_value=original), translator, HINDI_Q, "hi")

    assert result.english_result.sources == original.sources
    assert result.english_result.sources[0].page_number == 17
    assert result.english_result.sources[0].excerpt == ENGLISH_A
    # Only the answer text, never an excerpt or title, is sent for translation.
    assert [call[0] for call in translator.calls[1:]] == [[ENGLISH_A]]


def test_multi_sentence_answer_is_translated_sentence_by_sentence():
    answer = AnswerResult(
        question=ENGLISH_Q,
        mode="answered",
        answer_kind="extractive_evidence",
        answer_text="First irrigation at sowing. Second irrigation at tillering.",
        sources=(_citation(),),
    )
    translator = ScriptedTranslator(
        {("hi", "en"): ENGLISH_Q, ("en", "hi"): ["पहली सिंचाई बुवाई पर।", "दूसरी सिंचाई कल्ले निकलने पर।"]}
    )

    result = answer_multilingual(Mock(return_value=answer), translator, HINDI_Q, "hi")

    assert translator.calls[1][0] == [
        "First irrigation at sowing.",
        "Second irrigation at tillering.",
    ]
    assert result.translated_answer == "पहली सिंचाई बुवाई पर। दूसरी सिंचाई कल्ले निकलने पर।"


def test_abstention_is_translated_and_keeps_no_sources():
    abstained = AnswerResult(
        question=ENGLISH_Q,
        mode="abstained",
        answer_kind="abstention",
        answer_text=ABSTAIN_MESSAGE,
        warnings=("no evidence above min_score gate (0.41)",),
    )
    translator = ScriptedTranslator({("hi", "en"): ENGLISH_Q, ("en", "hi"): "ज्ञान आधार में पर्याप्त प्रमाण नहीं है।"})

    result = answer_multilingual(Mock(return_value=abstained), translator, HINDI_Q, "hi")

    assert result.status == "translated"
    assert result.english_result.mode == "abstained"
    assert result.english_result.sources == ()


def test_question_translation_failure_does_not_search_or_crash():
    translator = ScriptedTranslator({("hi", "en"): TranslationError("worker stopped")})
    ask = Mock()

    result = answer_multilingual(ask, translator, HINDI_Q, "hi")

    ask.assert_not_called()
    assert result.status == "translation_failed"
    assert result.english_result is None
    assert result.translated_answer is None
    assert "Hindi question could not be translated" in result.error


def test_answer_translation_failure_is_reported_not_presented_as_hindi():
    translator = ScriptedTranslator(
        {("hi", "en"): ENGLISH_Q, ("en", "hi"): TranslationError("model timed out")}
    )

    result = answer_multilingual(Mock(return_value=_answered()), translator, HINDI_Q, "hi")

    assert result.status == "translation_failed"
    assert result.translated_answer is None
    assert "could not be translated into Hindi" in result.error
    assert result.english_result.sources[0].page_number == 17


def test_unexpected_translator_exception_does_not_crash_the_flow():
    translator = ScriptedTranslator({("kn", "en"): RuntimeError("boom")})

    result = answer_multilingual(Mock(), translator, KANNADA_Q, "kn")

    assert result.status == "translation_failed"
    assert "unexpected translation error" in result.error


@pytest.mark.parametrize("bad", ["", "   ", "\n"])
def test_empty_question_translation_is_rejected(bad):
    translator = ScriptedTranslator({("hi", "en"): bad})
    ask = Mock()

    result = answer_multilingual(ask, translator, HINDI_Q, "hi")

    ask.assert_not_called()
    assert result.status == "translation_failed"
    assert "empty or invalid" in result.error


@pytest.mark.parametrize("bad", ["", "  ", "Wheat irrigation is required at tillering."])
def test_empty_or_untranslated_answer_output_is_rejected_for_hindi(bad):
    translator = ScriptedTranslator({("hi", "en"): ENGLISH_Q, ("en", "hi"): bad})

    result = answer_multilingual(Mock(return_value=_answered()), translator, HINDI_Q, "hi")

    assert result.status == "translation_failed"
    assert result.translated_answer is None


def test_hindi_text_is_not_accepted_as_a_kannada_answer():
    translator = ScriptedTranslator({("kn", "en"): ENGLISH_Q, ("en", "kn"): HINDI_A})

    result = answer_multilingual(Mock(return_value=_answered()), translator, KANNADA_Q, "kn")

    assert result.status == "translation_failed"


def test_rag_error_is_reported_without_translating_an_answer():
    error = AnswerResult(
        question=ENGLISH_Q,
        mode="error",
        answer_kind="error",
        answer_text="This question could not be processed.",
        warnings=("retrieval failed (RuntimeError)",),
    )
    translator = ScriptedTranslator({("hi", "en"): ENGLISH_Q})

    result = answer_multilingual(Mock(return_value=error), translator, HINDI_Q, "hi")

    assert result.status == "error"
    assert len(translator.calls) == 1


def test_unsupported_language_is_rejected():
    with pytest.raises(ValueError):
        answer_multilingual(Mock(), Mock(), "x", "fr")


# --------------------------------------------------------------------------
# Worker protocol (pure functions, no model)
# --------------------------------------------------------------------------


class EchoTranslator:
    def translate_batch(self, texts, source, target):
        return ["{}>{}:{}".format(source, target, text) for text in texts]


def test_worker_translates_and_reports_errors_per_request():
    translator = EchoTranslator()

    ok = handle_request(translator, {"id": 3, "op": "translate", "texts": [HINDI_Q], "source": "hi", "target": "en"})
    assert ok == {"id": 3, "ok": True, "translations": ["hi>en:" + HINDI_Q]}

    for bad in (
        {"id": 4, "op": "translate", "texts": "not a list", "source": "hi", "target": "en"},
        {"id": 5, "op": "explode"},
        "not an object",
    ):
        response = handle_request(translator, bad)
        assert response["ok"] is False and "error" in response

    class Failing:
        def translate_batch(self, *args):
            raise RuntimeError("model exploded")

    failed = handle_request(Failing(), {"id": 6, "op": "translate", "texts": ["x"], "source": "en", "target": "hi"})
    assert failed["ok"] is False and "model exploded" in failed["error"]


def test_worker_output_is_ascii_json_and_survives_bad_lines():
    lines = [
        json.dumps({"id": 1, "op": "translate", "texts": [KANNADA_Q], "source": "kn", "target": "en"}) + "\n",
        "this is not json\n",
        "\n",
        json.dumps({"id": 2, "op": "ping"}) + "\n",
    ]
    out = io.StringIO()

    serve(EchoTranslator(), lines, out)

    raw = out.getvalue()
    assert raw.isascii()  # no dependence on a console code page
    responses = [json.loads(line) for line in raw.splitlines()]
    assert responses[0]["translations"] == ["kn>en:" + KANNADA_Q]
    assert responses[1]["ok"] is False
    assert responses[2] == {"id": 2, "ok": True}


# --------------------------------------------------------------------------
# Client against a real subprocess speaking the same protocol
# --------------------------------------------------------------------------

FAKE_WORKER = textwrap.dedent(
    '''
    import json, os, sys, time
    mode = os.environ.get("FAKE_MODE", "ok")
    sys.stdin.reconfigure(encoding="utf-8"); sys.stdout.reconfigure(encoding="utf-8")
    if mode == "never_ready":
        time.sleep(60)
    if mode == "bad_start":
        print(json.dumps({"event": "error", "error": "ImportError: no torch"}), flush=True); sys.exit(1)
    print("noise before ready that is not json", flush=True)
    print(json.dumps({"event": "ready"}), flush=True)
    count = 0
    for line in sys.stdin:
        req = json.loads(line); count += 1
        if mode == "crash":
            sys.exit(3)
        if mode == "hang":
            time.sleep(60)
        if mode == "error":
            out = {"id": req["id"], "ok": False, "error": "model failed"}
        elif mode == "empty":
            out = {"id": req["id"], "ok": True, "translations": [""] * len(req["texts"])}
        elif mode == "malformed":
            out = {"id": req["id"], "ok": True, "translations": "oops"}
        elif mode == "short":
            out = {"id": req["id"], "ok": True, "translations": []}
        elif mode == "env":
            out = {"id": req["id"], "ok": True, "translations": [
                "token=" + str("HF_TOKEN" in os.environ) + " utf8=" + os.environ.get("PYTHONUTF8", "")
                + " offline=" + os.environ.get("HF_HUB_OFFLINE", "")] * len(req["texts"])}
        else:
            out = {"id": req["id"], "ok": True, "translations": ["%d|%s" % (count, t) for t in req["texts"]]}
        print(json.dumps(out, ensure_ascii=True), flush=True)
    '''
)


@pytest.fixture
def fake_worker(tmp_path, monkeypatch):
    script = tmp_path / "fake_worker.py"
    script.write_text(FAKE_WORKER, encoding="utf-8")
    created = []

    def make(mode="ok", **kwargs):
        monkeypatch.setenv("FAKE_MODE", mode)
        translator = SubprocessTranslator(command=[sys.executable, str(script)], **kwargs)
        created.append(translator)
        return translator

    yield make
    for translator in created:
        translator.close()


def test_client_round_trips_devanagari_and_kannada_exactly(fake_worker):
    translator = fake_worker()

    hindi = translator.translate(HINDI_Q + " 50-60 kg/ha", "hi", "en")
    kannada = translator.translate(KANNADA_A, "kn", "en")

    assert hindi == "1|" + HINDI_Q + " 50-60 kg/ha"
    assert kannada == "2|" + KANNADA_A  # same worker process, no model reload


def test_client_serves_repeated_requests_from_cache_without_calling_the_worker(fake_worker):
    translator = fake_worker()

    first = translator.translate("hello there", "en", "hi")
    second = translator.translate("hello there", "en", "hi")

    assert first == second == "1|hello there"


def test_client_same_language_is_a_no_op_without_starting_a_worker(fake_worker):
    translator = fake_worker()

    assert translator.translate("hello", "en", "en") == "hello"
    assert translator._process is None


def test_client_rejects_unsupported_language(fake_worker):
    with pytest.raises(TranslationError, match="Unsupported language"):
        fake_worker().translate("hello", "en", "fr")


@pytest.mark.parametrize(
    "mode,message",
    [
        ("error", "could not translate"),
        ("empty", "empty translation"),
        ("malformed", "malformed"),
        ("short", "malformed"),
    ],
)
def test_client_rejects_failed_empty_and_malformed_worker_output(fake_worker, mode, message):
    with pytest.raises(TranslationError, match=message):
        fake_worker(mode).translate("hello", "en", "hi")


def test_client_reports_a_crashing_worker_and_restarts_on_the_next_request(fake_worker, monkeypatch):
    translator = fake_worker("crash")
    with pytest.raises(TranslationError, match="stopped unexpectedly"):
        translator.translate("hello", "en", "hi")

    monkeypatch.setenv("FAKE_MODE", "ok")
    assert translator.translate("hello again", "en", "hi") == "1|hello again"


def test_client_times_out_a_hung_worker(fake_worker):
    translator = fake_worker("hang", request_timeout=1.0)

    with pytest.raises(TranslationError, match="did not respond in time"):
        translator.translate("hello", "en", "hi")
    assert translator._process is None  # the stuck process was killed


def test_client_reports_startup_failures(fake_worker):
    with pytest.raises(TranslationError, match="failed to start: ImportError"):
        fake_worker("bad_start").translate("hello", "en", "hi")
    with pytest.raises(TranslationError, match="did not respond in time"):
        fake_worker("never_ready", startup_timeout=1.0).translate("hello", "en", "hi")


def test_client_reports_a_missing_translation_environment(tmp_path):
    translator = SubprocessTranslator(python_executable=tmp_path / "missing" / "python.exe")

    with pytest.raises(TranslationError, match="translation environment was not found"):
        translator.translate("hello", "en", "hi")


def test_worker_environment_is_utf8_offline_and_has_no_secrets(fake_worker, monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "hf_example_not_a_real_token")
    monkeypatch.setenv("SOME_API_KEY", "x")

    output = fake_worker("env").translate("hello", "en", "hi")

    assert output == "token=False utf8=1 offline=1"


# --------------------------------------------------------------------------
# Presentation
# --------------------------------------------------------------------------


class FakeUI:
    def __init__(self):
        self.messages = []

    def __getattr__(self, name):
        def record(*args, **kwargs):
            self.messages.append((name, args, kwargs))

        return record

    def text(self):
        return "\n".join(" ".join(str(a) for a in args) for _, args, _ in self.messages)

    def kinds(self):
        return [name for name, _, _ in self.messages]


def test_language_selector_offers_english_hindi_and_kannada():
    assert set(LANGUAGE_OPTIONS.values()) == {"en", "hi", "kn"}
    assert any("हिन्दी" in label for label in LANGUAGE_OPTIONS)
    assert any("ಕನ್ನಡ" in label for label in LANGUAGE_OPTIONS)


def test_translated_answer_is_labeled_and_kept_apart_from_english_sources():
    translator = ScriptedTranslator({("hi", "en"): ENGLISH_Q, ("en", "hi"): HINDI_A})
    result = answer_multilingual(Mock(return_value=_answered()), translator, HINDI_Q, "hi")
    ui = FakeUI()

    render_multilingual_result(ui, result)

    text = ui.text()
    assert "machine-translated to Hindi" in text
    assert HINDI_A in text
    assert "Original English evidence" in text
    assert "written in English" in text and "not translated" in text
    assert "Page 17" in text
    assert "Crop Production Guide — Agriculture 2020" in text
    assert ENGLISH_A in text  # excerpt is shown verbatim in English


def test_failed_translation_is_an_error_and_english_text_is_not_called_a_hindi_answer():
    translator = ScriptedTranslator(
        {("hi", "en"): ENGLISH_Q, ("en", "hi"): TranslationError("worker stopped unexpectedly")}
    )
    result = answer_multilingual(Mock(return_value=_answered()), translator, HINDI_Q, "hi")
    ui = FakeUI()

    render_multilingual_result(ui, result)

    text = ui.text()
    assert "error" in ui.kinds()
    assert "Translation unavailable" in text
    assert "NOT a Hindi answer" in text
    assert "success" not in ui.kinds()


def test_failed_question_translation_shows_error_and_no_sources():
    translator = ScriptedTranslator({("kn", "en"): TranslationError("worker stopped unexpectedly")})
    result = answer_multilingual(Mock(), translator, KANNADA_Q, "kn")
    ui = FakeUI()

    render_multilingual_result(ui, result)

    assert "Translation unavailable" in ui.text()
    assert "Sources" not in ui.text()


def test_app_submit_routes_english_directly_and_indic_through_translation():
    pipeline = Mock()
    pipeline.answer.return_value = _answered()
    translator = ScriptedTranslator({("kn", "en"): ENGLISH_Q, ("en", "kn"): KANNADA_A})

    english = submit_multilingual_question(pipeline, translator, ENGLISH_Q, "en")
    assert english.status == "english" and translator.calls == []

    kannada = submit_multilingual_question(pipeline, translator, KANNADA_Q, "kn")
    assert kannada.status == "translated" and kannada.translated_answer == KANNADA_A
    assert pipeline.answer.call_args_list[-1].args == (ENGLISH_Q,)
