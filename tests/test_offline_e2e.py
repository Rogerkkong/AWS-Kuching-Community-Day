"""End-to-end ask over real HTTP on 127.0.0.1 with every non-localhost socket blocked (pytest-socket)."""
import json
import socket

import httpx
import pytest
from pytest_socket import SocketConnectBlockedError, socket_allow_hosts

from conftest import make_officer


@pytest.fixture
def offline():
    socket_allow_hosts(["127.0.0.1", "localhost", "::1"], allow_unix_socket=True)
    yield
    from pytest_socket import enable_socket

    enable_socket()


def test_offline_end_to_end_ask(env, tmp_path, offline):
    import dataclasses

    from app.desktop import ApiServer

    # Prove the network really is blocked for anything but localhost.
    with pytest.raises(SocketConnectBlockedError):
        socket.create_connection(("1.1.1.1", 53), timeout=1)

    # Prepare an officer data folder with packs installed (local folder update source).
    make_officer(env.settings, tmp_path / "officer")
    import app.desktop as desktop

    s = dataclasses.replace(env.settings, data_dir=tmp_path / "officer")
    original = desktop.create_app
    desktop.create_app = lambda mode, token: original(mode, token, s)
    try:
        server = ApiServer("officer")
        health = server.start()
        assert health["packs_installed"] == 2
        headers = {"X-Session-Token": server.token}
        with httpx.stream("POST", f"{server.base_url}/api/ask", headers=headers,
                          json={"query": "Berapa hari cuti rehat yang boleh dibawa ke hadapan?"}, timeout=30) as r:
            body = "".join(r.iter_text())
        events = [b.split("\n") for b in body.strip().split("\n\n")]
        assert events[0][0] == "event: sources" and events[-1][0] == "event: final"
        final = json.loads(events[-1][1][6:])
        assert final["answerable"] and final["citations"]
        assert httpx.get(f"{server.base_url}/api/users", timeout=5).status_code == 401
        server.stop()
    finally:
        desktop.create_app = original
