"""Build, checksum and sign one knowledge pack per clearance tier into dist_packs/ and update
dist_packs/manifest.json (also the demo update source).

Usage: python scripts/build_pack.py --version 1 [--tiers 0,1] [--force]
"""
from __future__ import annotations

import argparse
import sys

import _bootstrap  # noqa: F401
from app.config import get_settings
from app.services.packs.build import build_packs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", type=int, required=True)
    ap.add_argument("--tiers", default=None, help="comma-separated tiers (default: every tier with documents)")
    ap.add_argument("--force", action="store_true", help="allow rebuilding an existing version")
    args = ap.parse_args()
    tiers = [int(t) for t in args.tiers.split(",")] if args.tiers else None
    entries = build_packs(get_settings(), args.version, tiers, force=args.force)
    print(f"{len(entries)} pack(s) written to {get_settings().dist_packs_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
