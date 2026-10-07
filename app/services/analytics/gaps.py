"""Publisher dashboard aggregates over imported usage reports."""
from __future__ import annotations

import json
from collections import Counter, defaultdict


def dashboard(conn) -> dict:
    queries = []
    reports = 0
    for (payload,) in conn.execute("SELECT payload_json FROM usage_reports"):
        reports += 1
        try:
            queries += json.loads(payload).get("queries", [])
        except ValueError:
            continue
    by_cluster: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    unanswered, low, topics, excluded = Counter(), [], Counter(), Counter()
    for q in queries:
        cluster = q.get("cluster") or "lain-lain"
        by_cluster[cluster][0] += 1
        if not q.get("answerable"):
            by_cluster[cluster][1] += 1
            unanswered[q.get("query", "").strip()] += 1
        elif q.get("confidence") == "LOW":
            low.append(q.get("query"))
        if q.get("topic"):
            topics[q["topic"]] += 1
        for no in q.get("excluded_circulars") or []:
            excluded[no] += 1
    total = len(queries)
    return {
        "reports": reports, "queries": total,
        "unanswered_rate": round(sum(v[1] for v in by_cluster.values()) / total, 3) if total else 0.0,
        "by_cluster": [{"cluster": c, "queries": v[0], "unanswered": v[1], "rate": round(v[1] / v[0], 3) if v[0] else 0}
                       for c, v in sorted(by_cluster.items(), key=lambda kv: -kv[1][0])],
        "top_unanswered": [{"query": q, "count": n} for q, n in unanswered.most_common(10)],
        "low_confidence": [q for q in low[:10]],
        "top_topics": [{"topic": t, "count": n} for t, n in topics.most_common(10)],
        "excluded_circulars": [{"circular_no": c, "count": n} for c, n in excluded.most_common(10)],
    }
