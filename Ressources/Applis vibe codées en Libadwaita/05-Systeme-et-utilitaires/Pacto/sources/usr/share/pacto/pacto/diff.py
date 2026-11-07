"""Line alignment and intra-line highlighting for the side by side view."""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field

EQUAL = "equal"
DELETE = "delete"
INSERT = "insert"
REPLACE = "replace"
SKIP = "skip"

CONTEXT_LINES = 3
COLLAPSE_THRESHOLD = 2 * CONTEXT_LINES + 3

_WORD_RE = re.compile(r"\w+|\s+|[^\w\s]")


@dataclass
class Row:
    """One visual line of the diff, holding both sides."""

    kind: str
    left_no: int | None = None
    left_text: str = ""
    right_no: int | None = None
    right_text: str = ""
    left_spans: list[tuple[int, int]] = field(default_factory=list)
    right_spans: list[tuple[int, int]] = field(default_factory=list)
    skipped: int = 0


@dataclass
class DiffStats:
    deletions: int = 0
    insertions: int = 0
    changes: int = 0

    @property
    def total(self) -> int:
        return self.deletions + self.insertions + self.changes


def _word_spans(old: str, new: str) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """Return the byte-agnostic character ranges that differ inside two lines."""
    a, b = _WORD_RE.findall(old), _WORD_RE.findall(new)
    offsets_a, offsets_b = _offsets(a), _offsets(b)
    left: list[tuple[int, int]] = []
    right: list[tuple[int, int]] = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag in (DELETE, REPLACE) and i1 != i2:
            left.append((offsets_a[i1], offsets_a[i2]))
        if tag in (INSERT, REPLACE) and j1 != j2:
            right.append((offsets_b[j1], offsets_b[j2]))
    return left, right


def _offsets(tokens: list[str]) -> list[int]:
    offsets = [0]
    for token in tokens:
        offsets.append(offsets[-1] + len(token))
    return offsets


def build_rows(old: list[str], new: list[str], collapse: bool = False) -> tuple[list[Row], DiffStats]:
    """Align both files line by line, padding each side so rows stay in sync."""
    rows: list[Row] = []
    stats = DiffStats()
    matcher = difflib.SequenceMatcher(None, old, new, autojunk=False)
    opcodes = matcher.get_opcodes()

    for index, (tag, i1, i2, j1, j2) in enumerate(opcodes):
        if tag == EQUAL:
            block = [
                Row(EQUAL, i + 1, old[i], j + 1, new[j])
                for i, j in zip(range(i1, i2), range(j1, j2))
            ]
            if collapse and len(block) >= COLLAPSE_THRESHOLD:
                head = [] if index == 0 else block[:CONTEXT_LINES]
                tail = [] if index == len(opcodes) - 1 else block[-CONTEXT_LINES:]
                hidden = len(block) - len(head) - len(tail)
                rows.extend(head)
                rows.append(Row(SKIP, skipped=hidden))
                rows.extend(tail)
            else:
                rows.extend(block)
        elif tag == DELETE:
            stats.deletions += i2 - i1
            rows.extend(Row(DELETE, i + 1, old[i]) for i in range(i1, i2))
        elif tag == INSERT:
            stats.insertions += j2 - j1
            rows.extend(Row(INSERT, right_no=j + 1, right_text=new[j]) for j in range(j1, j2))
        else:
            paired = min(i2 - i1, j2 - j1)
            stats.changes += paired
            stats.deletions += max(0, (i2 - i1) - paired)
            stats.insertions += max(0, (j2 - j1) - paired)
            for offset in range(max(i2 - i1, j2 - j1)):
                i, j = i1 + offset, j1 + offset
                if i < i2 and j < j2:
                    left_spans, right_spans = _word_spans(old[i], new[j])
                    rows.append(
                        Row(REPLACE, i + 1, old[i], j + 1, new[j], left_spans, right_spans)
                    )
                elif i < i2:
                    rows.append(Row(DELETE, i + 1, old[i]))
                else:
                    rows.append(Row(INSERT, right_no=j + 1, right_text=new[j]))
    return rows, stats
