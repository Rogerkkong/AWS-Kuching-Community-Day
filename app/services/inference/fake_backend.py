"""Deterministic offline stand-in for the LLM and embedding model.

Used by the test-suite and whenever no model is installed (INFERENCE_BACKEND=fake). It is NOT a
language model: embeddings are hashed bag-of-words + character trigrams, and "answers" are extractive
(the first sentence of the best passages), so the whole pipeline can be exercised without Ollama.
Packs built with it record the embedding model "fake-hash-1024" and are refused by an Ollama-backed
Officer app (rule 8).
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from typing import Iterator

from app.config import Settings
from app.services.inference.client import normalize

WORD_RE = re.compile(r"[a-z0-9]+")
STOP = {"yang", "dan", "untuk", "saya", "di", "ke", "dari", "ini", "itu", "adalah", "the", "a", "an",
        "of", "to", "is", "in", "for", "and", "what", "how", "can", "i", "my", "apa", "apakah", "berapa",
        "boleh", "bagi", "dengan", "pada", "atau", "does", "do", "are", "be", "it", "on", "with",
        "kah", "tak", "nak", "perlu", "buat", "tentang", "mana", "masih", "still"}
ACTION_HINTS = ("boleh", "bolehkah", "macam mana", "bagaimana", "apa perlu", "perlu saya", "how do i",
                "how can i", "can i", "am i allowed", "what should", "what do i", "nak mohon", "mohon",
                "what next", "langkah")


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def _stem(word: str) -> str:
    # Cheap Malay/English suffix folding so "cuti"/"cutinya", "leave"/"leaves" collide.
    for suf in ("nya", "kan", "lah", "es", "s"):
        if len(word) > len(suf) + 3 and word.endswith(suf):
            return word[: -len(suf)]
    return word


def tokens(text: str) -> list[str]:
    return [_stem(w) for w in WORD_RE.findall(_fold(text)) if w not in STOP]


def _bucket(feature: str, dim: int) -> tuple[int, float]:
    h = hashlib.blake2b(feature.encode(), digest_size=8).digest()
    idx = int.from_bytes(h[:4], "little") % dim
    sign = 1.0 if h[4] & 1 else -1.0
    return idx, sign


def hash_embed(text: str, dim: int = 1024) -> list[float]:
    vec = [0.0] * dim
    toks = tokens(text)
    for t in toks:
        i, s = _bucket("w:" + t, dim)
        vec[i] += 2.0 * s
        padded = f"#{t}#"
        for j in range(len(padded) - 2):
            i, s = _bucket("c:" + padded[j:j + 3], dim)
            vec[i] += 0.5 * s
    if not toks:
        vec[0] = 1.0
    return normalize(vec)


SENT_RE = re.compile(r"(?<=[.!?])\s+")
CTX_RE = re.compile(r"^\[S(\d+)\] (.*)$", re.M)


class FakeBackend:
    name = "fake"

    def __init__(self, settings: Settings):
        self.s = settings

    def health(self) -> dict:
        return {"backend": self.name, "reachable": True, "chat_model": "fake-extractive",
                "embed_model": "fake-hash-1024", "chat_model_present": True, "embed_model_present": True,
                "detail": "Deterministic test backend (no language model)."}

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [hash_embed(t, self.s.embed_dim) for t in texts]

    def rerank(self, query: str, documents: list[str]) -> list[float] | None:
        q = set(tokens(query))
        if not q:
            return [0.0] * len(documents)
        scores = []
        for d in documents:
            dt = set(tokens(d))
            scores.append(len(q & dt) / (len(q) + 2))
        return scores

    def warm_up(self) -> None:
        return None

    # ------------------------------------------------------------------- chat
    def chat(self, messages: list[dict], *, json_mode: bool = False, max_tokens: int | None = None,
             timeout: float | None = None) -> str:
        system = messages[0]["content"] if messages else ""
        user = messages[-1]["content"] if messages else ""
        if "You prepare search queries" in system or "You prepare search queries" in user:
            return self._rewrite(user)
        if "Extract metadata" in system or "Extract metadata" in user:
            return json.dumps({"doc_type": None, "circular_no": None, "series": None, "title": None,
                               "issuer": None, "issue_date": None, "effective_date": None,
                               "jurisdiction": None, "applicability": None, "one_off": False,
                               "language": "ms"})
        if "You classify how a Malaysian government circular" in system + user:
            return self._relations(user)
        if "You explain changes between two versions" in system + user:
            return self._change_summary(user)
        return "".join(self.chat_stream(messages, max_tokens=max_tokens))

    def chat_stream(self, messages: list[dict], *, max_tokens: int | None = None) -> Iterator[str]:
        user = messages[-1]["content"] if messages else ""
        text = self._answer(user)
        for piece in re.findall(r"\S+\s*|\n", text):
            yield piece

    def _answer(self, user: str) -> str:
        m = re.search(r"QUESTION: (.*)", user)
        question = m.group(1).strip() if m else ""
        ctx = user.split("CONTEXT:", 1)[1] if "CONTEXT:" in user else ""
        blocks = re.split(r"\n(?=\[S\d+\] )", "\n" + ctx.strip())
        passages = []
        for b in blocks:
            hm = CTX_RE.match(b.strip())
            if not hm:
                continue
            sid = int(hm.group(1))
            header = hm.group(2).split(" | ")
            body = b.strip().split("\n", 1)[1] if "\n" in b.strip() else ""
            passages.append((sid, header, body))
        q = set(tokens(question))
        scored = []
        for sid, header, body in passages:
            overlap = len(q & set(tokens(body + " " + " ".join(header[:2]))))
            scored.append((overlap, -sid, sid, header, body))
        scored.sort(reverse=True)
        if not scored or scored[0][0] < max(1, min(2, len(q) // 3)):
            return "ANSWERABLE: NO"
        lines = []
        for overlap, _, sid, header, body in scored[:2]:
            if overlap == 0:
                continue
            sentence = self._best_line(body, q)
            status = header[4] if len(header) > 4 else ""
            date = header[5] if len(header) > 5 else ""
            prefix = f"Mesyuarat pada {date}: " if status == "RECORD" else ""
            lines.append(f"{prefix}{sentence.rstrip('.')} [S{sid}].")
        out = "ANSWERABLE: YES\n" + " ".join(lines)
        if any(h in _fold(question) for h in ACTION_HINTS):
            top = scored[0][2]
            out += (f"\nACTIONS:\n- Semak syarat kelayakan dalam {scored[0][3][0]} [S{top}]\n"
                    f"- Dapatkan kelulusan pegawai yang diturunkan kuasa [S{top}]")
        return out

    @staticmethod
    def _best_line(body: str, q: set) -> str:
        """The clause line sharing most words with the question (headings skipped)."""
        best, best_score = "", -1
        for line in body.split("\n"):
            line = re.sub(r"^PERKARA \d+:.*? - (KEPUTUSAN|TINDAKAN): ", "", line.strip())
            line = re.sub(r"^(KEPUTUSAN|TINDAKAN|KEHADIRAN): ", "", line)
            if not line or line.isupper() or line.startswith("PERKARA "):
                continue
            score = len(q & set(tokens(line)))
            if score > best_score:
                best, best_score = line, score
        best = re.sub(r"^\d+(\.\d+)*\.?\s+", "", best)
        return SENT_RE.split(best)[0].strip() if len(best.split()) > 45 else best

    def _rewrite(self, user: str) -> str:
        m = re.search(r"QUESTION: (.*)", user)
        question = m.group(1).strip() if m else user
        toks = [w for w in WORD_RE.findall(_fold(question)) if w not in STOP]
        refs = [f"{a.upper()} {b}/{c}" for a, b, c in
                re.findall(r"\b(spp|pp|pas|se)\s*(?:bil\.?\s*)?(\d{1,3})\s*/\s*((?:19|20)\d{2})", _fold(question))]
        hist = any(w in _fold(question) for w in ("dahulu", "lama", "sebelum", "dibatalkan", "previous", "old", "cancelled"))
        jur = "SARAWAK" if "sarawak" in _fold(question) else ("FEDERAL" if "persekutuan" in _fold(question) or "federal" in _fold(question) else None)
        return json.dumps({"queries_ms": [" ".join(toks[:5])] if toks else [], "queries_en": [],
                           "circular_refs": refs, "jurisdiction_hint": jur,
                           "topic": " ".join(toks[:3]), "wants_history": hist})

    def _relations(self, user: str) -> str:
        m = re.search(r"CANDIDATES: (\[.*\])\s*$", user, re.S)
        cands = json.loads(m.group(1)) if m else []
        out = []
        for c in cands:
            s = _fold(c.get("sentence", ""))
            if "digantikan" in s or "menggantikan" in s or "supersede" in s or "replaces" in s:
                rel = "SUPERSEDES"
            elif "dibatalkan" in s or "dimansuhkan" in s or "tidak lagi terpakai" in s or "membatalkan" in s or "cancel" in s or "revoked" in s:
                rel = "CANCELS"
            elif "dipinda" in s or "pindaan" in s or "amend" in s:
                rel = "AMENDS"
            else:
                rel = "REFERENCES"
            out.append({"ref_text": c.get("ref_text"), "relation": rel, "scope": "whole",
                        "effective_date": None, "evidence": c.get("sentence"), "page": c.get("page"),
                        "confidence": 0.8})
        return json.dumps(out)

    def _change_summary(self, user: str) -> str:
        m = re.search(r"DIFF: (\[.*\])\s*$", user, re.S)
        diff = json.loads(m.group(1)) if m else []
        changed = [d for d in diff if d.get("type") != "UNCHANGED"]
        clauses = ", ".join(sorted({str(d.get("clause_new") or d.get("clause_old")) for d in changed})) or "-"
        return json.dumps({
            "summary_ms": f"Perenggan yang berubah: {clauses}. Rujuk perbandingan klausa untuk butiran.",
            "summary_en": f"Changed paragraphs: {clauses}. See the clause comparison for details.",
            "effective_date": None, "who_is_affected": "Tidak dinyatakan / Not stated",
            "changes": [{"clause_old": d.get("clause_old"), "clause_new": d.get("clause_new"),
                         "type": d.get("type"), "plain_change": f"Perenggan {d.get('clause_new') or d.get('clause_old')} {d.get('type', '').lower()}."}
                        for d in changed[:8]],
        })
