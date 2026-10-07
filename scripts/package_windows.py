"""Build the Windows one-folder app with PyInstaller and smoke-test it.

    python scripts/package_windows.py [--skip-ui]

Output: dist/PekelilingNavigator/PekelilingNavigator.exe (copy the whole folder). Models are not
bundled: install Ollama + models on the target PC, or use the llamacpp backend with models/ next to
the executable. Put packs in the update folder or install them from file in the app.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(cmd: list[str], **kw) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, **kw)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skip-ui", action="store_true", help="do not rebuild ui/dist")
    args = ap.parse_args()
    if not args.skip_ui or not (ROOT / "ui" / "dist" / "index.html").exists():
        npm = shutil.which("npm") or shutil.which("npm.cmd")
        if not npm:
            print("npm not found and ui/dist is missing; install Node.js 20 LTS to build the UI.")
            return 1
        run([npm, "run", "build"], cwd=ROOT / "ui")
    if not (ROOT / "app" / "resources" / "publisher_public.pem").exists():
        print("Missing app/resources/publisher_public.pem; run scripts/make_keys.py on the Publisher machine.")
        return 1
    run([sys.executable, "-m", "PyInstaller", str(ROOT / "packaging" / "pyinstaller.spec"), "--noconfirm",
         "--distpath", str(ROOT / "dist"), "--workpath", str(ROOT / "build")], cwd=ROOT)

    exe = ROOT / "dist" / "PekelilingNavigator" / "PekelilingNavigator.exe"
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "health.json"
        env = {**os.environ, "INFERENCE_BACKEND": "fake", "PN_DATA_DIR": str(Path(tmp) / "data")}
        result = subprocess.run([str(exe), "--smoke", "--smoke-out", str(out)], env=env, timeout=120)
        if result.returncode != 0 or not out.exists():
            print("Smoke test FAILED (exit code", result.returncode, ")")
            return 1
        health = json.loads(out.read_text(encoding="utf-8"))
        print("Smoke test OK:", health["status"], "| mode", health["mode"], "| sqlite", health["sqlite_version"],
              "| sqlite-vec", health["sqlite_vec"])
    size = sum(f.stat().st_size for f in exe.parent.rglob("*") if f.is_file())
    print(f"Built {exe} ({size / 1e6:.0f} MB folder)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
