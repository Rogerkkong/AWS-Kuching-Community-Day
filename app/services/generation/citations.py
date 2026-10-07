"""Citation validation (rule 5) and ACTIONS parsing for the "Apa perlu saya buat?" box."""
from __future__ import annotations

import re

GROUP_RE = re.compile(r"\[\s*S\s*\d+(?:\s*[,;]\s*S?\s*\d+)+\s*\]", re.I)  # [S1, S3] -> [S1][S3]
CITE_RE = re.compile(r"\[\s*S\s*(\d+)\s*\]", re.I)
TRAILING_RE = re.compile(r"((?:\s*\[S\d+\])+)\s*[.;:!?]*\s*$")


def normalize(text: str) -> str:
    def split(m: re.Match) -> str:
        nums = re.findall(r"\d+", m.group(0))
        return "".join(f"[S{n}]" for n in nums)
    text = GROUP_RE.sub(split, text)
    return CITE_RE.sub(lambda m: f"[S{int(m.group(1))}]", text)


def validate_answer(text: str, valid_ids: set[int]) -> tuple[str, list[int], list[int]]:
    """Remove citations not present in the context. Returns (clean text, used ids, removed ids)."""
    text = normalize(text)
    used, removed = [], []

    def repl(m: re.Match) -> str:
        n = int(m.group(1))
        if n in valid_ids:
            if n not in used:
                used.append(n)
            return f"[S{n}]"
        removed.append(n)
        return ""

    clean = CITE_RE.sub(repl, text)
    clean = re.sub(r"[ \t]+([.,;:])", r"\1", clean)
    clean = re.sub(r"[ \t]{2,}", " ", clean).strip()
    return clean, used, removed


def parse_actions(text: str, valid_ids: set[int], max_lines: int = 5) -> list[dict]:
    """Keep "- " lines that END with at least one valid citation; drop the rest."""
    out = []
    for raw in text.splitlines():
        line = raw.strip()
        if not re.match(r"^[-*•]\s+", line):
            continue
        line = re.sub(r"^[-*•]\s+", "", line)
        clean, used, _ = validate_answer(line, valid_ids)
        m = TRAILING_RE.search(clean)
        if not m or not used:
            continue
        ending = [int(n) for n in re.findall(r"\[S(\d+)\]", m.group(1))]
        if not any(n in valid_ids for n in ending):
            continue
        body = clean[: m.start()].strip().rstrip(".;,")
        if not body:
            continue
        out.append({"text": body, "citations": ending, "rendered": f"{body} {''.join(f'[S{n}]' for n in ending)}"})
        if len(out) >= max_lines:
            break
    return out


def has_valid_citation(text: str, valid_ids: set[int]) -> bool:
    return any(int(n) in valid_ids for n in CITE_RE.findall(normalize(text)))
