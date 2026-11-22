"""Public entry points: :func:`normalize` and :func:`analyze`."""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass, field
from typing import Literal

from . import delimiters, dollars, regions
from . import rules
from .rules import Raw

PROFILES: tuple[str, ...] = ("remark", "streamlit")

Action = Literal["keep_math", "convert", "escape", "protect"]
Kind = Literal["inline", "display", "currency", "stray", "code", "url", "html"]

_SOURCE_LIMIT = 120


@dataclass(frozen=True)
class Decision:
    """One thing mathfence decided, with the rule that decided it.

    ``offset``, ``line`` (1-based) and ``column`` (1-based, in characters) point
    into the *input* text.  ``source`` is the original fragment, clipped to
    120 characters.
    """

    offset: int
    line: int
    column: int
    source: str
    action: Action
    kind: Kind
    rule: str


@dataclass(frozen=True)
class Result:
    """What :func:`analyze` returns."""

    text: str
    decisions: list[Decision] = field(default_factory=list)
    changed: bool = False


def check_input(text: object, profile: str) -> None:
    """Raise ``TypeError`` / ``ValueError`` for bad arguments."""
    if not isinstance(text, str):
        hint = " (decode bytes with .decode('utf-8') first)" if isinstance(text, (bytes, bytearray)) else ""
        raise TypeError(f"text must be str, got {type(text).__name__}{hint}")
    if profile not in PROFILES:
        raise ValueError(f"unknown profile {profile!r}; choose one of: {', '.join(PROFILES)}")


def _clip(s: str) -> str:
    return s if len(s) <= _SOURCE_LIMIT else s[: _SOURCE_LIMIT - 1] + "…"


def run(text: str, profile: str, streaming: bool = False) -> Result:
    """Normalize ``text`` (arguments already validated).

    Decisions describe the first pass.  A second pass runs over a changed text
    until it stops changing (at most three more), which makes the result
    idempotent even when a rewrite exposes new structure to the scanner.
    """
    first = _single_pass(text, profile, streaming)
    if streaming or not first.changed:
        return first
    out = first.text
    for _ in range(3):
        again = _single_pass(out, profile, False).text
        if again == out:
            break
        out = again
    return Result(out, first.decisions, out != text)


def _single_pass(text: str, profile: str, streaming: bool) -> Result:
    if "$" not in text and "\\(" not in text and "\\[" not in text:
        return Result(text, [], False)
    first = regions.scan(text, streaming=streaming)
    conv = delimiters.convert(text, first.regions, streaming=streaming)
    if conv.edits:
        mid = conv.text
        second = regions.scan(mid, streaming=streaming)
    else:
        mid, second = text, first
    out, dollar_raws = dollars.process(
        mid, second.regions, profile=profile, streaming=streaming, display_hints=conv.display_starts
    )

    raws: list[Raw] = []
    for r in first.regions:
        if r.rule == rules.STREAM_PENDING:
            continue  # reported by the dollar pass
        piece = text[r.start : r.end]
        if "$" in piece or "\\(" in piece or "\\[" in piece:
            raws.append(Raw(r.start, piece, "protect", r.kind, r.rule))
    raws.extend(conv.raws)
    for r in dollar_raws:
        if r.action == "keep_math" and delimiters.inside_edit(conv.edits, r.offset):
            continue  # already reported as a "convert" decision
        raws.append(r._replace(offset=delimiters.to_original(conv.edits, r.offset)))
    raws.sort(key=lambda r: r.offset)

    newlines = [i for i, c in enumerate(text) if c == "\n"]
    decisions: list[Decision] = []
    for r in raws:
        k = bisect_right(newlines, r.offset - 1)
        line_start = newlines[k - 1] + 1 if k else 0
        decisions.append(
            Decision(
                offset=r.offset,
                line=k + 1,
                column=r.offset - line_start + 1,
                source=_clip(r.source),
                action=r.action,  # type: ignore[arg-type]
                kind=r.kind,  # type: ignore[arg-type]
                rule=r.rule,
            )
        )
    return Result(out, decisions, out != text)


def analyze(text: str, *, profile: str = "remark") -> Result:
    """Normalize ``text`` and report every decision.

    Args:
        text: Markdown as produced by an LLM.
        profile: ``"remark"`` (default; any renderer reading ``$``/``$$``) or
            ``"streamlit"`` (block math on its own lines).

    Raises:
        TypeError: ``text`` is not a ``str``.
        ValueError: ``profile`` is not one of :data:`PROFILES`.
    """
    check_input(text, profile)
    return run(text, profile)


def normalize(text: str, *, profile: str = "remark") -> str:
    """Return ``text`` ready for a Markdown renderer that reads ``$`` math.

    Code, URLs and HTML are copied unchanged; ``\\( \\)`` and ``\\[ \\]`` become
    ``$ $`` and ``$$ $$``; every ``$`` that is not math becomes ``\\$``.
    """
    check_input(text, profile)
    return run(text, profile).text
