"""Client for the persistent IndicTrans2 worker (``src.translation_worker``).

The production environment cannot import the IndicTrans2 checkpoints (its
transformers 5.x is incompatible with their remote code), so translation runs
in a separate worker process started with the isolated interpreter
(``.venv-indic-test`` by default, or ``AGRIGUIDE_TRANSLATOR_PYTHON``). The
worker is started lazily on the first non-English request, kept alive so the
models load once, and restarted after a crash or timeout. Messages are
ASCII-escaped JSON lines, so non-Latin text cannot be corrupted by a console
code page.
"""

from __future__ import annotations

import atexit
import json
import logging
import os
import queue
import subprocess
import threading
import time
from collections import OrderedDict, deque
from pathlib import Path
from typing import Deque, List, Optional, Sequence

LOGGER = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON_ENV_VAR = "AGRIGUIDE_TRANSLATOR_PYTHON"
SUPPORTED_LANGUAGES = ("en", "hi", "kn")
_SECRET_MARKERS = ("TOKEN", "SECRET", "PASSWORD", "API_KEY")


class TranslationError(RuntimeError):
    """Translation could not be completed; the message is safe to show to a user."""


def default_worker_python() -> Path:
    override = os.environ.get(PYTHON_ENV_VAR)
    if override:
        return Path(override)
    scripts = "Scripts" if os.name == "nt" else "bin"
    executable = "python.exe" if os.name == "nt" else "python"
    return PROJECT_ROOT / ".venv-indic-test" / scripts / executable


def _worker_environment() -> dict:
    """A minimal environment: UTF-8, offline, and no credentials."""
    env = {
        key: value
        for key, value in os.environ.items()
        if not any(marker in key.upper() for marker in _SECRET_MARKERS)
    }
    cache = PROJECT_ROOT / ".cache" / "huggingface"
    env.update(
        {
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
        }
    )
    env.setdefault("HF_HOME", str(cache))
    env.setdefault("HF_HUB_CACHE", str(cache / "hub"))
    return env


class SubprocessTranslator:
    """Translate en/hi/kn text through a long-lived worker subprocess."""

    def __init__(
        self,
        python_executable: Optional[Path] = None,
        command: Optional[Sequence[str]] = None,
        startup_timeout: float = 180.0,
        request_timeout: float = 300.0,
        cache_size: int = 128,
    ) -> None:
        self._python = Path(python_executable) if python_executable else None
        self._command = list(command) if command else None
        self._startup_timeout = startup_timeout
        self._request_timeout = request_timeout
        self._cache_size = cache_size
        self._cache: "OrderedDict[tuple, List[str]]" = OrderedDict()
        self._lock = threading.RLock()
        self._process: Optional[subprocess.Popen] = None
        self._lines: "queue.Queue[Optional[bytes]]" = queue.Queue()
        self._stderr_tail: Deque[str] = deque(maxlen=20)
        self._next_id = 0
        atexit.register(self.close)

    # -- public API ---------------------------------------------------------

    def translate(self, text: str, source: str, target: str) -> str:
        return self.translate_batch([text], source, target)[0]

    def translate_batch(self, texts: Sequence[str], source: str, target: str) -> List[str]:
        """Translate ``texts`` and validate the worker's output.

        Raises ``TranslationError`` for unsupported languages, a missing or
        crashed worker, a timeout, a worker-reported error, or malformed or
        empty output. Text is never returned untranslated.
        """
        for language in (source, target):
            if language not in SUPPORTED_LANGUAGES:
                raise TranslationError("Unsupported language {!r}; use en, hi or kn.".format(language))
        texts = list(texts)
        if not texts:
            return []
        if not all(isinstance(text, str) for text in texts):
            raise TranslationError("Only text can be translated.")
        if source == target:
            return texts

        key = (source, target, tuple(texts))
        with self._lock:
            cached = self._cache.get(key)
            if cached is not None:
                self._cache.move_to_end(key)
                return list(cached)
            response = self._request(
                {"op": "translate", "texts": texts, "source": source, "target": target}
            )
            translations = self._validated(texts, response)
            self._cache[key] = translations
            while len(self._cache) > self._cache_size:
                self._cache.popitem(last=False)
            return list(translations)

    def close(self) -> None:
        with self._lock:
            self._kill()

    # -- worker lifecycle ---------------------------------------------------

    def _worker_command(self) -> List[str]:
        if self._command:
            return self._command
        python = self._python or default_worker_python()
        if not Path(python).exists():
            raise TranslationError(
                "The translation environment was not found at {}. Set {} to the "
                "interpreter that has the IndicTrans2 dependencies.".format(python, PYTHON_ENV_VAR)
            )
        return [str(python), "-X", "utf8", "-m", "src.translation_worker"]

    def _ensure_started(self) -> None:
        if self._process is not None and self._process.poll() is None:
            return
        self._kill()
        command = self._worker_command()
        LOGGER.info("Starting translation worker")
        try:
            self._process = subprocess.Popen(
                command,
                cwd=str(PROJECT_ROOT),
                env=_worker_environment(),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError as exc:
            self._process = None
            raise TranslationError("The translation worker could not be started ({}).".format(type(exc).__name__)) from exc
        self._lines = queue.Queue()
        self._stderr_tail.clear()
        threading.Thread(target=self._pump_stdout, args=(self._process, self._lines), daemon=True).start()
        threading.Thread(target=self._pump_stderr, args=(self._process,), daemon=True).start()

        try:
            ready = self._read_message(self._startup_timeout)
        except TranslationError:
            self._kill()
            raise
        if ready.get("event") != "ready":
            detail = ready.get("error", "unexpected start-up message")
            self._kill()
            raise TranslationError("The translation worker failed to start: {}".format(detail))

    @staticmethod
    def _pump_stdout(process: subprocess.Popen, lines: "queue.Queue[Optional[bytes]]") -> None:
        for raw in iter(process.stdout.readline, b""):
            lines.put(raw)
        lines.put(None)

    def _pump_stderr(self, process: subprocess.Popen) -> None:
        for raw in iter(process.stderr.readline, b""):
            self._stderr_tail.append(raw.decode("utf-8", errors="replace").rstrip())

    def _kill(self) -> None:
        process, self._process = self._process, None
        if process is None:
            return
        try:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=10)
        except Exception:  # best effort during shutdown
            pass
        for stream in (process.stdin, process.stdout, process.stderr):
            try:
                if stream is not None:
                    stream.close()
            except Exception:
                pass

    # -- messaging ----------------------------------------------------------

    def _read_message(self, timeout: float) -> dict:
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TranslationError("The translation worker did not respond in time.")
            try:
                raw = self._lines.get(timeout=remaining)
            except queue.Empty:
                raise TranslationError("The translation worker did not respond in time.") from None
            if raw is None:
                raise TranslationError("The translation worker stopped unexpectedly.")
            try:
                message = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                LOGGER.warning("Ignoring a non-protocol line from the translation worker")
                continue
            if isinstance(message, dict):
                return message

    def _request(self, payload: dict) -> dict:
        self._ensure_started()
        self._next_id += 1
        payload = dict(payload, id=self._next_id)
        try:
            self._process.stdin.write((json.dumps(payload, ensure_ascii=True) + "\n").encode("utf-8"))
            self._process.stdin.flush()
        except (OSError, ValueError) as exc:
            self._kill()
            raise TranslationError("The translation worker is not accepting requests.") from exc
        try:
            while True:
                message = self._read_message(self._request_timeout)
                if message.get("id") == payload["id"]:
                    return message
        except TranslationError:
            # A timed-out or dead worker is replaced on the next request.
            self._kill()
            raise

    def _validated(self, texts: Sequence[str], response: dict) -> List[str]:
        if not response.get("ok"):
            LOGGER.warning("Translation worker reported an error: %s", str(response.get("error"))[:200])
            raise TranslationError("The translation model could not translate this text.")
        translations = response.get("translations")
        if (
            not isinstance(translations, list)
            or len(translations) != len(texts)
            or not all(isinstance(item, str) for item in translations)
        ):
            raise TranslationError("The translation worker returned malformed output.")
        for original, translated in zip(texts, translations):
            if original.strip() and not translated.strip():
                raise TranslationError("The translation worker returned an empty translation.")
        return translations
