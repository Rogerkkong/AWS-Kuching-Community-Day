"""Automatic provider detection never needs the user to choose a mode."""

import socket

from mixup import netcheck


class _Settings:
    ollama_base_url = "http://localhost:1"  # nothing listens here
    bedrock_api_key = None
    aws_profile = None


def test_offline_when_nothing_is_reachable(monkeypatch):
    netcheck.clear_cache()

    def no_net(*a, **k):
        raise OSError("no route")

    monkeypatch.setattr(socket, "create_connection", no_net)
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    d = netcheck.detect(_Settings())
    assert d.provider == "offline" and not d.online and not d.ollama


def test_ollama_wins_when_local_server_answers(monkeypatch):
    netcheck.clear_cache()
    monkeypatch.setattr(socket, "create_connection", lambda *a, **k: (_ for _ in ()).throw(OSError()))
    monkeypatch.setattr(netcheck, "ollama_available", lambda *a, **k: True)
    d = netcheck.detect(_Settings())
    assert d.provider == "ollama"


def test_bedrock_needs_internet_and_credentials(monkeypatch):
    netcheck.clear_cache()
    monkeypatch.setattr(netcheck, "network_online", lambda *a, **k: True)
    monkeypatch.setattr(netcheck, "ollama_available", lambda *a, **k: False)
    s = _Settings()
    s.bedrock_api_key = "demo-key"
    assert netcheck.detect(s).provider == "bedrock"
    netcheck.clear_cache()
    monkeypatch.setattr(netcheck, "network_online", lambda *a, **k: False)
    assert netcheck.detect(s).provider == "offline"


def test_forced_offline_overrides_detection(monkeypatch):
    netcheck.clear_cache()
    monkeypatch.setattr(netcheck, "ollama_available", lambda *a, **k: True)
    monkeypatch.setattr(netcheck, "network_online", lambda *a, **k: True)
    assert netcheck.detect(_Settings(), forced_offline=True).provider == "offline"
