"""Settings for MixUp, read from environment variables (and an optional .env file).

Three ways to run (pick one, see .env.example):
  1. `aws configure` (or AWS SSO) and optionally AWS_PROFILE
  2. A Bedrock API key in AWS_BEARER_TOKEN_BEDROCK
  3. MIXUP_OFFLINE=1 (no AWS at all; keyword search fallback)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Mapping

# Folder that holds app.py, mixup/, data/ ...
PROTOTYPE_DIR = Path(__file__).resolve().parent.parent

DEFAULT_MODEL = "anthropic.claude-opus-5-5"
DEFAULT_FALLBACK_MODEL = "anthropic.claude-opus-4-8"
DEFAULT_EMBED_MODEL = "amazon.titan-embed-text-v2:0"
VALID_EFFORTS = ("low", "medium", "high", "xhigh", "max")

_TRUE = {"1", "true", "yes", "on", "y"}
_FALSE = {"0", "false", "no", "off", "n", ""}


def _flag(value: str | None, default: bool) -> bool:
    """Turn '1'/'on'/'true' into True and '0'/'off'/'false' into False."""
    if value is None:
        return default
    value = value.strip().lower()
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    return default


def bedrock_model_id(model: str) -> str:
    """Bedrock model IDs need the 'anthropic.' prefix. Add it if someone forgot."""
    model = (model or "").strip() or DEFAULT_MODEL
    if model.startswith("claude-"):
        return "anthropic." + model
    return model


@dataclass(frozen=True)
class Settings:
    """All runtime settings. Frozen so Streamlit can use it as a cache key."""

    aws_region: str = "us-east-1"
    aws_profile: str | None = None
    bedrock_api_key: str | None = None  # from AWS_BEARER_TOKEN_BEDROCK
    model: str = DEFAULT_MODEL
    fallback_model: str = DEFAULT_FALLBACK_MODEL
    effort: str = "low"  # Q&A speed; features may pass "medium"
    embeddings: bool = False  # Titan embeddings for hybrid search (off by default)
    embed_model: str = DEFAULT_EMBED_MODEL
    offline: bool = False  # force offline mode (no AWS calls at all)
    cache: bool = True  # reuse identical AI responses from .mixup_cache/
    timeout_s: float = 90.0  # per AI request; keep the demo snappy
    data_dir: Path = PROTOTYPE_DIR / "data"
    cache_dir: Path = PROTOTYPE_DIR / ".mixup_cache"

    def with_changes(self, **changes) -> "Settings":
        """Return a copy with some fields changed (Settings is immutable)."""
        return replace(self, **changes)


def load_settings(env: Mapping[str, str] | None = None, use_dotenv: bool = True) -> Settings:
    """Build Settings from environment variables.

    env: a dict to read instead of os.environ (handy in tests).
    use_dotenv: also read a .env file next to app.py (never overrides real env vars).
    """
    if env is None:
        if use_dotenv:
            try:
                from dotenv import load_dotenv

                load_dotenv(PROTOTYPE_DIR / ".env", override=False)
            except ImportError:  # python-dotenv missing is not fatal
                pass
        env = os.environ

    def get(name: str) -> str | None:
        value = env.get(name)
        if value is None or value.strip() == "":
            return None
        return value.strip()

    effort = (get("MIXUP_EFFORT") or "low").lower()
    if effort not in VALID_EFFORTS:
        effort = "low"

    data_dir = Path(get("DATA_DIR") or (PROTOTYPE_DIR / "data"))
    if not data_dir.is_absolute():
        data_dir = PROTOTYPE_DIR / data_dir

    try:
        timeout_s = float(get("MIXUP_TIMEOUT") or 90)
    except ValueError:
        timeout_s = 90.0

    return Settings(
        aws_region=get("AWS_REGION") or get("AWS_DEFAULT_REGION") or "us-east-1",
        aws_profile=get("AWS_PROFILE"),
        bedrock_api_key=get("AWS_BEARER_TOKEN_BEDROCK"),
        model=bedrock_model_id(get("MIXUP_MODEL") or DEFAULT_MODEL),
        fallback_model=bedrock_model_id(get("MIXUP_FALLBACK_MODEL") or DEFAULT_FALLBACK_MODEL),
        effort=effort,
        embeddings=_flag(get("MIXUP_EMBEDDINGS"), False),
        offline=_flag(get("MIXUP_OFFLINE"), False),
        cache=_flag(get("MIXUP_CACHE"), True),
        timeout_s=timeout_s,
        data_dir=data_dir,
        cache_dir=PROTOTYPE_DIR / ".mixup_cache",
    )
