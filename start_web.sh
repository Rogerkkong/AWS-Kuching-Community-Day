#!/usr/bin/env bash
# macOS / Linux: set up (first run only) and start the MixUp Navigator website.
#   chmod +x start_web.sh && ./start_web.sh
set -e
cd "$(dirname "$0")"
PY=${PYTHON:-python3}
if [ ! -x .venv/bin/python ]; then
  echo "Creating .venv with $($PY --version)"
  "$PY" -m venv .venv
  .venv/bin/pip install --upgrade pip -q
  .venv/bin/pip install -r requirements.txt -q
fi
if [ ! -f dist_packs/manifest.json ]; then
  echo "Building the demo packs (first run)"
  .venv/bin/python scripts/reset_demo.py
fi
exec .venv/bin/python -m app.web "$@"
