"""Pack verification before installation: SHA-256, Ed25519 signature, manifest row, embedding model."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from app.services.packs.sign import sha256_file, verify_digest


class PackVerificationError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code  # checksum | signature | manifest | embedding_model | unreadable


def read_pack_manifest(path: Path) -> dict:
    uri = Path(path).resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM manifest LIMIT 1").fetchone()
        if row is None:
            raise PackVerificationError("manifest", "Pack has no manifest row")
        return dict(row)
    except sqlite3.DatabaseError as exc:
        raise PackVerificationError("unreadable", f"Pack is not a readable SQLite file: {exc}") from exc
    finally:
        conn.close()


def verify_pack(path: Path, entry: dict, public_key: Path, expected_embedding_model: str) -> dict:
    """Raises PackVerificationError; returns the pack's manifest row on success. Checks run on the
    copied file, so what is verified is exactly what gets installed."""
    digest = sha256_file(path)
    if digest != entry.get("sha256"):
        raise PackVerificationError("checksum", f"SHA-256 mismatch (expected {str(entry.get('sha256'))[:12]}..., got {digest[:12]}...)")
    if not public_key.exists():
        raise PackVerificationError("signature", "Publisher public key is missing from the app")
    if not verify_digest(public_key, digest, entry.get("signature", "")):
        raise PackVerificationError("signature", "Ed25519 signature is not valid for the bundled publisher key")
    manifest = read_pack_manifest(path)
    if int(manifest["tier"]) != int(entry["tier"]) or int(manifest["version"]) != int(entry["version"]):
        raise PackVerificationError("manifest", "Pack manifest does not match manifest.json (tier/version)")
    if manifest["embedding_model"] != expected_embedding_model:
        raise PackVerificationError(
            "embedding_model",
            f"Pack was built with embedding model '{manifest['embedding_model']}' but this app uses "
            f"'{expected_embedding_model}'. Search vectors would not be comparable.")
    return manifest
