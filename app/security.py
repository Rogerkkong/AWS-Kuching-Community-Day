"""Local-API protection: session token on every API request and a Host check (rule 2).

The static UI bundle (HTML/JS/CSS/fonts) carries no data and is served without a token; every
`/api/*` and `/health` request must send `X-Session-Token`. The Host header must be 127.0.0.1 or
localhost, which blocks DNS-rebinding pages from talking to the API. No CORS headers are ever added,
so other origins cannot read responses.
"""
from __future__ import annotations

import hmac
import json
import secrets
import socket

PROTECTED_PREFIXES = ("/api", "/health")
ALLOWED_HOSTS = {"127.0.0.1", "localhost"}
TOKEN_HEADER = b"x-session-token"


def new_token() -> str:
    return secrets.token_urlsafe(32)


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class SessionTokenMiddleware:
    """Pure ASGI middleware so streaming (SSE) responses pass through untouched."""

    def __init__(self, app, token: str, public: bool = False):
        self.app = app
        self.token = token
        self.public = public  # hosted demo with synthetic data only (PN_PUBLIC_DEMO=1)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or self.public:
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers") or [])
        host = headers.get(b"host", b"").decode("latin-1").rsplit(":", 1)[0].strip("[]")
        if host not in ALLOWED_HOSTS:
            return await _reject(send, 400, "Host not allowed")
        path = scope.get("path", "")
        if path.startswith(PROTECTED_PREFIXES):
            supplied = headers.get(TOKEN_HEADER, b"").decode("latin-1")
            if not supplied or not hmac.compare_digest(supplied, self.token):
                return await _reject(send, 401, "Missing or invalid session token")
        return await self.app(scope, receive, send)


async def _reject(send, status: int, message: str) -> None:
    body = json.dumps({"detail": message}).encode()
    await send({"type": "http.response.start", "status": status,
                "headers": [(b"content-type", b"application/json"),
                            (b"content-length", str(len(body)).encode())]})
    await send({"type": "http.response.body", "body": body})
