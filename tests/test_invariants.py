"""AC-4 (part 2): properties that must hold for any input (1,000 seeded random texts)."""

import re

import pytest

import mathfence
from fuzzgen import random_texts
from mathfence import regions

TEXTS = random_texts(1000)
UNESCAPED_DOLLAR = re.compile(r"(?<!\\)\$")


def test_generator_is_seeded_and_large_enough():
    assert len(TEXTS) == 1000
    assert TEXTS == random_texts(1000)
    assert len(set(TEXTS)) > 900


@pytest.mark.parametrize("profile", mathfence.PROFILES)
def test_idempotent(profile):
    for text in TEXTS:
        once = mathfence.normalize(text, profile=profile)
        assert mathfence.normalize(once, profile=profile) == once, repr(text)


def test_protected_regions_survive_unchanged():
    for text in TEXTS:
        out = mathfence.normalize(text)
        for region in regions.scan(text).regions:
            piece = text[region.start : region.end]
            assert piece in out, (text, piece)


def test_input_without_math_markers_is_returned_as_is():
    plain = [t for t in TEXTS if "$" not in t and "\\(" not in t and "\\[" not in t]
    assert len(plain) > 20
    for text in plain:
        assert mathfence.normalize(text) == text


def test_accepted_inline_math_never_contains_a_bare_dollar():
    for text in TEXTS:
        for d in mathfence.analyze(text).decisions:
            if d.action == "keep_math" and d.kind == "inline" and len(d.source) < 120:
                body = d.source[1:-1]
                for region in reversed(regions.scan(body).regions):  # dollars inside code or URLs are protected
                    body = body[: region.start] + body[region.end :]
                assert not UNESCAPED_DOLLAR.search(body), (text, d.source)


def test_decision_positions_point_at_their_source():
    for text in TEXTS:
        for d in mathfence.analyze(text).decisions:
            if d.rule.startswith("bracket-") or d.action == "protect":
                assert text.startswith(d.source[:20].rstrip("\u2026"), d.offset), (text, d)
            lines = text.split("\n")
            assert 1 <= d.line <= len(lines)
            assert 1 <= d.column <= len(lines[d.line - 1]) + 1
