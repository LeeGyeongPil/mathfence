"""AC-3: bracket delimiters become dollars, prefixes survive."""

import pytest

import mathfence


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("Euler: \\(e^{i\\pi}+1=0\\) holds.", "Euler: $e^{i\\pi}+1=0$ holds."),
        ("a \\( x + y \\) b", "a $x + y$ b"),
        ("\\[x^2\\]", "$$\nx^2\n$$"),
        ("Area:\n\n\\[\n\\int_0^1 x\\,dx\n\\]\n\nDone.", "Area:\n\n$$\n\\int_0^1 x\\,dx\n$$\n\nDone."),
        ("1. First:\n   \\[\n   a^2+b^2=c^2\n   \\]\n2. Next", "1. First:\n   $$\n   a^2+b^2=c^2\n   $$\n2. Next"),
        ("> \\[\n> a+b\n> \\]", "> $$\n> a+b\n> $$"),
        ("> > \\(a+b\\)\n> > text", "> > $a+b$\n> > text"),
        ("- item\n  \\[\n  z=1\n  \\]\n- next", "- item\n  $$\n  z=1\n  $$\n- next"),
    ],
)
def test_brackets_become_dollars(src, expected):
    assert mathfence.normalize(src) == expected


def test_inline_bracket_containing_dollar_becomes_double():
    assert mathfence.normalize("Cost \\(c = \\$5\\) per item") == "Cost $$c = \\$5$$ per item"


def test_inline_bracket_before_a_digit_uses_double_dollars():
    # $x$5 would read as a price; $$x$$5 cannot.
    assert mathfence.normalize("Final: \\(x\\)5") == "Final: $$x$$5"


def test_escaped_backslash_before_paren_is_not_a_delimiter():
    src = "Literal \\\\(not math\\\\) here."
    assert mathfence.normalize(src) == src


def test_three_backslashes_leave_a_real_delimiter():
    # `\\` is an escaped backslash, so the following `\(` still opens math.
    assert mathfence.normalize("a \\\\\\(x\\)") == "a \\\\$x$"


def test_unclosed_bracket_is_left_alone():
    assert mathfence.normalize("open \\(x + y and more") == "open \\(x + y and more"


def test_bracket_does_not_span_a_paragraph_break():
    src = "start \\(x\n\nend y\\)"
    assert mathfence.normalize(src) == src


def test_ambiguous_bracket_bodies_are_left_alone():
    # No safe $-form: a digit-led display body would be read as prices.
    assert mathfence.normalize("\\[5\\]") == "\\[5\\]"
    assert mathfence.normalize("\\(5 big apples\\)") == "\\(5 big apples\\)"


def test_empty_brackets_are_left_alone():
    assert mathfence.normalize("a \\( \\) b") == "a \\( \\) b"


def test_decisions_report_conversions():
    result = mathfence.analyze("a \\(x\\) b")
    assert [(d.action, d.rule) for d in result.decisions] == [("convert", "bracket-inline")]
    assert (result.decisions[0].line, result.decisions[0].column) == (1, 3)
