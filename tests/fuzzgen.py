"""Seeded random Markdown-ish inputs for property tests (no extra dependency)."""

from __future__ import annotations

import random

FRAGMENTS = [
    "$", "$", "$$", "$5", "$x$", "$10^6$", "\\(", "\\)", "\\(x\\)", "\\[", "\\]", "\\[y\\]",
    "`", "``", "```\n", "~~~\n", "\n", "\n", "\n\n", "> ", "- ", "1. ", "    ", "\t", " ", " ",
    "x", "5", "a b", " and ", "^2", "=", "+", "\\", "\\\\", "\\$", "http://a.b/$5", "<b>", "</b>",
    "<https://q.r/$>", "<div>\n", "</div>\n", "| ", "# ", "\ud55c\uae00", "\\frac{1}{2}", "$ ", " $", "$$\n", "\n$$",
]


def random_text(rng: random.Random) -> str:
    return "".join(rng.choice(FRAGMENTS) for _ in range(rng.randint(1, 40)))


def random_texts(count: int, seed: int = 20261123) -> list[str]:
    rng = random.Random(seed)
    return [random_text(rng) for _ in range(count)]
