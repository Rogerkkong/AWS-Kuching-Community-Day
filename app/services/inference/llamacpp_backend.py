"""llama.cpp backend for packaged builds (stretch goal).

Starts three bundled llama-server processes on free 127.0.0.1 ports: the chat model, bge-m3 with
--embedding and bge-reranker-v2-m3 with --reranking, then uses the OpenAI-compatible endpoints and
/v1/rerank. Processes are started lazily and stopped at exit.
"""
from __future__ import annotations

import atexit
import json
import subprocess
import time
from pathlib import Path
from typing import Iterator

import httpx

from app.config import Settings
from app.security import free_port
from app.services.inference.client import InferenceError, normalize


class _Server:
    def __init__(self, binary: Path, gguf: Path, extra: list[str]):
        self.binary, self.gguf, self.extra = binary, gguf, extra
        self.port: int | None = None
        self.proc: subprocess.Popen | None = None

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def ensure(self) -> str:
        if self.proc and self.proc.poll() is None:
            return self.url
        if not self.binary.exists() or not self.gguf.exists():
            raise InferenceError(f"Missing {self.binary.name} or {self.gguf.name} in models/")
        self.port = free_port()
        cmd = [str(self.binary), "-m", str(self.gguf), "--host", "127.0.0.1", "--port", str(self.port),
               "--log-disable", *self.extra]
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self.proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)
        atexit.register(self.stop)
        deadline = time.time() + 120
        while time.time() < deadline:
            try:
                if httpx.get(f"{self.url}/health", timeout=1).status_code == 200:
                    return self.url
            except Exception:  # noqa: BLE001
                pass
            time.sleep(0.5)
        raise InferenceError(f"llama-server for {self.gguf.name} did not start")

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()


class LlamaCppBackend:
    name = "llamacpp"

    def __init__(self, settings: Settings):
        self.s = settings
        root = settings.repo_root
        binary = root / settings.llamacpp_server
        self.chat_srv = _Server(binary, root / settings.llamacpp_chat_gguf, ["-c", str(settings.num_ctx)])
        self.embed_srv = _Server(binary, root / settings.llamacpp_embed_gguf, ["--embedding", "--pooling", "cls"])
        self.rerank_srv = _Server(binary, root / settings.llamacpp_rerank_gguf, ["--reranking"])

    def health(self) -> dict:
        files = {p.name: p.exists() for p in (self.chat_srv.gguf, self.embed_srv.gguf, self.rerank_srv.gguf)}
        ok = self.chat_srv.binary.exists() and all(files.values())
        return {"backend": self.name, "reachable": ok, "chat_model": self.chat_srv.gguf.name,
                "embed_model": self.s.embed_model, "chat_model_present": files.get(self.chat_srv.gguf.name, False),
                "embed_model_present": files.get(self.embed_srv.gguf.name, False),
                "detail": None if ok else f"Missing files in models/: {[k for k, v in files.items() if not v]}"}

    def embed(self, texts: list[str]) -> list[list[float]]:
        url = self.embed_srv.ensure()
        r = httpx.post(f"{url}/v1/embeddings", json={"input": texts, "model": "bge-m3"}, timeout=120)
        r.raise_for_status()
        return [normalize(d["embedding"]) for d in r.json()["data"]]

    def _body(self, messages: list[dict], stream: bool, json_mode: bool, max_tokens: int | None) -> dict:
        body = {"messages": messages, "stream": stream, "temperature": self.s.temperature, "seed": 7,
                "max_tokens": max_tokens or self.s.answer_max_tokens,
                "chat_template_kwargs": {"enable_thinking": False}}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        return body

    def chat(self, messages: list[dict], *, json_mode: bool = False, max_tokens: int | None = None,
             timeout: float | None = None) -> str:
        url = self.chat_srv.ensure()
        r = httpx.post(f"{url}/v1/chat/completions", json=self._body(messages, False, json_mode, max_tokens),
                       timeout=timeout or 300)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    def chat_stream(self, messages: list[dict], *, max_tokens: int | None = None) -> Iterator[str]:
        url = self.chat_srv.ensure()
        with httpx.stream("POST", f"{url}/v1/chat/completions",
                          json=self._body(messages, True, False, max_tokens), timeout=300) as r:
            for line in r.iter_lines():
                if not line.startswith("data: ") or line.endswith("[DONE]"):
                    continue
                delta = json.loads(line[6:])["choices"][0].get("delta", {}).get("content")
                if delta:
                    yield delta

    def rerank(self, query: str, documents: list[str]) -> list[float] | None:
        url = self.rerank_srv.ensure()
        r = httpx.post(f"{url}/v1/rerank", json={"query": query, "documents": documents}, timeout=120)
        r.raise_for_status()
        scores = [0.0] * len(documents)
        for item in r.json()["results"]:
            scores[item["index"]] = float(item["relevance_score"])
        return scores

    def warm_up(self) -> None:
        self.chat([{"role": "user", "content": "OK"}], max_tokens=2, timeout=600)
        self.embed(["cuti rehat"])
