"""Query rewriting: QUERY_REWRITE prompt (Malay + English keyword queries, refs, jurisdiction hint,
topic, wants_history) plus glossary expansion. Falls back to the raw query + glossary on any error."""
from __future__ import annotations

import concurrent.futures
import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path

from app.services.generation import prompts
from app.services.ingest.relations import refs_in_query

STOPWORDS = {
    "yang", "dan", "untuk", "saya", "di", "ke", "dari", "ini", "itu", "adalah", "ada", "apa", "apakah", "berapa",
    "bagaimana", "boleh", "bolehkah", "bagi", "dengan", "pada", "atau", "kah", "tak", "tidak", "nak", "mahu",
    "perlu", "buat", "tentang", "mana", "masih", "sahaja", "jika", "kalau", "kita", "kami", "anda", "dia", "lagi",
    "the", "a", "an", "of", "to", "is", "in", "for", "and", "what", "how", "can", "i", "my", "me", "does", "do", "are",
    "be", "it", "on", "with", "many", "much", "still", "should", "which", "who", "when", "there", "any", "this", "that",
    "if", "or", "am", "was", "will", "would", "about", "under",
}
HISTORY_RE = re.compile(r"\b(dahulu|terdahulu|sebelum ini|(?:peraturan|pekeliling|kadar|had|versi) lama|dibatalkan|sejarah|previous|older|old (?:rule|circular|rate|limit|version)s?|cancelled|history|historical)\b", re.I)
SARAWAK_RE = re.compile(r"\b(sarawak|negeri sarawak|perkhidmatan awam negeri|state service)\b", re.I)
FEDERAL_RE = re.compile(r"\b(persekutuan|federal)\b", re.I)
WORD_RE = re.compile(r"[\w/]+", re.U)


def fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


@dataclass
class RewrittenQuery:
    question: str
    queries_ms: list[str] = field(default_factory=list)
    queries_en: list[str] = field(default_factory=list)
    circular_refs: list[str] = field(default_factory=list)
    jurisdiction_hint: str | None = None
    topic: str = ""
    wants_history: bool = False
    expansions: list[str] = field(default_factory=list)
    source: str = "fallback"

    def keyword_terms(self, limit: int = 24) -> list[str]:
        text = " ".join([self.question, *self.queries_ms, *self.queries_en, *self.expansions])
        terms = []
        for w in WORD_RE.findall(fold(text)):
            w = w.strip("/")
            if len(w) < 2 or w in STOPWORDS or "/" in w:
                continue
            terms.append(w)
        return list(dict.fromkeys(terms))[:limit]

    def fts_query(self) -> str:
        return " OR ".join(f'"{t}"' for t in self.keyword_terms())

    def embedding_text(self) -> str:
        extra = " ".join(dict.fromkeys(self.queries_ms + self.queries_en))
        return f"{self.question}\n{extra}".strip()

    def rerank_text(self) -> str:
        return " ".join([self.question, *self.queries_ms, *self.expansions])

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


@lru_cache(maxsize=4)
def load_glossary(path: str) -> dict[str, list[str]]:
    p = Path(path)
    if not p.exists():
        return {}
    data = json.loads(p.read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_") and isinstance(v, list)}


def glossary_expand(question: str, glossary: dict[str, list[str]]) -> list[str]:
    q = f" {fold(question)} "
    out: list[str] = []
    for key, values in glossary.items():
        terms = [key, *values]
        if any(re.search(rf"(?<![\w]){re.escape(fold(t))}(?![\w])", q) for t in terms):
            out += [t for t in terms if fold(t) not in q]
    return list(dict.fromkeys(out))


def fallback(question: str) -> RewrittenQuery:
    hint = "SARAWAK" if SARAWAK_RE.search(question) else ("FEDERAL" if FEDERAL_RE.search(question) else None)
    words = [w for w in WORD_RE.findall(fold(question)) if w not in STOPWORDS and len(w) > 1]
    return RewrittenQuery(question=question, queries_ms=[" ".join(words[:5])] if words else [],
                          jurisdiction_hint=hint, topic=" ".join(words[:3]),
                          wants_history=bool(HISTORY_RE.search(question)), source="fallback")


def _llm_rewrite(question: str, user: dict, client) -> RewrittenQuery:
    from app.services.inference.client import parse_json_loose

    reply = client.chat([{"role": "user", "content": prompts.QUERY_REWRITE.format(
        question=question, jurisdiction=user.get("jurisdiction"), grade=user.get("grade"), scheme=user.get("scheme"))}],
        json_mode=True, max_tokens=220)
    data = parse_json_loose(reply)
    if not isinstance(data, dict):
        raise ValueError("rewrite JSON is not an object")

    def strs(key: str) -> list[str]:
        v = data.get(key) or []
        return [s.strip() for s in v if isinstance(s, str) and s.strip()][:3] if isinstance(v, list) else []

    hint = data.get("jurisdiction_hint")
    hint = hint if hint in ("FEDERAL", "SARAWAK") else None
    return RewrittenQuery(question=question, queries_ms=strs("queries_ms"), queries_en=strs("queries_en"),
                          circular_refs=strs("circular_refs"), jurisdiction_hint=hint,
                          topic=str(data.get("topic") or "")[:60], wants_history=bool(data.get("wants_history")),
                          source="llm")


_pool = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="rewrite")


def rewrite(question: str, user: dict, client, settings, use_llm: bool | None = None) -> RewrittenQuery:
    use_llm = settings.query_rewrite_mode == "llm" if use_llm is None else use_llm
    rq = fallback(question)
    if use_llm and client is not None:
        future = _pool.submit(_llm_rewrite, question, user, client)
        try:
            rq = future.result(timeout=settings.query_rewrite_timeout)
        except Exception:  # noqa: BLE001 - timeout, model busy or bad JSON -> fallback
            rq = fallback(question)
    # Deterministic parts always apply: regex refs, history words, jurisdiction words, glossary.
    refs = [re.sub(r"\s+", " ", r.upper()) for r in rq.circular_refs] + refs_in_query(question)
    rq.circular_refs = list(dict.fromkeys(refs))
    rq.wants_history = rq.wants_history or bool(HISTORY_RE.search(question))
    if rq.jurisdiction_hint is None:
        rq.jurisdiction_hint = fallback(question).jurisdiction_hint
    glossary = load_glossary(str(settings.ground_truth_dir / "glossary.json"))
    rq.expansions = glossary_expand(" ".join([question, *rq.queries_ms, *rq.queries_en]), glossary)
    rq.expansions += [lf for lf in (long_form(r) for r in rq.circular_refs) if lf]
    return rq


LONG_SERIES = {"PP": "Pekeliling Perkhidmatan", "SPP": "Surat Pekeliling Perkhidmatan", "PAS": "Pekeliling Am Sarawak",
               "PB": "Pekeliling Perbendaharaan", "SE": "Surat Edaran"}


def long_form(ref: str) -> str | None:
    """"PP 3/2018" -> "Pekeliling Perkhidmatan Bilangan 3 Tahun 2018" (how circulars cite each other)."""
    m = re.match(r"^([A-Z]+)\s+(\d+)/(\d{4})$", ref.strip())
    if not m or m.group(1) not in LONG_SERIES:
        return None
    return f"{LONG_SERIES[m.group(1)]} Bilangan {m.group(2)} Tahun {m.group(3)}"
