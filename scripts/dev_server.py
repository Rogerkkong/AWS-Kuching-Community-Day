"""Development helper: run the local API in --browser mode with the fake backend on a fixed port.

Usage: python scripts/dev_server.py 8765 [--mode publisher] [--real]
(--real keeps INFERENCE_BACKEND from the environment / .env instead of forcing "fake")
"""
import os
import sys
from pathlib import Path

import _bootstrap  # noqa: F401

ROOT = Path(__file__).resolve().parent.parent
args = sys.argv[1:]
port = args.pop(0) if args and args[0].isdigit() else "8765"
if "--real" in args:
    args.remove("--real")
else:
    os.environ["INFERENCE_BACKEND"] = "fake"
    os.environ.setdefault("PN_DATA_DIR", str(ROOT / "workspace" / "officer-dev"))

from app.desktop import main  # noqa: E402

sys.exit(main(["--browser", "--port", port, *args]))
