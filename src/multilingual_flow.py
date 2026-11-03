"""Question → English RAG → answer translation for Hindi and Kannada.

English questions go straight to the existing RAG path with no translation.
Hindi and Kannada questions are translated to English, answered by the same
English pipeline, and the answer text is translated back. Citations always come
from the English pipeline result unchanged: the source documents are English,
so excerpts, titles and page numbers are never translated or altered.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Literal, Optional, Tuple

from src.rag_pipeline import AnswerResult
from src.text_chunker import split_sentences
from src.translation_client import TranslationError

LOGGER = logging.getLogger(__name__)

LANGUAGE_NAMES = {"en": "English", "hi": "Hindi", "kn": "Kannada"}
# Unicode blocks used to confirm that "translated" text is really in the target script.
_SCRIPT_RANGES = {"hi": (0x0900, 0x097F), "kn": (0x0C80, 0x0CFF)}
_MIN_TARGET_SCRIPT_RATIO = 0.3

Status = Literal["english", "translated", "translation_failed", "error"]


@dataclass(frozen=True)
class MultilingualResult:
    """Everything the UI needs to show one answer in the selected language."""

    language: str
    original_question: str
    status: Status
    english_question: Optional[str] = None
    english_result: Optional[AnswerResult] = None
    translated_answer: Optional[str] = None
    error: Optional[str] = None
    warnings: Tuple[str, ...] = ()


def _target_script_ratio(text: str, language: str) -> float:
    low, high = _SCRIPT_RANGES[language]
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for ch in letters if low <= ord(ch) <= high) / len(letters)


def _check_english(text: str) -> str:
    english = text.strip()
    if not english or not any(ch.isascii() and ch.isalpha() for ch in english):
        raise TranslationError("The question translation was empty or invalid.")
    return english


def _check_target_language(text: str, language: str) -> str:
    translated = text.strip()
    if not translated or _target_script_ratio(translated, language) < _MIN_TARGET_SCRIPT_RATIO:
        raise TranslationError(
            "The answer translation was empty or not in {}.".format(LANGUAGE_NAMES[language])
        )
    return translated


def _reason(exc: Exception) -> str:
    if isinstance(exc, TranslationError):
        return str(exc)
    return "An unexpected translation error occurred ({}).".format(type(exc).__name__)


# PDF tables and bullet lists reach the answer as one run-on "sentence" of 100+
# words. Recorded translation time per word rose steeply with sentence length
# (about 0.2-0.4 s/word up to ~35 words, 0.8-0.9 s/word at 66-123 words), and a
# 106-word run-on made the Hindi and Kannada tomato-spacing answers exceed the
# 300 s request limit. Longer sentences are therefore translated as clause-sized
# units. Words are never added, dropped or reordered.
MAX_TRANSLATION_WORDS = 40
MIN_TRANSLATION_WORDS = 15
_NEVER_START_UNIT = frozenset({"x", "×"})


def _can_cut(words: list, index: int) -> bool:
    """May a unit end just before ``words[index]``? Not inside a number, unit or "60 x 45"."""
    nearby = words[max(0, index - 2) : index + 2]
    return not any(ch.isdigit() for word in nearby for ch in word) and (
        words[index].lower() not in _NEVER_START_UNIT
    )


def split_for_translation(sentence: str) -> list:
    """Split a sentence over ``MAX_TRANSLATION_WORDS`` words into clause-sized units."""
    words = sentence.split()
    if len(words) <= MAX_TRANSLATION_WORDS:
        return [sentence]
    units = []
    start = 0
    while len(words) - start > MAX_TRANSLATION_WORDS:
        window = range(start + MAX_TRANSLATION_WORDS, start + MIN_TRANSLATION_WORDS - 1, -1)
        cut = next(
            (
                i
                for i in window
                if _can_cut(words, i) and (words[i - 1][-1] in ",;:" or words[i] == "•")
            ),
            None,
        )
        if cut is None:  # next best: a capitalised word usually starts a new heading or item
            cut = next((i for i in window if _can_cut(words, i) and words[i][:1].isupper()), None)
        if cut is None:
            cut = next((i for i in window if _can_cut(words, i)), start + MAX_TRANSLATION_WORDS)
        units.append(" ".join(words[start:cut]))
        start = cut
    units.append(" ".join(words[start:]))
    return units


def _translate_answer(translator, answer_text: str, language: str) -> str:
    sentences = split_sentences(answer_text) or [answer_text]
    units = [unit for sentence in sentences for unit in split_for_translation(sentence)]
    translated = translator.translate_batch(units, "en", language)
    return _check_target_language(" ".join(translated), language)


def answer_multilingual(
    ask: Callable[[str], AnswerResult],
    translator,
    question: str,
    language: str,
) -> MultilingualResult:
    """Answer ``question`` written in ``language`` (en, hi or kn).

    ``ask`` runs the existing English RAG pipeline and never raises. Translation
    failures never crash the flow and are never reported as successful
    answers in the selected language.
    """
    question = question.strip()
    if language not in LANGUAGE_NAMES:
        raise ValueError("Unsupported language {!r}".format(language))

    if language == "en":
        return MultilingualResult(
            language="en",
            original_question=question,
            status="english",
            english_question=question,
            english_result=ask(question),
        )

    name = LANGUAGE_NAMES[language]
    try:
        english_question = _check_english(translator.translate(question, language, "en"))
    except Exception as exc:  # never let a translation problem crash the app
        LOGGER.warning("%s question translation failed (%s)", name, type(exc).__name__)
        return MultilingualResult(
            language=language,
            original_question=question,
            status="translation_failed",
            error="Your {} question could not be translated into English, so nothing was "
            "searched. {}".format(name, _reason(exc)),
        )

    english_result = ask(english_question)
    if english_result.mode == "error":
        return MultilingualResult(
            language=language,
            original_question=question,
            status="error",
            english_question=english_question,
            english_result=english_result,
            error=english_result.answer_text,
            warnings=english_result.warnings,
        )

    try:
        translated = _translate_answer(translator, english_result.answer_text, language)
    except Exception as exc:
        LOGGER.warning("%s answer translation failed (%s)", name, type(exc).__name__)
        return MultilingualResult(
            language=language,
            original_question=question,
            status="translation_failed",
            english_question=english_question,
            english_result=english_result,
            error="The answer could not be translated into {}. {}".format(name, _reason(exc)),
            warnings=english_result.warnings,
        )

    return MultilingualResult(
        language=language,
        original_question=question,
        status="translated",
        english_question=english_question,
        english_result=english_result,
        translated_answer=translated,
        warnings=english_result.warnings,
    )
