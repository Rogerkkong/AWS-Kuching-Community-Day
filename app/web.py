"""Website mode for live demos: Officer site + Publisher site in the browser (no desktop window).

    python -m app.web                 # Officer on :8765, Publisher on :8766, opens both in the browser
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
    ap.add_argument("--officer-port", type=int, default=8765)
    ap.add_argument("--publisher-port", type=int, default=8766)
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

    officer = ApiServer("officer", args.officer_port)
    officer.start()
    publisher = ApiServer("publisher", args.publisher_port)
    publisher.start()
    if get_client().health().get("reachable"):
        warm_up_async()

    print("\nPekeliling Navigator - website mode")
    print(f"  Officer   : {officer.window_url}")
    print(f"  Publisher : {publisher.window_url}")
    print("Keep this window open. Press Ctrl+C to stop.\n", flush=True)
    if not args.no_open:
        webbrowser.open(publisher.window_url)
        webbrowser.open(officer.window_url)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    officer.stop()
    publisher.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
