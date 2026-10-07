"""Ed25519 signing of pack checksums. The private key stays on the Publisher machine
(workspace/keys/, gitignored); only the public key is bundled with the app."""
from __future__ import annotations

import base64
import hashlib
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def generate_keypair(private_path: Path, public_path: Path, overwrite: bool = False) -> None:
    if private_path.exists() and not overwrite:
        raise FileExistsError(f"{private_path} exists; pass overwrite=True to replace it")
    key = Ed25519PrivateKey.generate()
    private_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.parent.mkdir(parents=True, exist_ok=True)
    private_path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                               serialization.NoEncryption()))
    public_path.write_bytes(key.public_key().public_bytes(serialization.Encoding.PEM,
                                                          serialization.PublicFormat.SubjectPublicKeyInfo))


def load_private(path: Path) -> Ed25519PrivateKey:
    key = serialization.load_pem_private_key(Path(path).read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("Publisher key is not Ed25519")
    return key


def load_public(path: Path) -> Ed25519PublicKey:
    key = serialization.load_pem_public_key(Path(path).read_bytes())
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError("Publisher public key is not Ed25519")
    return key


def sign_digest(private_path: Path, sha256_hex: str) -> str:
    """Signature over the ASCII hex digest, base64-encoded (as stored in manifest.json)."""
    return base64.b64encode(load_private(private_path).sign(sha256_hex.encode("ascii"))).decode("ascii")


def verify_digest(public_path: Path, sha256_hex: str, signature_b64: str) -> bool:
    try:
        load_public(public_path).verify(base64.b64decode(signature_b64), sha256_hex.encode("ascii"))
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False
