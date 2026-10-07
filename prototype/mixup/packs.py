"""Signed knowledge packs (desktop edition, guide 7.7 and 7.8) in FAST MODE.

Publisher side: build one pack per clearance tier from the live library, hash it
(SHA-256), sign the hash (Ed25519) and write dist_packs/manifest.json.
Officer side: check the manifest for newer packs the user is cleared for, verify
checksum + signature + embedding model, install by atomic rename (keeping the
previous file for rollback), then diff old vs new and notify the user.

Packs are JSON files here (SQLite in the desktop build). The demo keys are
generated locally; in production the private key never ships with the app.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import uuid
from datetime import datetime
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from mixup import access
from mixup.models import CLASSIFICATION_LABELS

TIERS = (0, 1, 2)
EMBEDDING_MODEL = "bm25-offline-v1"  # recorded in each pack; a mismatch is refused (guide rule 8)
DIST_DIR = "dist_packs"
INSTALLED_DIR = "installed_packs"
INSTALLED_JSON = "installed_packs.json"
NOTIFICATIONS = "notifications.json"


# --- keys -------------------------------------------------------------------

def _keys_dir(store) -> Path:
    path = store.runtime_dir / "keys"
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_keys(store) -> tuple[Ed25519PrivateKey, Ed25519PublicKey]:
    """Load the demo publisher key pair, creating it on first use."""
    priv_path, pub_path = _keys_dir(store) / "publisher_private.pem", _keys_dir(store) / "publisher_public.pem"
    if priv_path.exists():
        private = serialization.load_pem_private_key(priv_path.read_bytes(), password=None)
    else:
        private = Ed25519PrivateKey.generate()
        priv_path.write_bytes(private.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        pub_path.write_bytes(private.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    public = serialization.load_pem_public_key(pub_path.read_bytes())
    return private, public


# --- publisher: build + sign ------------------------------------------------

def tier_name(tier: int) -> str:
    return CLASSIFICATION_LABELS.get(tier, ("?", "?"))[0].lower()


def _pack_payload(store, tier: int, version: int) -> dict:
    docs = [d for d in store.docs.values() if d.classification_level == tier]
    ids = {d.doc_id for d in docs}
    rels = [r for r in store.verified_relations() if r.source_doc_id in ids and r.target_doc_id in ids]
    return {
        "manifest": {
            "pack_id": f"pack-{tier_name(tier)}-v{version}",
            "tier": tier,
            "version": version,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "embedding_model": EMBEDDING_MODEL,
            "document_count": len(docs),
        },
        "documents": [
            {
                "doc_id": d.doc_id, "circular_no": d.circular_no, "title": d.title,
                "status": d.status, "status_reason": d.status_reason,
                "jurisdiction": d.jurisdiction, "cluster": d.cluster,
                "effective_date": str(d.effective_date or ""),
            }
            for d in sorted(docs, key=lambda d: d.doc_id)
        ],
        "relations": [
            {"source": r.source_doc_id, "target": r.target_doc_id, "type": r.relation_type}
            for r in rels
        ],
    }


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_manifest(store) -> dict:
    return store.read_json(f"{DIST_DIR}/manifest.json", {"publisher": "MixUp Navigator demo publisher", "packs": []}) \
        or {"publisher": "MixUp Navigator demo publisher", "packs": []}


def next_version(store) -> int:
    versions = [p.get("version", 0) for p in read_manifest(store).get("packs", [])]
    return (max(versions) if versions else 0) + 1


def build_packs(store, version: int | None = None) -> list[dict]:
    """Write one signed pack per tier and update dist_packs/manifest.json."""
    private, _ = ensure_keys(store)
    version = version or next_version(store)
    dist = store.runtime_dir / DIST_DIR
    dist.mkdir(parents=True, exist_ok=True)
    manifest = read_manifest(store)
    entries = []
    for tier in TIERS:
        payload = _pack_payload(store, tier, version)
        name = f"{payload['manifest']['pack_id']}.json"
        path = dist / name
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        digest = sha256_of(path)
        signature = private.sign(bytes.fromhex(digest))  # sign the hash, as in the guide
        entry = {
            "tier": tier, "version": version, "file": name, "sha256": digest,
            "signature": base64.b64encode(signature).decode("ascii"),
            "embedding_model": EMBEDDING_MODEL, "created_at": payload["manifest"]["created_at"],
            "document_count": payload["manifest"]["document_count"],
        }
        manifest["packs"] = [p for p in manifest.get("packs", []) if not (p["tier"] == tier and p["version"] == version)]
        manifest["packs"].append(entry)
        entries.append(entry)
    manifest["packs"].sort(key=lambda p: (p["tier"], p["version"]))
    store.write_json(f"{DIST_DIR}/manifest.json", manifest)
    return entries


# --- officer: check, verify, install ----------------------------------------

def installed(store) -> dict[str, dict]:
    """Installed packs keyed by tier (as a string, since JSON keys are strings)."""
    return store.read_json(INSTALLED_JSON, {}) or {}


def check_updates(store, user) -> list[dict]:
    """Manifest entries newer than the installed version, for tiers the user is cleared for."""
    have = installed(store)
    out = []
    for entry in read_manifest(store).get("packs", []):
        tier = int(entry["tier"])
        if tier > getattr(user, "clearance_level", 0):
            continue  # restricted packs are never offered to uncleared officers
        current = int(have.get(str(tier), {}).get("version", 0))
        if int(entry["version"]) > current:
            out.append(entry)
    latest: dict[int, dict] = {}
    for e in out:
        if int(e["tier"]) not in latest or e["version"] > latest[int(e["tier"])]["version"]:
            latest[int(e["tier"])] = e
    return [latest[t] for t in sorted(latest)]


def verify_pack(store, path: Path, entry: dict) -> tuple[bool, str]:
    """Checksum, signature and embedding-model checks. Returns (ok, reason)."""
    if not path.exists():
        return False, "Fail pek tidak dijumpai / pack file missing"
    digest = sha256_of(path)
    if digest != entry.get("sha256"):
        return False, "Checksum SHA-256 tidak sepadan / SHA-256 checksum mismatch (file changed)"
    _, public = ensure_keys(store)
    try:
        public.verify(base64.b64decode(entry.get("signature", "")), bytes.fromhex(digest))
    except (InvalidSignature, ValueError):
        return False, "Tandatangan Ed25519 tidak sah / Ed25519 signature invalid (not from the publisher)"
    try:
        model = json.loads(path.read_text(encoding="utf-8"))["manifest"].get("embedding_model")
    except (OSError, ValueError, KeyError):
        return False, "Pek rosak / pack unreadable"
    if model != EMBEDDING_MODEL:
        return False, f"Model embedding berbeza / embedding model mismatch ({model} vs {EMBEDDING_MODEL})"
    return True, "ok"


def _diff(old: dict | None, new: dict) -> dict:
    old_docs = {d["doc_id"]: d for d in (old or {}).get("documents", [])}
    new_docs = {d["doc_id"]: d for d in new.get("documents", [])}
    added = [d for i, d in new_docs.items() if i not in old_docs]
    status_changes = [
        {"doc_id": i, "circular_no": d["circular_no"], "from": old_docs[i]["status"], "to": d["status"], "reason": d["status_reason"]}
        for i, d in new_docs.items() if i in old_docs and old_docs[i]["status"] != d["status"]
    ]
    return {"added": added, "status_changes": status_changes}


def install_update(store, user, entry: dict, source_path: Path | None = None) -> dict:
    """Verify and install one pack for the user; previous version is kept for rollback."""
    tier = int(entry["tier"])
    src = source_path or (store.runtime_dir / DIST_DIR / entry["file"])
    ok, reason = verify_pack(store, src, entry)
    result = {"tier": tier, "version": entry["version"], "ok": ok, "reason": reason, "diff": None}
    if not ok:
        return result  # previous version stays active
    inst_dir = store.runtime_dir / INSTALLED_DIR
    inst_dir.mkdir(parents=True, exist_ok=True)
    final = inst_dir / f"pack-{tier_name(tier)}.json"
    previous = inst_dir / f"pack-{tier_name(tier)}.prev.json"
    old = None
    if final.exists():
        old = json.loads(final.read_text(encoding="utf-8"))
        os.replace(final, previous)
    tmp = final.with_suffix(".tmp")
    tmp.write_bytes(src.read_bytes())
    os.replace(tmp, final)  # atomic install
    have = installed(store)
    have[str(tier)] = {
        "version": entry["version"], "file": str(final), "sha256": entry["sha256"],
        "embedding_model": entry["embedding_model"], "installed_at": datetime.now().isoformat(timespec="seconds"),
        "previous_file": str(previous) if old else "",
    }
    store.write_json(INSTALLED_JSON, have)
    new = json.loads(final.read_text(encoding="utf-8"))
    diff = _diff(old, new)
    result["diff"] = diff
    _notify(store, user, entry, diff)
    return result


def _notify(store, user, entry: dict, diff: dict) -> list[dict]:
    """One notification per status change or new document the user may see."""
    rows = store.read_json(NOTIFICATIONS, []) or []
    created = []
    uid = getattr(user, "user_id", None)
    items = [("status", c) for c in diff["status_changes"]] + [("added", d) for d in diff["added"]]
    for kind, item in items:
        doc = store.docs.get(item["doc_id"])
        if doc is None or not access.can_see(user, doc):
            continue
        key = f"pack:{entry['tier']}:{entry['version']}:{item['doc_id']}"
        if any(n.get("relation_id") == key and n.get("user_id") == uid for n in rows):
            continue
        if kind == "status":
            title = f"{item['circular_no']}: {item['from']} -> {item['to']}"
            summ_ms = f"Kemas kini pek v{entry['version']}: {item['circular_no']} kini {item['to']} ({item['reason']})."
            summ_en = f"Pack update v{entry['version']}: {item['circular_no']} is now {item['to']} ({item['reason']})."
        else:
            title = f"{item['circular_no']}: pekeliling baharu / new circular"
            summ_ms = f"Kemas kini pek v{entry['version']}: pekeliling baharu {item['circular_no']} - {item['title']}."
            summ_en = f"Pack update v{entry['version']}: new circular {item['circular_no']} - {item['title']}."
        note = {
            "id": f"N-{uuid.uuid4().hex[:10]}", "user_id": uid, "doc_id": item["doc_id"], "new_doc_id": "",
            "relation_id": key, "relation_type": "PACK_UPDATE", "title": title, "title_en": title,
            "summary_ms": summ_ms, "summary_en": summ_en, "effective_date": "", "cluster": doc.cluster,
            "pack_version": entry["version"], "created_at": datetime.now().isoformat(timespec="seconds"), "read": False,
        }
        rows.append(note)
        created.append(note)
    if created:
        store.write_json(NOTIFICATIONS, rows)
    return created


def tampered_copy(store, entry: dict) -> Path:
    """Demo helper: a copy of the pack with one character changed (must be rejected)."""
    src = store.runtime_dir / DIST_DIR / entry["file"]
    data = bytearray(src.read_bytes())
    i = data.find(b'"document_count"')
    data[i + 1] = ord("D") if i >= 0 else data[0]
    out = store.runtime_dir / DIST_DIR / f"tampered-{entry['file']}"
    out.write_bytes(bytes(data))
    return out
