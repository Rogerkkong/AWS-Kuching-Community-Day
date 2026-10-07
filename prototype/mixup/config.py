"""Settings for MixUp Navigator, read from environment variables (and .env).

LLM_PROVIDER picks the model behind the answers:
  offline  (default) no model at all; deterministic extractive answers
  ollama   a local open-weight model (sovereign, as in the build guide)
  bedrock  Claude on Amazon Bedrock (optional, public documents only)

MIXUP_TODAY=YYYY-MM-DD freezes "today" (tests and rehearsals).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from typing import Mapping

# Folder that holds app.py, mixup/, data/ ...
PROTOTYPE_DIR = Path(__file__).resolve().parent.parent

PROVIDERS = ("offline", "ollama", "bedrock")
DEFAULT_OLLAMA_MODEL = "qwen3:8b"
DEFAULT_BEDROCK_MODEL = "anthropic.claude-opus-5-5"
DEFAULT_BEDROCK_FALLBACK = "anthropic.claude-opus-4-8"
VALID_EFFORTS = ("low", "medium", "high", "xhigh", "max")

_TRUE = {"1", "true", "yes", "on", "y"}
_FALSE = {"0", "false", "no", "off", "n"}


def _flag(value: str | None, default: bool) -> bool:
    """'1'/'on'/'true' -> True, '0'/'off'/'false' -> False, anything else -> default."""
    if value is None:
        return default
    value = value.strip().lower()
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    return default


def parse_date(value) -> date | None:
    """'2024-03-01' (or a date) -> date; empty/invalid -> None."""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def bedrock_model_id(model: str) -> str:
    """Bedrock model ids need the 'anthropic.' prefix. Add it if someone forgot."""
    model = (model or "").strip() or DEFAULT_BEDROCK_MODEL
    return "anthropic." + model if model.startswith("claude-") else model


@dataclass(frozen=True)
class Settings:
    """All runtime settings. Frozen so it can be used as a cache key."""

    llm_provider: str = "offline"
    llm_model: str = DEFAULT_OLLAMA_MODEL  # Ollama model name
    ollama_base_url: str = "http://localhost:11434"
    llm_timeout_s: float = 60.0
    # Bedrock (optional)
    aws_region: str = "us-east-1"
    aws_profile: str | None = None
    bedrock_api_key: str | None = None  # AWS_BEARER_TOKEN_BEDROCK
    bedrock_model: str = DEFAULT_BEDROCK_MODEL
    bedrock_fallback_model: str = DEFAULT_BEDROCK_FALLBACK
    effort: str = "low"
    llm_cache: bool = True
    # Behaviour
    today: date | None = None  # None = the real date
    top_k: int = 6  # passages given to the answer step
    confidence_high: float = 0.75  # query-term coverage of the best passage
    confidence_medium: float = 0.5
    # Paths
    data_dir: Path = PROTOTYPE_DIR / "data"
    runtime_dir: Path = PROTOTYPE_DIR / "data" / "runtime"

    def with_changes(self, **changes) -> "Settings":
        """Return a copy with some fields changed (Settings is immutable)."""
        return replace(self, **changes)

    def current_date(self) -> date:
        """'Today' for the status engine: MIXUP_TODAY if set, else the real date."""
        return self.today or date.today()


def load_settings(env: Mapping[str, str] | None = None, use_dotenv: bool = True) -> Settings:
    """Build Settings from environment variables (env dict for tests)."""
    if env is None:
        if use_dotenv:
            try:
                from dotenv import load_dotenv

                load_dotenv(PROTOTYPE_DIR / ".env", override=False)
            except ImportError:
                pass
        env = os.environ

    def get(name: str) -> str | None:
        value = env.get(name)
        if value is None or value.strip() == "":
            return None
        return value.strip()

    provider = (get("LLM_PROVIDER") or "offline").lower()
    if provider not in PROVIDERS or _flag(get("MIXUP_OFFLINE"), False):
        provider = "offline"

    effort = (get("MIXUP_EFFORT") or "low").lower()
    if effort not in VALID_EFFORTS:
        effort = "low"

    def path(name: str, default: Path) -> Path:
        value = Path(get(name) or default)
        return value if value.is_absolute() else PROTOTYPE_DIR / value

    data_dir = path("DATA_DIR", PROTOTYPE_DIR / "data")
    runtime_dir = path("MIXUP_RUNTIME_DIR", data_dir / "runtime")

    def number(name: str, default: float) -> float:
        try:
            return float(get(name) or default)
        except ValueError:
            return default

    return Settings(
        llm_provider=provider,
        llm_model=get("LLM_MODEL") or DEFAULT_OLLAMA_MODEL,
        ollama_base_url=(get("OLLAMA_BASE_URL") or "http://localhost:11434").rstrip("/"),
        llm_timeout_s=number("LLM_TIMEOUT", 60.0),
        aws_region=get("AWS_REGION") or get("AWS_DEFAULT_REGION") or "us-east-1",
        aws_profile=get("AWS_PROFILE"),
        bedrock_api_key=get("AWS_BEARER_TOKEN_BEDROCK"),
        bedrock_model=bedrock_model_id(get("BEDROCK_MODEL") or get("MIXUP_MODEL") or DEFAULT_BEDROCK_MODEL),
        bedrock_fallback_model=bedrock_model_id(get("BEDROCK_FALLBACK_MODEL") or DEFAULT_BEDROCK_FALLBACK),
        effort=effort,
        llm_cache=_flag(get("MIXUP_LLM_CACHE"), True),
        today=parse_date(get("MIXUP_TODAY")),
        top_k=int(number("MIXUP_TOP_K", 6)),
        confidence_high=number("MIXUP_CONF_HIGH", 0.75),
        confidence_medium=number("MIXUP_CONF_MEDIUM", 0.5),
        data_dir=data_dir,
        runtime_dir=runtime_dir,
    )
