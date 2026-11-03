"""CPU-first translation wrapper for the prescribed IndicTrans2 checkpoints.

The wrapper uses the locally cached Hugging Face checkpoints by default and
does not initiate model downloads. Run translation on individual sentences or
short batches; long inputs that exceed ``max_input_tokens`` are rejected rather
than silently truncated. Hindi↔Kannada translation uses English as a pivot.
"""

from __future__ import annotations

import logging
import os
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Mapping, Optional, Sequence, Tuple, Union

# Transformers 5.20.2 reads HF_MODULES_CACHE when transformers.utils.hub is
# imported. Set it before importing torch/transformers so custom code is
# materialized in the project's writable .cache/, not the user-profile cache.
INDIC_TRANS2_CACHE = Path(__file__).resolve().parents[1] / ".cache" / "huggingface" / "hub"
INDIC_TRANS2_MODULES_CACHE = INDIC_TRANS2_CACHE.parent / "modules"
os.environ["HF_MODULES_CACHE"] = str(INDIC_TRANS2_MODULES_CACHE)

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

from src.indic_processor import IndicProcessor


LOGGER = logging.getLogger(__name__)

LANGUAGE_CODES = {
    "en": "eng_Latn",
    "eng": "eng_Latn",
    "eng_latn": "eng_Latn",
    "hi": "hin_Deva",
    "hin": "hin_Deva",
    "hin_deva": "hin_Deva",
    "kn": "kan_Knda",
    "kan": "kan_Knda",
    "kan_knda": "kan_Knda",
}
LANGUAGE_NAMES = {"eng_Latn": "English", "hin_Deva": "Hindi", "kan_Knda": "Kannada"}

EN_INDIC_CHECKPOINT = "ai4bharat/indictrans2-en-indic-dist-200M"
INDIC_EN_CHECKPOINT = "ai4bharat/indictrans2-indic-en-dist-200M"
MEASUREMENT_TERMS = (
    "kg/ha",
    "kg/acre",
    "g/plant",
    "g/L",
    "mg/L",
    "ml/plant",
    "ml/L",
    "l/ha",
    "litres",
    "liters",
    "litre",
    "liter",
)


class TranslatorError(RuntimeError):
    """Base class for errors safe to surface to an application caller."""


class TranslatorModelLoadError(TranslatorError):
    """A prescribed checkpoint could not be loaded locally."""


class TranslatorInferenceError(TranslatorError):
    """Preprocessing, generation, decoding, or postprocessing failed."""


class UnsupportedLanguageError(ValueError):
    """The requested language is not one of English, Hindi, or Kannada."""


@dataclass
class _LoadedModel:
    tokenizer: object
    model: object


ModelLoader = Callable[[str, bool], Tuple[object, object]]


def _default_model_loader(checkpoint: str, local_files_only: bool) -> Tuple[object, object]:
    """Load one official checkpoint on CPU without CUDA or flash-attention."""
    tokenizer = AutoTokenizer.from_pretrained(
        checkpoint,
        trust_remote_code=True,
        local_files_only=local_files_only,
        cache_dir=str(INDIC_TRANS2_CACHE),
    )
    model = AutoModelForSeq2SeqLM.from_pretrained(
        checkpoint,
        trust_remote_code=True,
        local_files_only=local_files_only,
        cache_dir=str(INDIC_TRANS2_CACHE),
    )
    model.to("cpu")
    model.eval()
    return tokenizer, model


class IndicTrans2Translator:
    """Translate English, Hindi, and Kannada with official IndicTrans2 models.

    Args:
        processor: Existing IndicProcessor implementation. A fresh instance is
            created when omitted.
        local_files_only: Defaults to True to prevent accidental large downloads.
            Set False only when downloading checkpoints is explicitly intended.
        batch_size: Maximum number of sentences processed in one model batch.
        max_input_tokens: Maximum encoded input length. Longer input is rejected
            rather than silently truncated.
        num_beams: Beam count for deterministic generation.
        protected_terms: Additional crop names, varieties, or agricultural
            terms to carry unchanged through preprocessing and decoding.
        model_loader: Injection point for tests and controlled model loading.
        use_cache: Whether to use model key/value caching during generation.
    """

    def __init__(
        self,
        processor: Optional[IndicProcessor] = None,
        local_files_only: bool = True,
        batch_size: int = 8,
        max_input_tokens: int = 256,
        num_beams: int = 5,
        protected_terms: Sequence[str] = (),
        model_loader: Optional[ModelLoader] = None,
        use_cache: bool = True,
    ) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be at least 1")
        if max_input_tokens < 1:
            raise ValueError("max_input_tokens must be at least 1")
        if num_beams < 1:
            raise ValueError("num_beams must be at least 1")

        self._checkpoints = {
            "en_indic": EN_INDIC_CHECKPOINT,
            "indic_en": INDIC_EN_CHECKPOINT,
        }
        self._processor = processor or IndicProcessor(inference=True)
        self._local_files_only = local_files_only
        self._batch_size = batch_size
        self._max_input_tokens = max_input_tokens
        self._num_beams = num_beams
        self._use_cache = use_cache
        if isinstance(protected_terms, str):
            raise TypeError("protected_terms must be a sequence of complete terms, not one string")
        if any(not isinstance(term, str) or not term for term in protected_terms):
            raise ValueError("protected_terms must contain non-empty strings")
        self._protected_terms = tuple(
            sorted(set(MEASUREMENT_TERMS).union(protected_terms), key=len, reverse=True)
        )
        self._model_loader = model_loader or _default_model_loader
        self._models: Dict[str, _LoadedModel] = {}
        # IndicProcessor maintains a FIFO placeholder queue; serialize each
        # preprocess→infer→postprocess stage so concurrent calls cannot mix it.
        self._lock = threading.RLock()

    @staticmethod
    def _normalize_language(language: str) -> str:
        if not isinstance(language, str):
            raise UnsupportedLanguageError("Language code must be a string (en, hi, kn).")
        normalized = LANGUAGE_CODES.get(language.strip().lower())
        if normalized is None:
            raise UnsupportedLanguageError(
                "Unsupported language {!r}; use en/eng_Latn, hi/hin_Deva, or kn/kan_Knda.".format(language)
            )
        return normalized

    @staticmethod
    def _sentences(texts: Union[str, Sequence[str]]) -> Tuple[List[str], bool]:
        is_single = isinstance(texts, str)
        if is_single:
            values = [texts]
        elif isinstance(texts, Sequence) and not isinstance(texts, (bytes, bytearray)):
            values = list(texts)
        else:
            raise TypeError("text must be a string or a sequence of strings")
        if not all(isinstance(value, str) for value in values):
            raise TypeError("every item in text must be a string")
        return values, is_single

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate one sentence, returning a string in the target language."""
        translated = self.translate_batch([text], source_lang, target_lang)
        return translated[0]

    def translate_batch(
        self,
        texts: Union[str, Sequence[str]],
        source_lang: str,
        target_lang: str,
    ) -> Union[str, List[str]]:
        """Translate a sentence or sequence of sentences.

        A string input returns a string; a sequence returns a list. Empty
        batches return immediately without trying to load model checkpoints.
        """
        sentences, was_single = self._sentences(texts)
        src = self._normalize_language(source_lang)
        tgt = self._normalize_language(target_lang)
        if not sentences:
            return []
        if src == tgt:
            unchanged = list(sentences)
            return unchanged[0] if was_single else unchanged

        if src == "eng_Latn" or tgt == "eng_Latn":
            result = self._translate_stage(sentences, src, tgt)
        else:
            english = self._translate_stage(sentences, src, "eng_Latn")
            result = self._translate_stage(english, "eng_Latn", tgt)

        return result[0] if was_single else result

    def _translate_stage(self, sentences: Sequence[str], src: str, tgt: str) -> List[str]:
        direction = "en_indic" if src == "eng_Latn" else "indic_en"
        loaded = self._get_model(direction)
        translated: List[str] = []

        for offset in range(0, len(sentences), self._batch_size):
            batch = list(sentences[offset : offset + self._batch_size])
            with self._lock:
                try:
                    prepared_source, protected_map = self._protect_terms(batch)
                    prepared = self._processor.preprocess_batch(
                        prepared_source, src_lang=src, tgt_lang=tgt, visualize=False
                    )
                    model_inputs = loaded.tokenizer(
                        prepared,
                        padding=True,
                        truncation=False,
                        return_tensors="pt",
                    )
                    input_ids = model_inputs["input_ids"]
                    input_length = int(input_ids.shape[-1])
                    if input_length > self._max_input_tokens:
                        raise ValueError(
                            "Input encodes to {} tokens; limit is {}. Split it into shorter sentences.".format(
                                input_length, self._max_input_tokens
                            )
                        )

                    model_inputs = model_inputs.to("cpu")
                    with torch.inference_mode():
                        generated = loaded.model.generate(
                            **model_inputs,
                            num_beams=self._num_beams,
                            num_return_sequences=1,
                            max_length=256,
                            use_cache=self._use_cache,
                        )
                    decoded = loaded.tokenizer.batch_decode(
                        generated,
                        skip_special_tokens=True,
                        clean_up_tokenization_spaces=True,
                    )
                    processed = self._processor.postprocess_batch(
                        decoded,
                        lang=tgt,
                        visualize=False,
                        num_return_sequences=1,
                    )
                    processed = [self._restore_terms(text, protected_map) for text in processed]
                    if len(processed) != len(batch):
                        raise ValueError(
                            "Model returned {} translations for {} inputs".format(len(processed), len(batch))
                        )
                    translated.extend(processed)
                except TranslatorError:
                    self._clear_placeholder_queue()
                    raise
                except Exception as exc:
                    self._clear_placeholder_queue()
                    raise TranslatorInferenceError(
                        "IndicTrans2 translation failed for {} to {}: {}".format(
                            LANGUAGE_NAMES[src], LANGUAGE_NAMES[tgt], exc
                        )
                    ) from exc

        return translated

    def _get_model(self, direction: str) -> _LoadedModel:
        with self._lock:
            if direction in self._models:
                return self._models[direction]
            checkpoint = self._checkpoints[direction]
            try:
                tokenizer, model = self._model_loader(checkpoint, self._local_files_only)
            except Exception as exc:
                LOGGER.error(
                    "Could not load prescribed IndicTrans2 checkpoint %s (%s)",
                    checkpoint,
                    type(exc).__name__,
                )
                download_note = (
                    " Downloads are disabled by default; explicitly enable them only if intended."
                    if self._local_files_only
                    else ""
                )
                raise TranslatorModelLoadError(
                    "Could not load prescribed IndicTrans2 checkpoint '{}'. Confirm the complete checkpoint "
                    "is available in the Hugging Face cache.{}".format(
                        checkpoint, download_note
                    )
                ) from exc
            loaded = _LoadedModel(tokenizer=tokenizer, model=model)
            self._models[direction] = loaded
            return loaded

    def _clear_placeholder_queue(self) -> None:
        queue = getattr(self._processor, "_placeholder_entity_maps", None)
        if queue is None:
            return
        # The lock is held by the caller; draining avoids stale maps after a
        # failed stage, which otherwise could be restored into a later answer.
        while not queue.empty():
            queue.get_nowait()

    def _protect_terms(self, batch: Sequence[str]) -> Tuple[List[str], Dict[str, str]]:
        """Protect caller-specified crop/variety/agricultural terms as entities."""
        if not self._protected_terms:
            return list(batch), {}
        replacements: Dict[str, str] = {}
        prepared: List[str] = []
        term_index = 0
        for text in batch:
            def replace_match(match: re.Match) -> str:
                nonlocal term_index
                sentinel = "@AGRI_TERM_{}".format(term_index)
                term_index += 1
                replacements[sentinel] = match.group(0)
                return sentinel

            protected = text
            for term in self._protected_terms:
                pattern = re.compile(r"(?<!\w){}(?!\w)".format(re.escape(term)), re.IGNORECASE)
                protected = pattern.sub(replace_match, protected)
            prepared.append(protected)
        return prepared, replacements

    @staticmethod
    def _restore_terms(text: str, protected_map: Mapping[str, str]) -> str:
        for sentinel, original in protected_map.items():
            text = text.replace(sentinel, original)
        return text


Translator = IndicTrans2Translator

