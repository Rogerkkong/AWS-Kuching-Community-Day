"""Reset the demo: delete data/runtime/ (uploads, pending relations, alerts, logs, caches).

Usage:  python scripts/reset_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mixup.store import Store  # noqa: E402


def main() -> None:
    store = Store()
    store.reset_runtime()
    print(f"Runtime cleared: {store.runtime_dir}")
    print(f"Loaded {len(store.docs)} documents, {len(store.chunks)} chunks, {len(store.relations)} relations.")
    for doc in store.docs.values():
        print(f"  {doc.label:14} {doc.status:10} {doc.status_reason}")


if __name__ == "__main__":
    main()
