"""Rule ids and the "does this body look like math?" judgement.

Every decision mathfence makes carries one of the ids below, so the CLI
(``--explain``) can say *why* a ``$`` was kept or escaped.
"""

from __future__ import annotations

import re
from typing import NamedTuple

# --- decisions about `$` ---
MATH_PAIR = "math-pair"
CLOSE_FOLLOWED_BY_DIGIT = "close-followed-by-digit"
CLOSE_FOLLOWED_BY_DOLLAR = "close-followed-by-dollar"
BODY_EMPTY = "body-empty"
BODY_EDGE_SPACE = "body-edge-space"
BODY_WORDS = "body-words"
BODY_ENDS_OPERATOR = "body-ends-operator"
BODY_BLOCK_BOUNDARY = "body-block-boundary"
NO_CLOSING = "no-closing"
DOUBLE_CURRENCY = "double-currency"
DOLLAR_RUN = "dollar-run"
STREAM_PENDING = "stream-pending"
DISPLAY_OWN_LINE = "display-own-line"

# --- decisions about `\(` and `\[` ---
BRACKET_INLINE = "bracket-inline"
BRACKET_INLINE_DOUBLE = "bracket-inline-double"
BRACKET_DISPLAY = "bracket-display"
BRACKET_HAS_DOLLAR = "bracket-has-dollar"
BRACKET_AMBIGUOUS = "bracket-ambiguous"

# --- protected regions ---
CODE_FENCE = "code-fence"
CODE_SPAN = "code-span"
INDENTED_CODE = "indented-code"
AUTOLINK = "autolink"
BARE_URL = "bare-url"
HTML_BLOCK = "html-block"
HTML_TAG = "html-tag"

ALL_RULES: tuple[str, ...] = (
    MATH_PAIR,
    CLOSE_FOLLOWED_BY_DIGIT,
    CLOSE_FOLLOWED_BY_DOLLAR,
    BODY_EMPTY,
    BODY_EDGE_SPACE,
    BODY_WORDS,
    BODY_ENDS_OPERATOR,
    BODY_BLOCK_BOUNDARY,
    NO_CLOSING,
    DOUBLE_CURRENCY,
    DOLLAR_RUN,
    STREAM_PENDING,
    DISPLAY_OWN_LINE,
    BRACKET_INLINE,
    BRACKET_INLINE_DOUBLE,
    BRACKET_DISPLAY,
    BRACKET_HAS_DOLLAR,
    BRACKET_AMBIGUOUS,
    CODE_FENCE,
    CODE_SPAN,
    INDENTED_CODE,
    AUTOLINK,
    BARE_URL,
    HTML_BLOCK,
    HTML_TAG,
)

# Characters or commands that only appear in formulas.
_TEX = re.compile(r"\\[A-Za-z]+|[\^_{}=<>+]|\\\\")
# Two consecutive words of 2+ letters (English, accented Latin, Hangul).
_WORDS = re.compile(r"[A-Za-z\u00c0-\u024f\uac00-\ud7a3]{2,}[ \t]+[A-Za-z\u00c0-\u024f\uac00-\ud7a3]{2,}")
# A newline followed by something that starts a new Markdown block.
_BLOCK_START = re.compile(r"\n[ \t]*(?:[-*+][ \t]|\d{1,9}[.)][ \t]|>|#|\|)")
_OPERATORS = "+-*/=,.;:"


def has_tex(body: str) -> bool:
    """True if ``body`` contains a TeX command or a formula-only character."""
    return _TEX.search(body) is not None


def judge_single(body: str, after: str) -> str | None:
    """Judge the body of a single-``$`` pair.

    ``body`` is the text between the dollars, ``after`` the character that
    follows the closing dollar (``""`` at the end of the text).  Returns
    ``None`` when the pair is math, otherwise the id of the failing rule.
    """
    if not body.strip():
        return BODY_EMPTY
    if body[0].isspace() or body[-1].isspace():
        return BODY_EDGE_SPACE
    if _BLOCK_START.search(body):
        return BODY_BLOCK_BOUNDARY
    if body[-1] in _OPERATORS:
        return BODY_ENDS_OPERATOR
    if "\\" not in body and _WORDS.search(body):
        return BODY_WORDS
    if after[:1].isdigit():
        return CLOSE_FOLLOWED_BY_DIGIT
    return None


def judge_double(body: str) -> str | None:
    """Judge the body of a ``$$ … $$`` pair (``None`` means math)."""
    if not body.strip():
        return BODY_EMPTY
    if body.lstrip()[0].isdigit() and not has_tex(body):
        return DOUBLE_CURRENCY
    return None


class Raw(NamedTuple):
    """A decision before line/column are resolved (offset is in the text it was made on)."""

    offset: int
    source: str
    action: str
    kind: str
    rule: str
