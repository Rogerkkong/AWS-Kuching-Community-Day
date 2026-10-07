"""LLM providers behind one tiny interface (LLM_PROVIDER, default "offline").

    llm.provider  -> "offline" | "ollama" | "bedrock"
    llm.label     -> sidebar text, e.g. "Ollama qwen3:8b"
    llm.online    -> False for offline
    llm.json(system, prompt, schema) -> dict     (structured output)
    llm.text(system, prompt) -> str

Any problem (offline mode, model not running, timeout, refusal, bad JSON)
raises LLMError with a friendly message. Callers catch it and use their
deterministic offline logic, adding the message as a warning:

    data, warning = call_json(store.llm, system, prompt, schema)
    if data is None: ...offline path...

Optional dependencies (anthropic, boto3) are imported lazily, so the app runs
with only the core requirements.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from .config import VALID_EFFORTS, Settings

REFUSAL_MESSAGE = "Sorry, I can't help with that request. / Maaf, saya tidak dapat membantu dengan permintaan itu."

PROVIDER_LABELS = {"offline": "Offline", "ollama": "Ollama", "bedrock": "Claude on Bedrock"}


class LLMError(Exception):
    """Friendly, user-facing error. kind: offline|auth|access|rate|network|api|refusal|parse|unknown."""

    def __init__(self, message: str, kind: str = "unknown"):
        super().__init__(message)
        self.message = message
        self.kind = kind

    def __str__(self) -> str:
        return self.message


def strict_schema(schema: dict) -> dict:
    """Copy of a JSON schema with additionalProperties false and all properties required."""
    schema = copy.deepcopy(schema)

    def fix(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object" or "properties" in node:
                node["additionalProperties"] = False
                node["required"] = list(node.get("properties", {}).keys())
            for value in node.values():
                fix(value)
        elif isinstance(node, list):
            for item in node:
                fix(item)

    fix(schema)
    return schema


def _parse_json(text: str) -> dict:
    """json.loads that tolerates ```json fences; raises LLMError on failure."""
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[4:] if text.lower().startswith("json") else text
    try:
        data = json.loads(text)
    except (TypeError, ValueError) as exc:
        raise LLMError("The model returned invalid JSON; using the offline result.", "parse") from exc
    if not isinstance(data, dict):
        raise LLMError("The model returned JSON in an unexpected shape; using the offline result.", "parse")
    return data


# ----------------------------------------------------------------------------
# Providers
# ----------------------------------------------------------------------------


class LLM:
    """Base interface."""

    provider = "offline"
    online = False
    label = "Offline"

    def __init__(self) -> None:
        self.last_error: str | None = None

    def text(self, system: str, prompt: str, *, max_tokens: int = 4000) -> str:
        raise NotImplementedError

    def json(self, system: str, prompt: str, schema: dict, *, max_tokens: int = 4000) -> dict:
        raise NotImplementedError


class OfflineLLM(LLM):
    """No model. Every call raises LLMError(kind='offline'); features use deterministic logic."""

    provider = "offline"
    online = False

    def __init__(self, reason: str = "Offline mode: deterministic answers, no model."):
        super().__init__()
        self.reason = reason
        self.label = "Offline"

    def text(self, system: str, prompt: str, *, max_tokens: int = 4000) -> str:
        raise LLMError(self.reason, "offline")

    def json(self, system: str, prompt: str, schema: dict, *, max_tokens: int = 4000) -> dict:
        raise LLMError(self.reason, "offline")


class OllamaLLM(LLM):
    """Local open-weight model via Ollama's /api/chat (sovereign option from the guide)."""

    provider = "ollama"
    online = True

    def __init__(self, settings: Settings, session: Any = None):
        super().__init__()
        self.settings = settings
        self.url = settings.ollama_base_url.rstrip("/") + "/api/chat"
        self.model = settings.llm_model
        self.label = f"Ollama {self.model}"
        self._session = session  # tests inject a fake with .post()

    def _post(self, payload: dict) -> dict:
        try:
            import requests

            poster = self._session or requests
            resp = poster.post(self.url, json=payload, timeout=self.settings.llm_timeout_s)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            name = type(exc).__name__
            if "Timeout" in name:
                err = LLMError(f"Ollama took longer than {self.settings.llm_timeout_s:.0f}s; using the offline result.", "network")
            elif "Connection" in name:
                err = LLMError(f"Cannot reach Ollama at {self.settings.ollama_base_url}; using the offline result.", "network")
            else:
                err = LLMError(f"Ollama error ({name}); using the offline result.", "api")
            self.last_error = err.message
            raise err from exc

    def _chat(self, system: str, prompt: str, schema: dict | None) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.1},
            "think": False,
        }
        if schema is not None:
            payload["format"] = schema
        data = self._post(payload)
        content = ((data or {}).get("message") or {}).get("content", "")
        if not content:
            raise LLMError("Ollama returned an empty answer; using the offline result.", "api")
        self.last_error = None
        return content

    def text(self, system: str, prompt: str, *, max_tokens: int = 4000) -> str:
        return self._chat(system, prompt, None)

    def json(self, system: str, prompt: str, schema: dict, *, max_tokens: int = 4000) -> dict:
        return _parse_json(self._chat(system, prompt, strict_schema(schema)))


def _friendly_bedrock_error(exc: BaseException, settings: Settings) -> LLMError:
    """Convert SDK / AWS exceptions into an LLMError with a clear hint."""
    if isinstance(exc, LLMError):
        return exc
    try:
        import anthropic
    except ImportError:
        return LLMError(f"Claude on Bedrock unavailable ({type(exc).__name__}).", "unknown")
    region, model = settings.aws_region, settings.bedrock_model
    if isinstance(exc, anthropic.AuthenticationError):
        return LLMError("AWS credentials were rejected. Run `aws sso login` or check AWS_BEARER_TOKEN_BEDROCK.", "auth")
    if isinstance(exc, (anthropic.PermissionDeniedError, anthropic.NotFoundError)):
        return LLMError(f"Model access not enabled in {region} for {model}.", "access")
    if isinstance(exc, anthropic.RateLimitError):
        return LLMError("Amazon Bedrock is rate limiting requests; using the offline result.", "rate")
    if isinstance(exc, (anthropic.APITimeoutError, anthropic.APIConnectionError)):
        return LLMError("Cannot reach Amazon Bedrock; using the offline result.", "network")
    if isinstance(exc, anthropic.APIStatusError):
        return LLMError(f"Amazon Bedrock returned HTTP {exc.status_code}; using the offline result.", "api")
    return LLMError(f"Claude on Bedrock unavailable ({type(exc).__name__}); using the offline result.", "unknown")


class BedrockLLM(LLM):
    """Claude on Amazon Bedrock via anthropic.AnthropicBedrockMantle (optional).

    Never sends thinking / temperature / prefill; effort lives in output_config.
    `client` can be injected (tests use a fake with .beta.messages.create).
    """

    provider = "bedrock"
    online = True

    def __init__(self, settings: Settings, client: Any = None):
        super().__init__()
        self.settings = settings
        self.label = f"Claude on Bedrock ({settings.bedrock_model})"
        self._client = client if client is not None else self._make_client(settings)

    @staticmethod
    def _make_client(settings: Settings) -> Any:
        from anthropic import AnthropicBedrockMantle, BetaRefusalFallbackMiddleware

        kwargs: dict[str, Any] = {
            "aws_region": settings.aws_region,
            "timeout": settings.llm_timeout_s,
            "max_retries": 1,
            "middleware": [BetaRefusalFallbackMiddleware([{"model": settings.bedrock_fallback_model}])],
        }
        if settings.bedrock_api_key:
            kwargs["api_key"] = settings.bedrock_api_key
        elif settings.aws_profile:
            kwargs["aws_profile"] = settings.aws_profile
        return AnthropicBedrockMantle(**kwargs)

    def build_request(self, system: str, prompt: str, *, max_tokens: int = 16000, schema: dict | None = None) -> dict:
        """kwargs for client.beta.messages.create (pure; unit-testable)."""
        effort = self.settings.effort if self.settings.effort in VALID_EFFORTS else "low"
        output_config: dict[str, Any] = {"effort": effort}
        if schema is not None:
            output_config["format"] = {"type": "json_schema", "schema": strict_schema(schema)}
        return {
            "model": self.settings.bedrock_model,
            "max_tokens": int(max(max_tokens, 16000)),
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
            "output_config": output_config,
        }

    # Tiny disk cache: identical request -> identical answer (repeatable demo).
    def _cache_path(self, kwargs: dict) -> Path:
        key = hashlib.sha256(json.dumps(kwargs, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        return Path(self.settings.runtime_dir) / "llm_cache" / f"{key[:40]}.json"

    def _run(self, kwargs: dict) -> str:
        path = self._cache_path(kwargs)
        if self.settings.llm_cache:
            try:
                return json.loads(path.read_text(encoding="utf-8"))["text"]
            except (OSError, ValueError, KeyError):
                pass
        from anthropic import BetaFallbackState

        try:
            with BetaFallbackState():
                response = self._client.beta.messages.create(**kwargs)
        except Exception as exc:
            err = _friendly_bedrock_error(exc, self.settings)
            self.last_error = err.message
            raise err from exc
        if getattr(response, "stop_reason", None) == "refusal":
            raise LLMError(REFUSAL_MESSAGE, "refusal")
        text = next((b.text for b in (response.content or []) if getattr(b, "type", None) == "text"), "").strip()
        if not text:
            raise LLMError("Claude returned an empty answer; using the offline result.", "api")
        self.last_error = None
        if self.settings.llm_cache and getattr(response, "stop_reason", None) != "max_tokens":
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps({"text": text}, ensure_ascii=False), encoding="utf-8")
            except OSError:
                pass
        return text

    def text(self, system: str, prompt: str, *, max_tokens: int = 16000) -> str:
        return self._run(self.build_request(system, prompt, max_tokens=max_tokens))

    def json(self, system: str, prompt: str, schema: dict, *, max_tokens: int = 16000) -> dict:
        return _parse_json(self._run(self.build_request(system, prompt, max_tokens=max_tokens, schema=schema)))


# ----------------------------------------------------------------------------
# Factory and helpers
# ----------------------------------------------------------------------------


def make_llm(settings: Settings, provider: str | None = None) -> LLM:
    """Build the provider named in settings (or `provider`); fall back to offline with a reason."""
    provider = (provider or settings.llm_provider or "offline").lower()
    if provider == "ollama":
        return OllamaLLM(settings)
    if provider == "bedrock":
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return OfflineLLM("Claude on Bedrock needs `pip install anthropic[bedrock] boto3`; running offline.")
        if not settings.bedrock_api_key:
            try:
                import boto3

                session = boto3.Session(profile_name=settings.aws_profile) if settings.aws_profile else boto3.Session()
                if session.get_credentials() is None:
                    return OfflineLLM("No AWS credentials found for Bedrock; running offline.")
            except Exception as exc:
                return OfflineLLM(f"AWS credentials problem ({type(exc).__name__}); running offline.")
        try:
            return BedrockLLM(settings)
        except Exception as exc:
            return OfflineLLM(_friendly_bedrock_error(exc, settings).message)
    return OfflineLLM()


def call_json(llm: LLM | None, system: str, prompt: str, schema: dict) -> tuple[dict | None, str | None]:
    """(data, warning). data is None in offline mode or on any error (warning says why;
    warning is None for plain offline mode, which is not a problem)."""
    if llm is None or llm.provider == "offline":
        return None, None
    try:
        return llm.json(system, prompt, schema), None
    except LLMError as err:
        return None, err.message
    except Exception as exc:  # never let the model crash the demo
        return None, f"Model error ({type(exc).__name__}); using the offline result."


def mode_label(llm: LLM | None) -> str:
    """'Offline' / 'Ollama' / 'Claude on Bedrock'."""
    return PROVIDER_LABELS.get(getattr(llm, "provider", "offline"), "Offline")
