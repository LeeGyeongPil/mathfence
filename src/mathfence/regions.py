"""Find the regions of a Markdown text that must be copied byte for byte.

Protected regions are fenced code, indented code, code spans, HTML blocks,
inline HTML tags, autolinks and bare URLs.  Everything is a plain line/regex
scan (no full CommonMark parser), tuned to be *conservative*: when unsure the
text is left alone.
"""

from __future__ import annotations

import re
from bisect import bisect_right
from dataclasses import dataclass

from . import rules

# A paragraph break: a blank line, or a line holding only quote markers.
PARA = re.compile(r"\n[ \t>\r]*\n")

_LIST_MARK = re.compile(r"^ {0,3}(?:[-*+]|\d{1,9}[.)])(?:[ \t]|$)")
_FENCE = re.compile(
    r"^(?P<prefix>(?:[ \t]*>)*[ \t]*(?:(?:[-*+]|\d{1,9}[.)])[ \t]+)*)"
    r"(?P<fence>`{3,}|~{3,})(?P<info>.*)$"
)
_BLOCK_TAGS = (
    "address|article|aside|base|basefont|blockquote|body|caption|center|col|colgroup|dd|"
    "details|dialog|dir|div|dl|dt|fieldset|figcaption|figure|footer|form|frame|frameset|"
    "h1|h2|h3|h4|h5|h6|head|header|hr|html|iframe|legend|li|link|main|menu|menuitem|nav|"
    "noframes|ol|optgroup|option|p|param|section|source|summary|table|tbody|td|tfoot|th|"
    "thead|title|tr|track|ul"
)
_HTML_START = re.compile(
    r"^ {0,3}(?:(?P<raw><(?P<rawname>pre|script|style|textarea)(?:[ \t>]|$))"
    r"|(?P<comment><!--)|(?P<pi><\?)|(?P<decl><![A-Za-z])|(?P<cdata><!\[CDATA\[)"
    r"|</?(?:" + _BLOCK_TAGS + r")(?:[ \t]|/?>|$))",
    re.IGNORECASE,
)
_AUTOLINK = re.compile(r"<[A-Za-z][A-Za-z0-9+.-]{1,31}:[^\s<>]*>")
_URL = re.compile(r"(?<![\w/])(?:https?|ftp)://[^\s<>]+")
_HTML_TAG = re.compile(
    r"</?[A-Za-z][A-Za-z0-9-]*"
    r"(?:[ \t\r\n]+[A-Za-z_:][\w.:-]*(?:[ \t\r\n]*=[ \t\r\n]*(?:[^\s\"'=<>`]+|'[^']*'|\"[^\"]*\"))?)*"
    r"[ \t\r\n]*/?>"
)


@dataclass(frozen=True)
class Region:
    """A half-open ``[start, end)`` slice that is copied unchanged."""

    start: int
    end: int
    kind: str  # "code" | "url" | "html"
    rule: str  # one of the rule ids in :mod:`mathfence.rules`


@dataclass(frozen=True)
class Scan:
    """Result of :func:`scan`."""

    regions: tuple[Region, ...]
    #: Offsets that start a line right after a blank line, outside every block
    #: construct. Text can be split there without changing the result.
    boundaries: tuple[int, ...]


class RegionIndex:
    """Fast "which region contains offset i" lookups over sorted regions."""

    def __init__(self, regions: tuple[Region, ...]) -> None:
        self.regions = regions
        self._starts = [r.start for r in regions]

    def at(self, i: int) -> Region | None:
        k = bisect_right(self._starts, i) - 1
        if k >= 0 and self.regions[k].end > i:
            return self.regions[k]
        return None


def _leading_spaces(prefix: str) -> int:
    return len(prefix) - len(prefix.lstrip(" "))


def _scan_blocks(text: str) -> tuple[list[Region], list[int]]:
    lines = text.split("\n")
    starts: list[int] = []
    pos = 0
    for ln in lines:
        starts.append(pos)
        pos += len(ln) + 1
    n = len(lines)
    regions: list[Region] = []
    boundaries: list[int] = []
    i = 0
    prev_blank = True
    list_active = False
    while i < n:
        line = lines[i]
        # --- fenced code (also inside quotes and list items) ---
        m = _FENCE.match(line)
        if m:
            prefix, fence, info = m.group("prefix"), m.group("fence"), m.group("info")
            has_container = ">" in prefix or bool(prefix.strip())
            plain_indent = not has_container and _leading_spaces(prefix) >= 4 and not list_active
            if not plain_indent and not (fence[0] == "`" and "`" in info):
                j = i + 1
                end = len(text)
                while j < n:
                    stripped = re.sub(r"^[ \t>]*", "", lines[j]).strip()
                    if len(stripped) >= len(fence) and set(stripped) == {fence[0]}:
                        end = starts[j] + len(lines[j])
                        break
                    j += 1
                regions.append(Region(starts[i], end, "code", rules.CODE_FENCE))
                i = j + 1
                prev_blank = True
                if re.search(r"[-*+]|\d[.)]", prefix.replace(">", "")) and prefix.strip(" >\t"):
                    list_active = True
                elif _leading_spaces(prefix) < 2:
                    list_active = False
                continue
        # --- blank line ---
        if not line.strip():
            if not list_active and starts[i] + len(line) + 1 <= len(text):
                boundaries.append(starts[i] + len(line) + 1)
            prev_blank = True
            i += 1
            continue
        # --- HTML block (top level only) ---
        hm = _HTML_START.match(line) if not line.lstrip().startswith(">") else None
        if hm and not line.startswith("    "):
            j = i
            if hm.group("raw"):
                closer = "</" + hm.group("rawname").lower() + ">"
                while j < n and closer not in lines[j].lower():
                    j += 1
            elif hm.group("comment"):
                while j < n and "-->" not in lines[j]:
                    j += 1
            elif hm.group("pi"):
                while j < n and "?>" not in lines[j]:
                    j += 1
            elif hm.group("cdata"):
                while j < n and "]]>" not in lines[j]:
                    j += 1
            elif hm.group("decl"):
                while j < n and ">" not in lines[j]:
                    j += 1
            else:
                while j + 1 < n and lines[j + 1].strip():
                    j += 1
            j = min(j, n - 1)
            regions.append(Region(starts[i], starts[j] + len(lines[j]), "html", rules.HTML_BLOCK))
            i = j + 1
            prev_blank = False
            continue
        # --- indented code ---
        if prev_blank and not list_active and (line.startswith("    ") or line.startswith("\t")):
            j = i
            k = i + 1
            while k < n:
                if lines[k].startswith("    ") or lines[k].startswith("\t"):
                    j = k
                elif lines[k].strip():
                    break
                k += 1
            regions.append(Region(starts[i], starts[j] + len(lines[j]), "code", rules.INDENTED_CODE))
            i = j + 1
            prev_blank = False
            continue
        # --- ordinary line: track list context ---
        # A top-level list item that starts a new block can settle everything
        # before it, but only when no math marker (``$`` or a backslash) could
        # pair across the cut; otherwise full-document results could differ.
        if i > 0 and _LIST_MARK.match(line) and not line[0].isspace():
            seg_from = boundaries[-1] if boundaries else 0
            segment = text[seg_from : starts[i]]
            if "$" not in segment and "\\" not in segment and segment.strip():
                boundaries.append(starts[i])
        if _LIST_MARK.match(line):
            list_active = True
        elif prev_blank and _leading_spaces(line) < 2 and not line.startswith("\t"):
            list_active = False
        prev_blank = False
        i += 1
    return regions, boundaries


def _inline_regions(text: str, lo: int, hi: int, streaming: bool) -> list[Region]:
    found: list[Region] = []
    k = lo
    while k < hi:
        c = text[k]
        if c == "\\":
            k += 2
            continue
        if c != "`":
            k += 1
            continue
        n = 1
        while k + n < hi and text[k + n] == "`":
            n += 1
        closer = re.compile(r"(?<!`)" + "`" * n + r"(?!`)").search(text, k + n, hi)
        if closer and not PARA.search(text, k, closer.start()):
            found.append(Region(k, closer.end(), "code", rules.CODE_SPAN))
            k = closer.end()
            continue
        if streaming and hi == len(text) and not PARA.search(text, k, hi):
            # Still-open span at the end of a stream: hold it back unchanged.
            found.append(Region(k, hi, "code", rules.STREAM_PENDING))
            break
        k += n
    for m in _AUTOLINK.finditer(text, lo, hi):
        found.append(Region(m.start(), m.end(), "url", rules.AUTOLINK))
    for m in _URL.finditer(text, lo, hi):
        end = m.end()
        while end > m.start() and text[end - 1] in ".,;:!?'\"*_~":
            end -= 1
        while end > m.start() and text[end - 1] in ")]" and (
            text.count(text[end - 1], m.start(), end) > text.count("(" if text[end - 1] == ")" else "[", m.start(), end)
        ):
            end -= 1
        if end > m.start() + 8:
            found.append(Region(m.start(), end, "url", rules.BARE_URL))
    for m in _HTML_TAG.finditer(text, lo, hi):
        if not PARA.search(m.group(0)):
            found.append(Region(m.start(), m.end(), "html", rules.HTML_TAG))
    return found


def _merge(regions: list[Region]) -> tuple[Region, ...]:
    merged: list[Region] = []
    for r in sorted(regions, key=lambda r: (r.start, -r.end)):
        if merged and r.start < merged[-1].end:
            last = merged[-1]
            if r.end > last.end:
                merged[-1] = Region(last.start, r.end, last.kind, last.rule)
        else:
            merged.append(r)
    return tuple(merged)


def scan(text: str, *, streaming: bool = False) -> Scan:
    """Find protected regions and safe split points in ``text``.

    With ``streaming=True`` an unclosed inline code span at the very end is
    also protected (it is probably about to be closed).
    """
    blocks, boundaries = _scan_blocks(text)
    blocks.sort(key=lambda r: r.start)
    found: list[Region] = list(blocks)
    cursor = 0
    for b in blocks:
        if cursor < b.start:
            found.extend(_inline_regions(text, cursor, b.start, streaming))
        cursor = max(cursor, b.end)
    if cursor < len(text):
        found.extend(_inline_regions(text, cursor, len(text), streaming))
    merged = _merge(found)
    safe = tuple(
        b for b in boundaries if not any(r.start < b <= r.end and r.rule != rules.STREAM_PENDING for r in merged)
    )
    return Scan(merged, safe)
