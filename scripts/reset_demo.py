"""Reset the demo to its starting state for a rehearsal: archive (move, never delete) the Publisher
database, uploads, built packs and, optionally, the Officer data folder into workspace/archive/<time>/,
then re-ingest data/raw and build pack v1. Keys are kept.

Usage: python scripts/reset_demo.py [--officer] [--no-build]
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from datetime import datetime

import _bootstrap  # noqa: F401
from app import db
from app.config import get_settings
from app.services.inference.client import get_client
from app.services.ingest.pipeline import ingest_paths
from app.services.packs.build import build_packs
from app.services.packs.sign import generate_keypair


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--officer", action="store_true", help="also archive the Officer data folder (installed packs, app.db)")
    ap.add_argument("--no-build", action="store_true", help="only archive")
    args = ap.parse_args()
    if "INFERENCE_BACKEND" not in os.environ and not get_client().health().get("reachable"):
        # Same rule as `python -m app.web`, so the packs match the website's embedding model.
        print("Ollama not reachable -> building with the fake backend (INFERENCE_BACKEND=fake).")
        os.environ["INFERENCE_BACKEND"] = "fake"
        from app.config import reset_settings
        from app.services.inference.client import set_client
        reset_settings()
        set_client(None)
    s = get_settings()
    archive = s.workspace_dir / "archive" / datetime.now().strftime("%Y%m%d-%H%M%S")
    moved = []

    def move(path, name=None):
        if path.exists():
            dest = archive / (name or path.name)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(path), str(dest))
            moved.append(path)

    move(s.publisher_db)
    move(s.uploads_dir)
    for p in sorted(s.dist_packs_dir.glob("pack-*.sqlite")) + sorted(s.dist_packs_dir.glob("pack-*.sig.json")):
        move(p, f"dist_packs/{p.name}")
    move(s.dist_packs_dir / "manifest.json", "dist_packs/manifest.json")
    if args.officer:
        move(s.data_dir, "officer-data")
    print(f"Archived {len(moved)} item(s) to {archive}" if moved else "Nothing to archive.")
    if args.no_build:
        return 0

    if not s.private_key_path.exists():
        # Fresh clone: the private key is never in git, so create this machine's own key pair.
        generate_keypair(s.private_key_path, s.public_key_path, overwrite=True)
        print("Created a new publisher key pair (workspace/keys/ + app/resources/publisher_public.pem)")
    client = get_client()
    if not client.health().get("reachable"):
        print("Inference backend not reachable; start Ollama or set INFERENCE_BACKEND=fake.")
        return 2
    conn = db.init_publisher_db(s.publisher_db)
    try:
        ingest_paths(conn, sorted(s.raw_dir.glob("*.pdf")), client, s)
    finally:
        conn.close()
    build_packs(s, 1)
    print("Demo reset: publisher.db rebuilt from data/raw, packs v1 in", s.dist_packs_dir)
    print("Held back for the live update: data/incoming/PP-3-2026.pdf")
    return 0


if __name__ == "__main__":
    sys.exit(main())
