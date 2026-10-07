"""Single entry point for chat, embeddings and reranking.

Backends (INFERENCE_BACKEND):
* ollama   - development default: chat via /api/chat, embeddings via /api/embed (bge-m3).
* llamacpp - packaged builds: bundled llama-server processes (OpenAI-compatible + /v1/rerank).
* fake     - deterministic offline stand-in used by tests and when no model is installed.
"""
from __future__ import annotations

import math
import threading
from typing import Iterator, Protocol

from app.config import Settings, get_settings


class InferenceError(RuntimeError):
    pass


class Backend(Protocol):
    name: str

    def health(self) -> dict: ...
    def embed(self, texts: list[str]) -> list[list[float]]: ...
    def chat(self, messages: list[dict], *, json_mode: bool = False, max_tokens: int | None = None,
             timeout: float | None = None) -> str: ...
    def chat_stream(self, messages: list[dict], *, max_tokens: int | None = None) -> Iterator[str]: ...
    def rerank(self, query: str, documents: list[str]) -> list[float] | None: ...
    def warm_up(self) -> None: ...


def parse_json_loose(text: str):
    """Parse the first JSON object/array in a model reply (tolerates code fences and chatter)."""
    import json
    import re

    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    try:
        return json.loads(text)
    except ValueError:
        pass
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start, end = text.find(open_ch), text.rfind(close_ch)
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except ValueError:
                continue
    raise InferenceError("Model did not return valid JSON")


def normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


_client: Backend | None = None
_lock = threading.Lock()
_warm = {"state": "idle", "error": None}  # idle | loading | ready | error


def make_backend(settings: Settings | None = None) -> Backend:
    settings = settings or get_settings()
    kind = settings.inference_backend
    if kind == "fake":
        from app.services.inference.fake_backend import FakeBackend
        return FakeBackend(settings)
    if kind == "llamacpp":
        from app.services.inference.llamacpp_backend import LlamaCppBackend
        return LlamaCppBackend(settings)
    if kind == "ollama":
        from app.services.inference.ollama_backend import OllamaBackend
        return OllamaBackend(settings)
    raise InferenceError(f"Unknown INFERENCE_BACKEND {kind!r}")


def get_client() -> Backend:
    global _client
    with _lock:
        if _client is None:
            _client = make_backend()
        return _client


def set_client(backend: Backend | None) -> None:
    """Replace the process-wide client (tests, settings changes)."""
    global _client
    with _lock:
        _client = backend
        _warm.update(state="idle", error=None)


def warm_up_async() -> None:
    """Load the chat model in the background so the first question is fast."""
    if _warm["state"] in ("loading", "ready"):
        return
    _warm.update(state="loading", error=None)

    def run() -> None:
        try:
            get_client().warm_up()
            _warm.update(state="ready", error=None)
        except Exception as exc:  # noqa: BLE001 - reported through /health
            _warm.update(state="error", error=str(exc))

    threading.Thread(target=run, name="model-warm-up", daemon=True).start()


def warm_state() -> dict:
    return dict(_warm)
