"""Decide, for every ``$`` outside protected regions, whether it is math or text.

A single ``$`` is paired with the next ``$`` of the same paragraph; the text
between them must look like a formula (see :mod:`mathfence.rules`).  Anything
that is not math is escaped as ``\\$`` so no renderer can mistake it for math.
"""

from __future__ import annotations

import re

from . import rules
from .regions import PARA, Region, RegionIndex
from .rules import Raw

_JUMP = re.compile(r"[\\$]")
_PREFIX = re.compile(r"^((?:[ \t]*>)*)([ \t]*)((?:(?:[-*+]|\d{1,9}[.)])[ \t]+)*)")
_ONLY_PREFIX = re.compile(r"[ \t>\r]*")


def _currency_kind(text: str, after: int) -> str:
    return "currency" if text[after : after + 1].isdigit() else "stray"


class _Pass:
    def __init__(
        self,
        text: str,
        regions: tuple[Region, ...],
        profile: str,
        streaming: bool,
        display_hints: set[int],
    ) -> None:
        self.text = text
        self.n = len(text)
        self.idx = RegionIndex(regions)
        self.profile = profile
        self.streaming = streaming
        self.display_hints = display_hints
        self.out: list[str] = []
        self.raws: list[Raw] = []
        self._pe_from = 0
        self._pe = -1

    # -- helpers ---------------------------------------------------------
    def para_end(self, i: int) -> int:
        """Offset where the paragraph containing ``i`` ends."""
        if not (self._pe_from <= i <= self._pe):
            m = PARA.search(self.text, i)
            self._pe_from = i
            self._pe = m.start() if m else self.n
        return self._pe

    def next_dollar(self, j: int, limit: int) -> int:
        """Next unescaped ``$`` in ``[j, limit)`` that is outside every region, or -1."""
        text = self.text
        while True:
            m = _JUMP.search(text, j, limit)
            if not m:
                return -1
            p = m.start()
            r = self.idx.at(p)
            if r:
                j = r.end
                continue
            if text[p] == "\\":
                j = p + 2
                continue
            return p

    def run_at(self, p: int) -> int:
        run = 1
        while p + run < self.n and self.text[p + run] == "$":
            run += 1
        return run

    def escape(self, p: int, run: int, rule: str) -> int:
        self.out.append("\\$" * run)
        self.raws.append(Raw(p, "$" * run, "escape", _currency_kind(self.text, p + run), rule))
        return p + run

    # -- main loop -------------------------------------------------------
    def run(self) -> tuple[str, list[Raw]]:
        text, i = self.text, 0
        while True:
            m = _JUMP.search(text, i)
            if not m:
                self.out.append(text[i:])
                break
            p = m.start()
            r = self.idx.at(p)
            if r:
                self.out.append(text[i : r.end])
                if r.rule == rules.STREAM_PENDING:
                    self.hold_pending(r, i)
                i = r.end
                continue
            self.out.append(text[i:p])
            if text[p] == "\\":
                self.out.append(text[p : p + 2])
                i = p + 2
                continue
            run = self.run_at(p)
            if run >= 3:
                i = self.escape(p, run, rules.DOLLAR_RUN)
            elif run == 2:
                i = self.double(p)
            else:
                i = self.single(p)
        return "".join(self.out), self.raws

    def hold_pending(self, r: Region, copied_from: int) -> None:
        """An unclosed code span at the end of a stream: show its ``$`` as text for now.

        The region was just copied; replace that copy with an escaped one so the
        renderer cannot pair these dollars into math that the finished answer
        (where the span is code) will not have.
        """
        text = self.text
        piece = text[max(copied_from, r.start) : r.end]
        head = text[copied_from : r.start] if copied_from < r.start else ""
        del self.out[-1]
        escaped = re.sub(r"(?<!\\)\$", lambda m: "\\$", piece)
        self.out.append(head + escaped)
        if escaped != piece:
            self.raws.append(Raw(r.start, text[r.start : r.end], "escape", "stray", rules.STREAM_PENDING))

    # -- single dollar ---------------------------------------------------
    def single(self, p: int) -> int:
        text = self.text
        j = self.next_dollar(p + 1, self.para_end(p))
        if j == -1:
            return self.escape(p, 1, rules.NO_CLOSING)
        if self.streaming and j + 1 == self.n:
            return self.escape(p, 1, rules.STREAM_PENDING)
        if self.run_at(j) >= 2:
            return self.escape(p, 1, rules.CLOSE_FOLLOWED_BY_DOLLAR)
        fail = rules.judge_single(text[p + 1 : j], text[j + 1 : j + 2])
        if fail:
            return self.escape(p, 1, fail)
        self.out.append(text[p : j + 1])
        self.raws.append(Raw(p, text[p : j + 1], "keep_math", "inline", rules.MATH_PAIR))
        return j + 1

    # -- double dollar ---------------------------------------------------
    def double(self, p: int) -> int:
        text = self.text
        limit = self.para_end(p)
        j = p + 2
        close = -1
        while True:
            j = self.next_dollar(j, limit)
            if j == -1:
                break
            rj = self.run_at(j)
            if rj == 1:
                j += 1
                continue
            if rj == 2:
                close = j
            break
        if close == -1:
            return self.escape(p, 2, rules.NO_CLOSING)
        if self.streaming and close + 2 == self.n:
            return self.escape(p, 2, rules.STREAM_PENDING)
        fail = rules.judge_double(text[p + 2 : close])
        if fail:
            return self.escape(p, 2, fail)
        self.raws.append(Raw(p, text[p : close + 2], "keep_math", "display", rules.MATH_PAIR))
        if self.profile == "streamlit" or p in self.display_hints:
            laid_out = self.layout(p, close, own_line_only=self.profile != "streamlit")
            if laid_out is not None:
                return laid_out
        self.out.append(text[p : close + 2])
        return close + 2

    def layout(self, p: int, close: int, own_line_only: bool = False) -> int | None:
        """Put a display pair on its own lines, keeping ``>`` and list prefixes.

        Returns the offset to continue from, or ``None`` if the pair already
        sits on its own lines (or lives in a table or heading).
        """
        text = self.text
        line_start = text.rfind("\n", 0, p) + 1
        lead = text[line_start:p]
        pm = _PREFIX.match(lead)
        assert pm is not None
        quote, spaces, marker = pm.group(1), pm.group(2), pm.group(3)
        content = lead[pm.end() :]
        if content.lstrip().startswith(("|", "#")):
            return None
        if own_line_only and (content.strip() or text[close + 2 : close + 3].strip()):
            return None
        cont = quote + spaces + " " * len(marker)
        blank = cont.rstrip()
        body = text[p + 2 : close]
        eol = text.find("\n", close + 2)
        rest = text[close + 2 : eol if eol != -1 else self.n]
        lines = body.split("\n")
        opener_alone = len(lines) > 1 and not lines[0].strip()
        closer_alone = len(lines) > 1 and _ONLY_PREFIX.fullmatch(lines[-1]) is not None
        if not content.strip() and not rest.strip() and opener_alone and closer_alone:
            return None
        if opener_alone:
            core_lines, has_prefix = lines[1:], True
        else:
            lines[0] = lines[0].lstrip(" \t")
            core_lines, has_prefix = lines, False
        while core_lines and _ONLY_PREFIX.fullmatch(core_lines[-1]):
            core_lines.pop()
        core = "\n".join(core_lines).rstrip(" \t\r")
        if not core.strip():
            return None
        for line in core_lines:
            # A line that would start an HTML block or a fence inside the new
            # layout would swallow the closing $$: keep the pair as it is.
            if re.sub(r"^[ \t>]*", "", line).startswith(("<", "```", "~~~")):
                return None
        if not has_prefix:
            core = cont + core
        if content.strip():
            self.out = ["".join(self.out).rstrip(" \t")]
            self.out.append("\n" + blank + "\n" + cont)
        self.out.append("$$\n" + core + "\n" + cont + "$$")
        end = close + 2
        if rest.strip():
            self.out.append("\n" + blank + "\n" + cont)
            end += len(rest) - len(rest.lstrip(" \t"))
        self.raws.append(Raw(p, text[p : close + 2], "convert", "display", rules.DISPLAY_OWN_LINE))
        return end


def process(
    text: str,
    regions: tuple[Region, ...],
    *,
    profile: str,
    streaming: bool = False,
    display_hints: set[int] | None = None,
) -> tuple[str, list[Raw]]:
    """Run the ``$`` decisions over ``text``; offsets in the result refer to ``text``."""
    return _Pass(text, regions, profile, streaming, display_hints or set()).run()
