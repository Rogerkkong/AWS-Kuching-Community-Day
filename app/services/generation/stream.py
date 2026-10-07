"""Incremental parser for the ANSWER prompt's plain-text streaming format.

Line 1 is "ANSWERABLE: YES|NO" (read before anything is streamed); the rest is the answer, optionally
followed by "ACTIONS:" and "- " lines. The marker can arrive split across tokens, so a short tail that
could be the start of the marker is held back until it is resolved.
"""
from __future__ import annotations

import re

MARKER = "ACTIONS:"
HEAD_RE = re.compile(r"^\s*\**\s*ANSWERABLE\s*:\s*\**\s*(YES|NO)\b\**", re.I)
MARKER_RE = re.compile(r"\**\s*ACTIONS\s*:\s*\**", re.I)


class AnswerStreamParser:
    def __init__(self, head_limit: int = 60):
        self.head_limit = head_limit
        self.answerable: bool | None = None
        self.section = "answer"
        self._head = ""
        self._buf = ""
        self.answer_text = ""
        self.actions_text = ""

    def feed(self, piece: str) -> list[tuple[str, str]]:
        """Returns a list of (section, text) to emit now. section is "answer" or "actions"."""
        if self.answerable is None:
            self._head += piece
            m = HEAD_RE.match(self._head)
            if m and ("\n" in self._head[m.end():] or len(self._head) - m.end() > 3):
                self.answerable = m.group(1).upper() == "YES"
                rest = self._head[m.end():].lstrip("\n").lstrip()
                if not self.answerable:
                    return []
                return self._consume(rest)
            if not m and (len(self._head) > self.head_limit or "\n" in self._head.strip()):
                # The model ignored the format: treat the text as an answer; validation decides later.
                self.answerable = True
                return self._consume(self._head.lstrip())
            return []
        if not self.answerable:
            return []
        return self._consume(piece)

    def _consume(self, text: str) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        self._buf += text
        if self.section == "answer":
            m = MARKER_RE.search(self._buf)
            if m:
                before, after = self._buf[: m.start()], self._buf[m.end():]
                if before:
                    out.append(("answer", before))
                    self.answer_text += before
                self.section = "actions"
                self._buf = ""
                if after:
                    out += self._consume(after)
                return out
            hold = self._held_tail(self._buf)
            emit = self._buf[: len(self._buf) - hold]
            self._buf = self._buf[len(emit):]
            if emit:
                out.append(("answer", emit))
                self.answer_text += emit
            return out
        emit, self._buf = self._buf, ""
        if emit:
            out.append(("actions", emit))
            self.actions_text += emit
        return out

    @staticmethod
    def _held_tail(buf: str) -> int:
        """Length of the longest suffix that could still grow into the marker (allowing '*' and spaces)."""
        upper = buf.upper()
        for n in range(min(len(upper), len(MARKER) + 4), 0, -1):
            tail = upper[-n:].lstrip("* \n")
            if tail and MARKER.startswith(tail):
                return n
        return 0

    def finish(self) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        if self.answerable is None:
            m = HEAD_RE.match(self._head)
            if m:
                self.answerable = m.group(1).upper() == "YES"
                rest = self._head[m.end():].strip()
                if self.answerable and rest:
                    out += self._consume(rest)
            else:
                self.answerable = bool(self._head.strip())
                if self.answerable:
                    out += self._consume(self._head)
        if self._buf:
            out.append((self.section, self._buf))
            if self.section == "answer":
                self.answer_text += self._buf
            else:
                self.actions_text += self._buf
            self._buf = ""
        return out
