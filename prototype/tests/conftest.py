"""Shared fixtures: a Store with MIXUP_TODAY fixed and a private runtime dir, and FakeLLM."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mixup.config import load_settings  # noqa: E402
from mixup.llm import LLM  # noqa: E402
from mixup.store import Store  # noqa: E402

TODAY = "2026-10-07"


class FakeLLM(LLM):
    """Returns canned JSON responses in order and records every call."""

    provider = "fake"
    online = True
    label = "Fake"

    def __init__(self, responses=None, error=None):
        super().__init__()
        self.responses = list(responses or [])
        self.error = error
        self.calls: list[dict] = []

    def json(self, system, prompt, schema, **kwargs):
        self.calls.append({"system": system, "prompt": prompt, "schema": schema})
        if self.error:
            raise self.error
        return self.responses.pop(0) if self.responses else {}

    def text(self, system, prompt, **kwargs):
        self.calls.append({"system": system, "prompt": prompt})
        if self.error:
            raise self.error
        return str(self.responses.pop(0)) if self.responses else ""


def make_settings(tmp_path: Path, **env):
    base = {"MIXUP_TODAY": TODAY, "LLM_PROVIDER": "offline", "MIXUP_RUNTIME_DIR": str(tmp_path / "runtime")}
    base.update(env)
    return load_settings(base, use_dotenv=False)


@pytest.fixture
def settings(tmp_path):
    return make_settings(tmp_path)


@pytest.fixture
def store(settings):
    """Fresh store per test (cheap: ~15 documents), runtime files in tmp_path."""
    return Store(settings)


@pytest.fixture
def users(store):
    return store.users


@pytest.fixture
def fake_llm():
    return FakeLLM
