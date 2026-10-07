"""Desktop launcher: local API on 127.0.0.1 (free port, session token) + pywebview window.

    python -m app.desktop [--mode officer|publisher] [--browser] [--smoke]

--browser  serve only and print the URL (development; open it in any browser on this PC)
--smoke    start the API, print /health and exit (used by tests and the packaged-build check)
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time

import httpx
import uvicorn

from app.config import APP_TITLE, get_settings
from app.main import create_app
from app.security import free_port, new_token
from app.services.inference.client import get_client, warm_up_async


class ApiServer:
    def __init__(self, mode: str, port: int | None = None):
        self.mode = mode
        self.token = new_token()
        self.port = port or free_port()
        self.app = create_app(mode, self.token)
        config = uvicorn.Config(self.app, host="127.0.0.1", port=self.port, log_level="warning", access_log=False)
        self.server = uvicorn.Server(config)
        self.thread = threading.Thread(target=self.server.run, name="local-api", daemon=True)

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    @property
    def window_url(self) -> str:
        return f"{self.base_url}/?token={self.token}"

    def start(self, timeout: float = 30.0) -> dict:
        self.thread.start()
        deadline = time.time() + timeout
        last_error = None
        while time.time() < deadline:
            try:
                r = httpx.get(f"{self.base_url}/health", headers={"X-Session-Token": self.token}, timeout=2.0)
                if r.status_code == 200:
                    return r.json()
            except httpx.HTTPError as exc:
                last_error = exc
            time.sleep(0.15)
        raise RuntimeError(f"Local API did not start: {last_error}")

    def stop(self) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=5)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=["officer", "publisher"], default="officer")
    ap.add_argument("--browser", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--port", type=int, default=None, help="fixed port (development with --browser only)")
    ap.add_argument("--smoke-out", default=None, help="with --smoke: also write the health JSON to this file")
    args = ap.parse_args(argv)

    settings = get_settings()
    api = ApiServer(args.mode, args.port if args.browser else None)
    health = api.start()
    if args.smoke:
        report = json.dumps({"url": api.base_url, **health}, indent=2)
        print(report)
        if args.smoke_out:
            with open(args.smoke_out, "w", encoding="utf-8") as f:
                f.write(report)
        api.stop()
        return 0

    # Warm the model in the background; the UI shows "Memuatkan model..." until /health says ready.
    try:
        if get_client().health().get("reachable"):
            warm_up_async()
    except Exception:  # noqa: BLE001 - the setup screen explains what is missing
        pass

    title = APP_TITLE if args.mode == "officer" else f"{APP_TITLE} - Publisher"
    if args.browser:
        # Development convenience: the URL (with this run's token) is also written to the per-user data folder.
        (settings.data_dir / "dev-url.txt").write_text(api.window_url, encoding="utf-8")
        print(f"{title} ({settings.inference_backend}) running. Open:\n  {api.window_url}\nPress Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        api.stop()
        return 0

    import webview  # imported late so --smoke/--browser work without a GUI toolkit

    webview.create_window(title, api.window_url, width=1440, height=900, min_size=(1100, 680),
                          background_color="#F6F4F0")
    webview.start(private_mode=True)
    api.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
