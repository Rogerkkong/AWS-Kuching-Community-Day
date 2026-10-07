"""Website mode for live demos: one site in the browser; switching account switches the view
(officer accounts -> Officer screens, Faizal -> Publisher screens).

    python -m app.web                 # http://127.0.0.1:8765, opens it in the browser
    python -m app.web --no-open       # just print the URLs

Falls back to the deterministic fake backend when Ollama is not reachable (and INFERENCE_BACKEND
was not set explicitly), so the demo always starts.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import webbrowser


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-open", action="store_true")
    args = ap.parse_args(argv)

    from app.config import reset_settings
    from app.services.inference.client import get_client, set_client, warm_up_async

    if "INFERENCE_BACKEND" not in os.environ and not get_client().health().get("reachable"):
        print("Ollama not reachable -> using the fake backend (INFERENCE_BACKEND=fake).")
        os.environ["INFERENCE_BACKEND"] = "fake"
        reset_settings()
        set_client(None)

    from app.desktop import ApiServer

    site = ApiServer("web", args.port)
    site.start()
    if get_client().health().get("reachable"):
        warm_up_async()

    print("\nMixUp Navigator - website mode")
    print(f"  Open      : {site.window_url}")
    print("  Switch account (bottom left) to change view: officers <-> Faizal (Publisher)")
    print("Keep this window open. Press Ctrl+C to stop.\n", flush=True)
    if not args.no_open:
        webbrowser.open(site.window_url)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    site.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
