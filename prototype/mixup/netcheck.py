"""Automatic environment detection: internet, local Ollama, AWS credentials.

The officer should never have to choose a model mode. The app checks what is
reachable and picks the best provider itself (guide NFR-01, NFR-11):

    Ollama reachable on localhost  -> "ollama"  (local sovereign model)
    internet + AWS credentials     -> "bedrock" (Claude on Amazon Bedrock, public docs only)
    otherwise                      -> "offline" (deterministic answers, always works)

Results are cached for a short time so the sidebar stays fast.
"""

from __future__ import annotations

import socket
import time
from dataclasses import dataclass

import requests

CACHE_SECONDS = 20
_cache: dict[str, tuple[float, object]] = {}

# Well-known public resolvers; a TCP connect is enough to tell whether we are online.
PROBE_HOSTS = (("1.1.1.1", 443), ("8.8.8.8", 53))


def _cached(key: str, fn, ttl: float = CACHE_SECONDS):
    now = time.monotonic()
    hit = _cache.get(key)
    if hit and now - hit[0] < ttl:
        return hit[1]
    value = fn()
    _cache[key] = (now, value)
    return value


def clear_cache() -> None:
    _cache.clear()


def network_online(timeout: float = 0.8) -> bool:
    """True if a TCP connection to a public host succeeds (no data is sent)."""
    def probe() -> bool:
        for host, port in PROBE_HOSTS:
            try:
                with socket.create_connection((host, port), timeout=timeout):
                    return True
            except OSError:
                continue
        return False
    return bool(_cached("net", probe))


def ollama_available(base_url: str, timeout: float = 1.0) -> bool:
    """True if a local Ollama server answers /api/tags."""
    def probe() -> bool:
        try:
            r = requests.get(base_url.rstrip("/") + "/api/tags", timeout=timeout)
            return r.ok
        except requests.RequestException:
            return False
    return bool(_cached(f"ollama:{base_url}", probe))


def bedrock_configured(settings) -> bool:
    """AWS credentials look present (a Bedrock API key, a profile, or standard env vars)."""
    import os
    if getattr(settings, "bedrock_api_key", None) or getattr(settings, "aws_profile", None):
        return True
    return bool(os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY"))


@dataclass(frozen=True)
class Detection:
    online: bool
    ollama: bool
    bedrock: bool
    provider: str  # offline | ollama | bedrock

    def label_ms(self) -> str:
        return "Dalam talian" if self.online else "Luar talian"

    def label_en(self) -> str:
        return "Online" if self.online else "Offline"


def detect(settings, forced_offline: bool = False) -> Detection:
    """Check the environment and choose the provider automatically."""
    online = network_online()
    ollama = ollama_available(getattr(settings, "ollama_base_url", "http://localhost:11434"))
    bedrock = bedrock_configured(settings) and online
    if forced_offline:
        provider = "offline"
    elif ollama:
        provider = "ollama"
    elif bedrock:
        provider = "bedrock"
    else:
        provider = "offline"
    return Detection(online=online, ollama=ollama, bedrock=bedrock, provider=provider)
