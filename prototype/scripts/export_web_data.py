"""Export the MixUp Navigator corpus for the self-contained web edition.

    .venv/bin/python scripts/export_web_data.py            # writes web/data.js
    .venv/bin/python scripts/export_web_data.py --out x.js  # somewhere else

The web app (web/index.html) is opened by double-clicking, so it cannot fetch()
local files. Everything it needs is written as ONE JavaScript global:

    window.MX_DATA = { documents, relations, users, glossary, golden, eval,
                       today, upload_demo, labels_meta }

Documents carry their pages and clause-aware chunks (made by mixup.ingest), so
engine.js never has to parse markdown. Statuses are recomputed here with the
Python engine (today = MIXUP_TODAY or 2026-10-07) and recomputed again in the
browser from the same relations, so both editions agree.

The export uses a private, empty runtime folder: uploads, pending relations and
query logs made during a live demo never leak into data.js.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from dataclasses import asdict
from datetime import date
from pathlib import Path

PROTOTYPE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROTOTYPE_DIR))

from mixup import evaluate  # noqa: E402
from mixup.config import load_settings  # noqa: E402
from mixup.models import CLASSIFICATION_LABELS  # noqa: E402
from mixup.store import Store  # noqa: E402

DEFAULT_TODAY = date(2026, 10, 7)
DEFAULT_OUT = PROTOTYPE_DIR / "web" / "data.js"
UPLOAD_DEMO = PROTOTYPE_DIR / "data" / "upload_demo" / "SPP-1-2026.md"
RESULTS_JSON = PROTOTYPE_DIR / "eval" / "results" / "results.json"

# English display names for the demo profiles (users.json is in Malay).
USER_NAMES_EN = {
    "FED-T0": "Federal Officer (Terbuka)",
    "SWK-T0": "Sarawak Officer (Terbuka)",
    "FED-T1": "Restricted Officer (Terhad)",
    "OWNER": "Policy Owner",
    "ADMIN": "Admin",
}
SCHEME_EN = {
    "Pembantu Tadbir": "Administrative Assistant",
    "Pegawai Tadbir": "Administrative Officer",
    "Pegawai Tadbir dan Diplomatik": "Administrative and Diplomatic Officer",
    "Pegawai Teknologi Maklumat": "IT Officer",
}
# Columns of results.json rows that the Evaluation screen shows (answers are long; keep them).
ROW_FIELDS = (
    "id", "mode", "type", "language", "user_profile", "question", "expected_doc", "expected_clause",
    "must_not_cite", "answerable", "should_refuse", "expected_rank", "in_top5", "reciprocal_rank",
    "primary_citation", "citations", "citation_ok", "stale_as_current", "excluded", "keywords_ok",
    "leak", "correct_current", "confidence", "primary_status", "latency_ms", "failure", "answer",
)


def iso(value) -> str:
    """date -> 'YYYY-MM-DD'; None/'' -> ''."""
    if value is None or value == "":
        return ""
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def initials(name: str) -> str:
    """'Pegawai Persekutuan (Terbuka)' -> 'PP'; 'Admin' -> 'AD'."""
    words = [w for w in name.replace("(", " ").replace(")", " ").split() if w[0].isalpha()]
    words = [w for w in words if w.lower() not in ("binti", "bin", "anak", "a/l", "a/p")]
    if len(words) >= 2:
        return (words[0][0] + words[1][0]).upper()
    return (words[0][:2] if words else "??").upper()


def export_documents(store: Store) -> list[dict]:
    docs = []
    for doc in store.docs.values():
        data = asdict(doc)
        for key in ("issue_date", "effective_date", "expiry_date"):
            data[key] = iso(data[key])
        data["pages"] = [
            {"page_no": p.page_no, "heading": p.heading, "text": p.text} for p in store.pages.get(doc.doc_id, [])
        ]
        data["chunks"] = [
            {
                "chunk_id": c.chunk_id,
                "chunk_index": c.chunk_index,
                "page_no": c.page_start,
                "page_end": c.page_end,
                "heading": c.section,
                "clause_ref": c.clause_ref,
                "breadcrumb": c.breadcrumb,
                "text": c.text,
            }
            for c in store.chunks_by_doc.get(doc.doc_id, [])
        ]
        docs.append(data)
    return docs


def export_relations(store: Store) -> list[dict]:
    out = []
    for rel in store.relations:
        if rel.rejected:
            continue
        data = asdict(rel)
        data["effective_date"] = iso(rel.effective_date)
        out.append(data)
    return out


def export_users(store: Store) -> list[dict]:
    out = []
    for user in store.users.values():
        data = asdict(user)
        data["initials"] = initials(user.name)
        data["name_en"] = USER_NAMES_EN.get(user.user_id, user.name)
        data["scheme_en"] = SCHEME_EN.get(user.scheme, user.scheme)
        data["clearance_label"] = CLASSIFICATION_LABELS.get(user.clearance_level, ("?", "?"))[0]
        out.append(data)
    return out


def export_golden() -> list[dict]:
    rows = []
    for row in evaluate.load_golden():
        rows.append({k: row[k] for k in evaluate.GOLDEN_COLUMNS} | {
            "must_not": [list(pair) for pair in row["must_not"]],
            "keywords": row["keywords"],
            "should_refuse": row["should_refuse"],
        })
    return rows


def export_eval() -> dict:
    """Precomputed Baseline vs Navigator numbers from eval/results/results.json."""
    try:
        result = json.loads(RESULTS_JSON.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        result = {}
    base, nav = result.get("baseline") or {}, result.get("navigator") or {}
    fv = evaluate.format_value
    headline_en = headline_ms = ""
    if base and nav:
        headline_en = (
            "On trap questions about cancelled or replaced rules, the baseline presented a stale circular as "
            f"current in {fv('cancelled_citation_rate', base.get('cancelled_citation_rate'))} of cases "
            f"({base.get('cancelled_citations', 0)}/{base.get('trap_n', 0)}); MixUp Navigator in "
            f"{fv('cancelled_citation_rate', nav.get('cancelled_citation_rate'))} "
            f"({nav.get('cancelled_citations', 0)}/{nav.get('trap_n', 0)}). Correct and current answers: "
            f"baseline {base.get('correct_current', 0)}/{base.get('n', 0)}, Navigator "
            f"{nav.get('correct_current', 0)}/{nav.get('n', 0)}. Access leaks: baseline {base.get('access_leaks', 0)}, "
            f"Navigator {nav.get('access_leaks', 0)}."
        )
        headline_ms = (
            "Bagi soalan perangkap tentang peraturan yang dibatalkan atau digantikan, chatbot biasa memaparkan "
            f"pekeliling lapuk sebagai semasa dalam {fv('cancelled_citation_rate', base.get('cancelled_citation_rate'))} "
            f"kes ({base.get('cancelled_citations', 0)}/{base.get('trap_n', 0)}); MixUp Navigator dalam "
            f"{fv('cancelled_citation_rate', nav.get('cancelled_citation_rate'))} "
            f"({nav.get('cancelled_citations', 0)}/{nav.get('trap_n', 0)}). Jawapan betul dan semasa: "
            f"chatbot biasa {base.get('correct_current', 0)}/{base.get('n', 0)}, Navigator "
            f"{nav.get('correct_current', 0)}/{nav.get('n', 0)}. Kebocoran akses: chatbot biasa "
            f"{base.get('access_leaks', 0)}, Navigator {nav.get('access_leaks', 0)}."
        )
    return {
        "meta": result.get("meta", {}),
        "baseline": base,
        "navigator": nav,
        "by_type": result.get("by_type", {}),
        "rows": [{k: r.get(k, "") for k in ROW_FIELDS} for r in result.get("rows", [])],
        "table_ms": evaluate.comparison_table(result, "ms") if result else [],
        "table_en": evaluate.comparison_table(result, "en") if result else [],
        "metrics": {k: list(v) for k, v in evaluate.METRICS.items()},  # key -> [label_ms, label_en, target, kind]
        "headline_ms": headline_ms,
        "headline_en": headline_en,
    }


def build_payload(today: date) -> dict:
    with tempfile.TemporaryDirectory(prefix="mixup-export-") as tmp:
        settings = load_settings().with_changes(today=today, runtime_dir=Path(tmp), llm_provider="offline")
        store = Store(settings)
        if store.load_errors:
            print("warning: load errors:", store.load_errors, file=sys.stderr)
        payload = {
            "generated_at": date.today().isoformat(),
            "today": today.isoformat(),
            "documents": export_documents(store),
            "relations": export_relations(store),
            "users": export_users(store),
            "glossary": [[ms, en] for en, ms in store.glossary],
            "golden": export_golden(),
            "eval": export_eval(),
            "upload_demo": {
                "filename": UPLOAD_DEMO.name,
                "text": UPLOAD_DEMO.read_text(encoding="utf-8") if UPLOAD_DEMO.exists() else "",
            },
        }
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--today", default=DEFAULT_TODAY.isoformat(), help="status date (YYYY-MM-DD)")
    args = parser.parse_args()
    today = date.fromisoformat(args.today)
    payload = build_payload(today)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=1)
    # "</script>" inside document text would end the <script> tag that loads data.js inline;
    # data.js is loaded as a file, but escape anyway to be safe.
    text = text.replace("</", "<\\/")
    args.out.write_text(
        "// Generated by scripts/export_web_data.py - do not edit by hand.\n"
        "// SINTETIK - CONTOH SAHAJA / SYNTHETIC - SAMPLE ONLY: every document here is fictional.\n"
        f"window.MX_DATA = {text};\n",
        encoding="utf-8",
    )
    n_docs = len(payload["documents"])
    n_chunks = sum(len(d["chunks"]) for d in payload["documents"])
    print(f"wrote {args.out} ({args.out.stat().st_size / 1024:.1f} KB): {n_docs} documents, {n_chunks} chunks, "
          f"{len(payload['relations'])} relations, {len(payload['users'])} users, {len(payload['glossary'])} glossary pairs, "
          f"{len(payload['golden'])} golden questions, today={payload['today']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
