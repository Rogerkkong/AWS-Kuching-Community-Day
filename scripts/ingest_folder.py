"""Ingest every PDF in a folder into workspace/publisher.db (parse, OCR, metadata, chunks, embeddings,
relation candidates), then load data/relations.csv, recompute statuses and change summaries.

Usage: python scripts/ingest_folder.py [data/raw] [--no-llm] [--reset]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import _bootstrap  # noqa: F401
from app import db
from app.config import get_settings
from app.services.inference.client import get_client
from app.services.ingest.pipeline import ingest_paths


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", nargs="?", default="data/raw")
    ap.add_argument("--no-llm", action="store_true", help="skip METADATA/RELATION prompts (regex + CSV only)")
    ap.add_argument("--reset", action="store_true", help="delete workspace/publisher.db first")
    args = ap.parse_args()
    s = get_settings()
    folder = Path(args.folder)
    paths = sorted(p for p in folder.iterdir() if p.suffix.lower() == ".pdf") if folder.is_dir() else []
    if not paths:
        print(f"No PDFs in {folder}. Put documents there or run scripts/make_synthetic_docs.py.")
        return 1
    if args.reset and s.publisher_db.exists():
        s.publisher_db.unlink()
    client = get_client()
    health = client.health()
    if not health.get("reachable"):
        print("Inference backend not reachable:", health.get("detail"))
        return 2
    print(f"Backend {health['backend']} | embedding model {s.embedding_model_id} | {len(paths)} file(s)")
    conn = db.init_publisher_db(s.publisher_db)
    try:
        ingest_paths(conn, paths, client, s, echo=True, use_llm=not args.no_llm)
        for r in conn.execute("SELECT circular_no, doc_type, classification_level, status, status_reason FROM documents ORDER BY issue_date"):
            print(f"  {r[0]:<14} {r[1]:<9} tier {r[2]}  {r[3]:<9} {r[4] or ''}")
        pending = conn.execute("SELECT COUNT(*) FROM relations WHERE verified = 0").fetchone()[0]
        print(f"{pending} relation(s) waiting for verification in the Publisher queue.")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
