"""AC-2: text inside protected regions is copied byte for byte."""

import pytest

import mathfence
from mathfence import regions, rules

# (name, text) - every $ and \( inside must survive unchanged.
VERBATIM = [
    ("fence-backtick", "```\necho $5 \\(x\\)\n```"),
    ("fence-tilde", "~~~sh\nprice=$5\n~~~"),
    ("fence-long-closer", "````\n``` $5\n````"),
    ("fence-in-list", "- item\n  ```\n  echo $5\n  ```"),
    ("fence-in-quote", "> ```\n> echo $5 \\[x\\]\n> ```"),
    ("fence-unclosed", "text\n\n```py\nx = '$5'\ny = '\\(z\\)'"),
    ("indented-code", "Para\n\n    cost = $5 + $6\n    \\(x\\)\n\nafter"),
    ("tab-code", "Para\n\n\tcost = $5 + $6\n\nafter"),
    ("code-span", "Use `echo $5` here"),
    ("code-span-double", "Use ``a ` $5 ` b`` here"),
    ("autolink", "See <https://example.com/?a=$5&b=$6> now"),
    ("bare-url", "See https://example.com/p?x=$5&y=\\(z\\) now"),
    ("html-block", "<div class=\"a\">\ncost $5 \\(x\\)\n</div>"),
    ("html-comment", "<!-- $5 \\(x\\) -->"),
    ("html-script", "<script>\nvar a = '$5';\n</script>"),
    ("html-tag-attribute", "<a href=\"/p?x=$5\" title=\"$6\">link</a>"),
]


@pytest.mark.parametrize(("name", "text"), VERBATIM, ids=[v[0] for v in VERBATIM])
def test_protected_text_is_unchanged(name, text):
    assert mathfence.normalize(text) == text


@pytest.mark.parametrize(("name", "text"), VERBATIM, ids=[v[0] for v in VERBATIM])
def test_protected_text_is_unchanged_in_streamlit_profile(name, text):
    assert mathfence.normalize(text, profile="streamlit") == text


def test_text_around_protected_regions_is_still_normalized():
    out = mathfence.normalize("cost $5 and `$6` and $7 and \\(x\\)")
    assert out == "cost \\$5 and `$6` and \\$7 and $x$"


def test_indented_line_after_a_paragraph_is_not_code():
    # A 4-space line right after a paragraph line continues the paragraph.
    assert mathfence.normalize("text\n    pay $5") == "text\n    pay \\$5"


def test_indented_line_in_a_list_is_not_code():
    src = "1. item\n\n    pay $5 now"
    assert mathfence.normalize(src) == "1. item\n\n    pay \\$5 now"


def test_scan_reports_kind_and_rule():
    text = "a `b` <https://x.y> https://z.w/q\n\n```\nc\n```\n"
    found = [(r.kind, r.rule) for r in regions.scan(text).regions]
    assert found == [
        ("code", rules.CODE_SPAN),
        ("url", rules.AUTOLINK),
        ("url", rules.BARE_URL),
        ("code", rules.CODE_FENCE),
    ]


def test_url_trailing_punctuation_is_not_part_of_the_url():
    text = "see https://example.com/a. Then $5."
    out = mathfence.normalize(text)
    assert out == "see https://example.com/a. Then \\$5."


def test_backtick_fence_info_with_backtick_is_not_a_fence():
    # ```x``` on one line is an inline code span, not a fence opener.
    assert mathfence.normalize("```x $5```\npay $6") == "```x $5```\npay \\$6"


def test_boundaries_skip_open_fences_and_lists():
    text = "para\n\n```\ncode\n\nmore\n```\n\nnext\n"
    cuts = regions.scan(text).boundaries
    assert cuts == (6, len(text) - len("next\n"))
    # no cut inside a list, but one after the list has ended
    assert regions.scan("- a\n\n  b\n\nc\n\nd").boundaries == (len("- a\n\n  b\n\nc\n\n"),)


def test_unclosed_inline_code_is_held_back_only_while_streaming():
    text = "pay $5 `code $x"
    assert mathfence.normalize(text) == "pay \\$5 `code \\$x"
    streamed = mathfence.analyze(text).text
    assert streamed == "pay \\$5 `code \\$x"
