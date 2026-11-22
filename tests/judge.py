"""The judge: which math nodes does a lenient Markdown parser find in a text?

markdown-it-py + dollarmath is configured as *permissively* as possible
(single ``$`` with spaces and digits, inline ``$$``).  A ``$`` that is not
math but still gets parsed as math therefore shows up as a false positive.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from markdown_it import MarkdownIt
from mdit_py_plugins.dollarmath import dollarmath_plugin

CORPUS_DIR = Path(__file__).parent / "corpus"
_MATH_TYPES = {"math_inline", "math_inline_double", "math_block", "math_block_label"}

_md = (
    MarkdownIt("commonmark")
    .enable("table")
    .use(dollarmath_plugin, allow_space=True, allow_digits=True, double_inline=True)
)


def math_values(text: str) -> list[str]:
    """Stripped contents of every math node in ``text`` (document order)."""
    values: list[str] = []

    def walk(tokens: list[Any]) -> None:
        for tok in tokens:
            if tok.type in _MATH_TYPES:
                values.append(tok.content.strip())
            if tok.children:
                walk(tok.children)

    walk(_md.parse(text))
    return values


def same_math(got: list[str], expected: list[str]) -> bool:
    """True if both lists hold the same values (order does not matter)."""
    return Counter(got) == Counter(e.strip() for e in expected)


def load_cases() -> list[dict[str, Any]]:
    return json.loads((CORPUS_DIR / "cases.json").read_text(encoding="utf-8"))["cases"]


def load_streams() -> dict[str, Any]:
    return json.loads((CORPUS_DIR / "streams.json").read_text(encoding="utf-8"))


def build_long_answer(spec: dict[str, Any]) -> str:
    """Repeat a paragraph until the answer has ``target_chars`` characters."""
    para: str = spec["paragraph"]
    count = -(-int(spec["target_chars"]) // len(para))
    return para * count
