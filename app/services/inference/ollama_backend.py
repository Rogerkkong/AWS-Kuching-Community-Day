"""Ollama backend (development default). Talks only to the local Ollama server on 127.0.0.1."""
from __future__ import annotations

import json
import re
from typing import Iterator

import httpx

from app.config import Settings
from app.services.inference.client import InferenceError, normalize

THINK_RE = re.compile(r"<think>.*?</think>\s*", re.S)


class OllamaBackend:
    name = "ollama"

    def __init__(self, settings: Settings):
        self.s = settings
        self.base = settings.ollama_url.rstrip("/")

    # ------------------------------------------------------------------ health
    def health(self) -> dict:
        try:
            r = httpx.get(f"{self.base}/api/tags", timeout=2.0)
            r.raise_for_status()
            names = {m.get("name", "") for m in r.json().get("models", [])}
        except Exception as exc:  # noqa: BLE001
            return {"backend": self.name, "reachable": False, "chat_model": self.s.llm_model,
                    "embed_model": self.s.embed_model, "chat_model_present": False,
                    "embed_model_present": False, "detail": f"Ollama not reachable at {self.base}: {exc}"}

        def present(model: str) -> bool:
            return model in names or f"{model}:latest" in names or any(n.split(":")[0] == model for n in names)

        return {"backend": self.name, "reachable": True, "chat_model": self.s.llm_model,
                "embed_model": self.s.embed_model, "chat_model_present": present(self.s.llm_model),
                "embed_model_present": present(self.s.embed_model), "detail": None}

    # ------------------------------------------------------------- embeddings
    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), 16):
            batch = texts[i:i + 16]
            try:
                r = httpx.post(f"{self.base}/api/embed",
                               json={"model": self.s.embed_model, "input": batch,
                                     "keep_alive": self.s.ollama_keep_alive},
                               timeout=120.0)
                r.raise_for_status()
            except Exception as exc:  # noqa: BLE001
                raise InferenceError(f"Embedding failed: {exc}") from exc
            out.extend(normalize(v) for v in r.json()["embeddings"])
        return out

    # ------------------------------------------------------------------- chat
    def _payload(self, messages: list[dict], stream: bool, json_mode: bool, max_tokens: int | None) -> dict:
        payload = {
            "model": self.s.llm_model,
            "messages": messages,
            "stream": stream,
            "think": False,  # qwen3 thinking mode off for speed
            "keep_alive": self.s.ollama_keep_alive,
            "options": {"temperature": self.s.temperature, "num_ctx": self.s.num_ctx,
                        "num_predict": max_tokens or self.s.answer_max_tokens, "seed": 7},
        }
        if json_mode:
            payload["format"] = "json"
        return payload

    def chat(self, messages: list[dict], *, json_mode: bool = False, max_tokens: int | None = None,
             timeout: float | None = None) -> str:
        try:
            r = httpx.post(f"{self.base}/api/chat", json=self._payload(messages, False, json_mode, max_tokens),
                           timeout=timeout or 300.0)
            r.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            raise InferenceError(f"Chat failed: {exc}") from exc
        return THINK_RE.sub("", r.json()["message"]["content"])

    def chat_stream(self, messages: list[dict], *, max_tokens: int | None = None) -> Iterator[str]:
        payload = self._payload(messages, True, False, max_tokens)
        try:
            with httpx.stream("POST", f"{self.base}/api/chat", json=payload, timeout=300.0) as r:
                r.raise_for_status()
                in_think = False
                for line in r.iter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    piece = data.get("message", {}).get("content", "")
                    # Defensive: strip a <think> block if the model still emits one.
                    if "<think>" in piece:
                        in_think = True
                        piece = piece.split("<think>", 1)[0]
                    if in_think:
                        if "</think>" in piece:
                            in_think = False
                            piece = piece.split("</think>", 1)[1]
                        else:
                            continue
                    if piece:
                        yield piece
                    if data.get("done"):
                        break
        except InferenceError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise InferenceError(f"Streaming chat failed: {exc}") from exc

    def rerank(self, query: str, documents: list[str]) -> list[float] | None:
        return None  # Ollama has no rerank endpoint; rerank.py uses the CrossEncoder or a fallback.

    def warm_up(self) -> None:
        self.chat([{"role": "user", "content": "Jawab 'OK'."}], max_tokens=2, timeout=600)
        self.embed(["cuti rehat"])
