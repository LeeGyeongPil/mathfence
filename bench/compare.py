"""Score mathfence and three baselines on the same corpus with the same judge.

Run from the repository root:  ``uv run python bench/compare.py``

For every corpus case the output is parsed with markdown-it-py + dollarmath
(configured as permissively as possible, see ``tests/judge.py``).  A case
passes when the math nodes equal the expected ones and every ``verbatim``
fragment (code, URLs, HTML) is still byte for byte in the output.  ``broken``
counts cases where a verbatim fragment was damaged.  ``flicker`` counts
streaming screens (one per received character) that show math the finished
answer does not contain.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "bench"))
sys.path.insert(0, str(ROOT / "src"))

import baselines  # noqa: E402
import judge  # noqa: E402

import mathfence  # noqa: E402


class Row(NamedTuple):
    name: str
    passed: int
    total: int
    broken: int
    flicker: int


def _flicker(screens: list[str], final: str) -> int:
    final_values = judge.math_values(final)
    count = 0
    for screen in screens:
        if any(not any(f.startswith(v) for f in final_values) for v in judge.math_values(screen)):
            count += 1
    return count


def evaluate(name: str, fn: Callable[[str], str], stream_fn: Callable[[str], tuple[list[str], str]]) -> Row:
    cases = judge.load_cases()
    passed = broken = 0
    for case in cases:
        out = fn(case["src"])
        intact = all(v in out for v in case["verbatim"])
        broken += not intact
        passed += intact and judge.same_math(judge.math_values(out), case["expect"])
    flicker = 0
    for sentence in judge.load_streams()["sentences"]:
        screens, final = stream_fn(sentence)
        flicker += _flicker(screens, final)
    return Row(name, passed, len(cases), broken, flicker)


def _stateless(fn: Callable[[str], str]) -> Callable[[str], tuple[list[str], str]]:
    def run(sentence: str) -> tuple[list[str], str]:
        return [fn(sentence[:k]) for k in range(1, len(sentence) + 1)], fn(sentence)

    return run


def _mathfence_stream(sentence: str) -> tuple[list[str], str]:
    sn = mathfence.StreamNormalizer()
    screens = [sn.feed(ch) for ch in sentence]
    return screens, sn.finish()


def compare() -> list[Row]:
    return [
        evaluate("no processing", baselines.raw, _stateless(baselines.raw)),
        evaluate("escape every $", baselines.escape_all, _stateless(baselines.escape_all)),
        evaluate("regex recipe", baselines.regex_recipe, _stateless(baselines.regex_recipe)),
        evaluate("mathfence", mathfence.normalize, _mathfence_stream),
    ]


def main() -> int:
    rows = compare()
    print(f"{'approach':<16} {'pass':>9} {'score':>6} {'broken':>7} {'flicker':>8}")
    for r in rows:
        print(f"{r.name:<16} {r.passed:>4}/{r.total:<4} {r.passed / r.total:>6.2f} {r.broken:>7} {r.flicker:>8}")
    print("judge: markdown-it-py + dollarmath (single $, spaces, digits and inline $$ allowed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
