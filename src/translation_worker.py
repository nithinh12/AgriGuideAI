"""Persistent IndicTrans2 worker process.

Run with the isolated translation interpreter (``.venv-indic-test``), never the
production interpreter::

    .venv-indic-test\\Scripts\\python.exe -m src.translation_worker

Protocol: one JSON object per line on stdin/stdout, UTF-8, ASCII-escaped
(``ensure_ascii=True``) so the pipe never depends on a console code page. The
worker announces ``{"event": "ready"}`` once the translation libraries have
imported; the (large) checkpoints load lazily on the first request and then
stay resident, so each model loads once per worker process.

Request:  ``{"id": 1, "op": "translate", "texts": ["..."], "source": "hi", "target": "en"}``
Response: ``{"id": 1, "ok": true, "translations": ["..."]}`` or
          ``{"id": 1, "ok": false, "error": "..."}``

Only protocol lines are written to stdout; anything the libraries print goes to
stderr. The translator uses cached checkpoints only (no downloads).
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, IO, Iterable


def handle_request(translator: Any, request: Any) -> Dict[str, Any]:
    """Run one decoded request and return a JSON-serialisable response."""
    request_id = request.get("id") if isinstance(request, dict) else None
    try:
        if not isinstance(request, dict):
            raise ValueError("request must be a JSON object")
        operation = request.get("op")
        if operation == "ping":
            return {"id": request_id, "ok": True}
        if operation != "translate":
            raise ValueError("unknown op {!r}".format(operation))
        texts = request.get("texts")
        if not isinstance(texts, list) or not all(isinstance(item, str) for item in texts):
            raise ValueError("'texts' must be a list of strings")
        translations = translator.translate_batch(texts, request.get("source"), request.get("target"))
        return {"id": request_id, "ok": True, "translations": list(translations)}
    except Exception as exc:  # the worker must survive any single bad request
        return {"id": request_id, "ok": False, "error": "{}: {}".format(type(exc).__name__, exc)}


def serve(translator: Any, lines: Iterable[str], out: IO[str]) -> None:
    """Answer each request line until the input stream closes."""
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError as exc:
            response: Dict[str, Any] = {"id": None, "ok": False, "error": "invalid JSON: {}".format(exc)}
        else:
            response = handle_request(translator, request)
        out.write(json.dumps(response, ensure_ascii=True) + "\n")
        out.flush()


def main() -> int:
    # Cached checkpoints only: never reach for the network from this process.
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    protocol_out = sys.stdout
    protocol_in = sys.stdin
    for stream in (protocol_in, protocol_out):
        stream.reconfigure(encoding="utf-8")
    # Keep stdout reserved for protocol lines; library chatter goes to stderr.
    sys.stdout = sys.stderr

    try:
        from src.translator import IndicTrans2Translator

        # use_cache=False: the checkpoints' remote modeling code is not
        # compatible with the key/value cache objects of transformers 4.57.
        translator = IndicTrans2Translator(use_cache=False, local_files_only=True)
    except Exception as exc:
        protocol_out.write(
            json.dumps({"event": "error", "error": "{}: {}".format(type(exc).__name__, exc)}) + "\n"
        )
        protocol_out.flush()
        return 1

    protocol_out.write(json.dumps({"event": "ready", "pid": os.getpid()}) + "\n")
    protocol_out.flush()
    serve(translator, protocol_in, protocol_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
