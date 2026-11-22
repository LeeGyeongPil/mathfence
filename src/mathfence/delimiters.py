"""Rewrite ``\\( … \\)`` and ``\\[ … \\]`` into ``$ … $`` and ``$$ … $$``.

Only text outside protected regions is touched.  The delimiters are replaced
in place, so list indentation and ``>`` quote prefixes on continuation lines
survive untouched.  Brackets that cannot be converted safely are left as is.
"""

from __future__ import annotations

import re
from typing import NamedTuple

from . import rules
from .regions import PARA, Region
from .rules import Raw

_OPEN = re.compile(r"\\[(\[]")


class Edit(NamedTuple):
    """One replacement: ``text[orig_start:orig_end]`` became ``mid[mid_start:mid_end]``."""

    orig_start: int
    orig_end: int
    mid_start: int
    mid_end: int


class Converted(NamedTuple):
    text: str
    edits: list[Edit]
    raws: list[Raw]  # offsets are in the *original* text
    display_starts: set[int]  # mid offsets of converted ``$$`` pairs


def _odd_backslashes_before(text: str, idx: int) -> bool:
    n = 0
    k = idx - 1
    while k >= 0 and text[k] == "\\":
        n += 1
        k -= 1
    return n % 2 == 1


def _find_closer(text: str, start: int, limit: int, char: str) -> int:
    pat = "\\" + char
    k = start
    while True:
        k = text.find(pat, k, limit)
        if k == -1:
            return -1
        if not _odd_backslashes_before(text, k):
            return k
        k += 1


def _segments(text: str, regions: tuple[Region, ...]) -> list[tuple[int, int]]:
    segs: list[tuple[int, int]] = []
    cursor = 0
    for r in regions:
        if cursor < r.start:
            segs.append((cursor, r.start))
        cursor = max(cursor, r.end)
    if cursor < len(text):
        segs.append((cursor, len(text)))
    return segs


def convert(text: str, regions: tuple[Region, ...], *, streaming: bool = False) -> Converted:
    """Convert bracket delimiters outside ``regions``.

    With ``streaming=True`` a closing bracket that touches the end of the text
    is not converted yet: the next character may change how it must be written.
    """
    out: list[str] = []
    edits: list[Edit] = []
    raws: list[Raw] = []
    display_starts: set[int] = set()
    last = 0
    mid_len = 0
    for seg_start, seg_end in _segments(text, regions):
        pos = seg_start
        while True:
            m = _OPEN.search(text, pos, seg_end)
            if not m:
                break
            if _odd_backslashes_before(text, m.start()):
                pos = m.start() + 1
                continue
            display = text[m.start() + 1] == "["
            para = PARA.search(text, m.end(), seg_end)
            limit = para.start() if para else seg_end
            k = _find_closer(text, m.end(), limit, "]" if display else ")")
            if k == -1 or (streaming and k + 2 == len(text)):
                pos = m.end()
                continue
            end = k + 2
            raw_body = text[m.end() : k]
            source = text[m.start() : end]
            after = text[end] if end < len(text) else ""
            replacement, kind, rule = _rewrite(raw_body, after, display)
            pos = end
            if replacement is None:
                if raw_body.strip():
                    raws.append(Raw(m.start(), source, "protect", "stray", rules.BRACKET_AMBIGUOUS))
                continue
            out.append(text[last : m.start()])
            mid_len += m.start() - last
            if display:
                display_starts.add(mid_len)
            out.append(replacement)
            edits.append(Edit(m.start(), end, mid_len, mid_len + len(replacement)))
            mid_len += len(replacement)
            last = end
            raws.append(Raw(m.start(), source, "convert", kind, rule))
    out.append(text[last:])
    return Converted("".join(out), edits, raws, display_starts)


def _rewrite(raw_body: str, after: str, display: bool) -> tuple[str | None, str, str]:
    """Return ``(replacement, kind, rule)``; ``replacement`` is ``None`` to leave the brackets."""
    body = raw_body.strip()
    if not body:
        return None, "stray", rules.BRACKET_AMBIGUOUS
    if display:
        if "$$" in body or rules.judge_double(body) is not None:
            return None, "display", rules.BRACKET_AMBIGUOUS
        inner = raw_body if "\n" in raw_body else body
        return "$$" + inner + "$$", "display", rules.BRACKET_DISPLAY
    double_ok = "$$" not in body and rules.judge_double(body) is None
    if "$" in body:
        if double_ok:
            return "$$" + body + "$$", "inline", rules.BRACKET_HAS_DOLLAR
        return None, "inline", rules.BRACKET_AMBIGUOUS
    if rules.judge_single(body, after) is None:
        return "$" + body + "$", "inline", rules.BRACKET_INLINE
    if double_ok:
        return "$$" + body + "$$", "inline", rules.BRACKET_INLINE_DOUBLE
    return None, "inline", rules.BRACKET_AMBIGUOUS


def _last_edit_index(edits: list[Edit], mid_offset: int) -> int:
    """Number of edits starting at or before ``mid_offset`` (binary search)."""
    lo, hi = 0, len(edits)
    while lo < hi:
        half = (lo + hi) // 2
        if edits[half].mid_start <= mid_offset:
            lo = half + 1
        else:
            hi = half
    return lo


def inside_edit(edits: list[Edit], mid_offset: int) -> bool:
    """True if ``mid_offset`` falls inside a converted piece."""
    lo = _last_edit_index(edits, mid_offset)
    return lo > 0 and mid_offset < edits[lo - 1].mid_end


def to_original(edits: list[Edit], mid_offset: int) -> int:
    """Map an offset in the converted text back to the original text."""
    lo = _last_edit_index(edits, mid_offset)
    if lo == 0:
        return mid_offset
    e = edits[lo - 1]
    if mid_offset >= e.mid_end:
        return e.orig_end + (mid_offset - e.mid_end)
    return e.orig_start
