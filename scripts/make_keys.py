"""Create the Publisher Ed25519 key pair.

Private key -> workspace/keys/publisher_private.pem (gitignored; never bundled with the app).
Public key  -> app/resources/publisher_public.pem (bundled; Officer mode verifies packs with it).
"""
from __future__ import annotations

import argparse
import sys

import _bootstrap  # noqa: F401
from app.config import get_settings
from app.services.packs.sign import generate_keypair


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="replace an existing key pair (old packs will no longer verify)")
    args = ap.parse_args()
    s = get_settings()
    if s.private_key_path.exists() and not args.force:
        print(f"Key pair already exists ({s.private_key_path}); nothing to do. Use --force to replace it.")
        return 0
    generate_keypair(s.private_key_path, s.public_key_path, overwrite=True)
    print("private key:", s.private_key_path)
    print("public key :", s.public_key_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
