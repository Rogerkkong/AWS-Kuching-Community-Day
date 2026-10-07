"""Officer-side pack installation: check the update source, copy, verify, atomic install with a
rollback copy, then diff old vs new and create notifications."""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Callable

import httpx

from app.config import TIERS
from app.services.packs import diff as pack_diff
from app.services.packs.verify import PackVerificationError, verify_pack


def active_path(state, tier: int) -> Path:
    return state.settings.packs_dir / f"pack-{TIERS[tier]}.sqlite"


def installed_packs(state) -> list[dict]:
    with state.app_db() as conn:
        rows = [dict(r) for r in conn.execute("SELECT * FROM installed_packs ORDER BY tier")]
    return [r for r in rows if Path(r["file_path"]).exists()]


def device_clearance(state) -> int:
    """Highest clearance among this device's officer profiles. In production a device only ever
    receives the tiers its officer is cleared for (see README / DECISIONS.md)."""
    with state.app_db() as conn:
        row = conn.execute("SELECT MAX(clearance_level) FROM users WHERE role = 'OFFICER'").fetchone()
    return int(row[0] or 0)


def _is_url(source: str) -> bool:
    return source.lower().startswith(("http://", "https://"))


def read_source(source: str) -> tuple[dict, Callable[[str, Path], None]]:
    """Returns (manifest, fetch(file_name, dest))."""
    if _is_url(source):
        base = source.rstrip("/")
        if base.endswith("manifest.json"):
            base = base.rsplit("/", 1)[0]
        r = httpx.get(f"{base}/manifest.json", timeout=15)
        r.raise_for_status()

        def fetch(name: str, dest: Path) -> None:
            with httpx.stream("GET", f"{base}/{name}", timeout=120) as resp:
                resp.raise_for_status()
                with dest.open("wb") as f:
                    for block in resp.iter_bytes():
                        f.write(block)
        return r.json(), fetch

    folder = Path(source).expanduser()
    if folder.name == "manifest.json":
        folder = folder.parent
    manifest_path = folder / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"No manifest.json in {folder}")

    def fetch(name: str, dest: Path) -> None:
        src = (folder / name).resolve()
        if folder.resolve() not in src.parents:
            raise PermissionError("Pack file outside the update folder")
        shutil.copyfile(src, dest)
    return json.loads(manifest_path.read_text(encoding="utf-8")), fetch


def check_updates(state, source: str) -> dict:
    manifest, _ = read_source(source)
    installed = {p["tier"]: p for p in installed_packs(state)}
    cleared = device_clearance(state)
    newest: dict[int, dict] = {}
    for entry in manifest.get("packs", []):
        t = int(entry["tier"])
        if t > cleared:
            continue  # restricted packs are never fetched for devices without that clearance
        if t not in newest or int(entry["version"]) > int(newest[t]["version"]):
            newest[t] = entry
    updates = [e for t, e in sorted(newest.items())
               if t not in installed or int(e["version"]) > int(installed[t]["version"])]
    return {"source": source, "updates": updates, "installed": list(installed.values()),
            "checked_at": datetime.now().isoformat(timespec="seconds")}


def install_entry(state, entry: dict, fetch: Callable[[str, Path], None]) -> dict:
    tier, version = int(entry["tier"]), int(entry["version"])
    settings = state.settings
    settings.packs_dir.mkdir(parents=True, exist_ok=True)
    tmp = settings.packs_dir / f".incoming-{TIERS[tier]}-v{version}.sqlite"
    steps = []
    try:
        fetch(entry["file"], tmp)
        steps.append({"step": "copy", "ok": True, "detail": f"{tmp.stat().st_size / 1e6:.1f} MB"})
        verify_pack(tmp, entry, settings.public_key_path, settings.embedding_model_id)
        steps += [{"step": "checksum", "ok": True, "detail": entry["sha256"][:12]},
                  {"step": "signature", "ok": True, "detail": "Ed25519"},
                  {"step": "embedding_model", "ok": True, "detail": entry.get("embedding_model")}]
    except PackVerificationError as exc:
        tmp.unlink(missing_ok=True)
        steps.append({"step": exc.code, "ok": False, "detail": str(exc)})
        return {"tier": tier, "version": version, "ok": False, "error_code": exc.code, "message": str(exc), "steps": steps}
    except Exception as exc:  # noqa: BLE001
        tmp.unlink(missing_ok=True)
        steps.append({"step": "copy", "ok": False, "detail": str(exc)})
        return {"tier": tier, "version": version, "ok": False, "error_code": "copy", "message": str(exc), "steps": steps}

    active = active_path(state, tier)
    prev_file = settings.packs_dir / f"pack-{TIERS[tier]}.prev.sqlite"
    with state.lock:
        old_row = next((p for p in installed_packs(state) if p["tier"] == tier), None)
        changes = pack_diff.compare(active if active.exists() else None, tmp)
        if active.exists():
            shutil.copyfile(active, prev_file)  # rollback copy
        os.replace(tmp, active)  # atomic on the same volume
        with state.app_db() as conn:
            conn.execute("""INSERT OR REPLACE INTO installed_packs
                            (tier, version, file_path, sha256, embedding_model, installed_at, previous_file_path, previous_version)
                            VALUES (?,?,?,?,?,?,?,?)""",
                         (tier, version, str(active), entry["sha256"], entry.get("embedding_model"),
                          datetime.now().isoformat(timespec="seconds"),
                          str(prev_file) if old_row else None, old_row["version"] if old_row else None))
            notes = pack_diff.create_notifications(conn, changes, tier, version) if old_row else 0
    steps.append({"step": "install", "ok": True, "detail": f"v{old_row['version']} kept for rollback" if old_row else "first install"})
    steps.append({"step": "compare", "ok": True, "detail": f"{len(changes['added'])} new, {len(changes['status_changes'])} status change(s)"})
    return {"tier": tier, "version": version, "ok": True, "steps": steps, "changes": changes,
            "notifications": notes, "previous_version": old_row["version"] if old_row else None}


def install_updates(state, source: str) -> dict:
    manifest, fetch = read_source(source)
    available = check_updates(state, source)["updates"]
    return {"results": [install_entry(state, e, fetch) for e in available]}


def install_local_file(state, pack_path: Path, entry: dict) -> dict:
    """USB / file-picker case: a pack file plus its .sig.json sidecar (same fields as manifest.json)."""
    if int(entry.get("tier", 99)) > device_clearance(state):
        return {"ok": False, "error_code": "clearance", "message": "This device is not cleared for that pack tier"}
    current = next((p for p in installed_packs(state) if p["tier"] == int(entry["tier"])), None)
    if current and int(entry["version"]) <= int(current["version"]):
        return {"ok": False, "error_code": "version",
                "message": f"v{entry['version']} is not newer than installed v{current['version']}"}

    def fetch(_: str, dest: Path) -> None:
        shutil.copyfile(pack_path, dest)
    return install_entry(state, entry, fetch)


def rollback(state, tier: int) -> dict:
    row = next((p for p in installed_packs(state) if p["tier"] == tier), None)
    if not row or not row.get("previous_file_path") or not Path(row["previous_file_path"]).exists():
        return {"ok": False, "message": "No previous version to roll back to"}
    with state.lock:
        os.replace(row["previous_file_path"], row["file_path"])
        with state.app_db() as conn:
            conn.execute("UPDATE installed_packs SET version = ?, previous_file_path = NULL, previous_version = NULL WHERE tier = ?",
                         (row["previous_version"], tier))
    return {"ok": True, "version": row["previous_version"]}
