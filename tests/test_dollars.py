"""AC-4 (part 1): currency vs math decisions."""

import pytest

import mathfence

CASES = [
    # currency: every $ escaped
    ("It costs $5 and $10.", "It costs \\$5 and \\$10."),
    ("From $5 to $10 is a $5 increase.", "From \\$5 to \\$10 is a \\$5 increase."),
    ("Budget: $100-$200 range.", "Budget: \\$100-\\$200 range."),
    ("Total: $5+$3=$8 overall.", "Total: \\$5+\\$3=\\$8 overall."),
    ("Between $5 and$10 exactly.", "Between \\$5 and\\$10 exactly."),
    ("It is 5$ or 10$ in some locales.", "It is 5\\$ or 10\\$ in some locales."),
    ("Spend $5 on the x$ token.", "Spend \\$5 on the x\\$ token."),
    ("- Basic: $9\n- Pro: $19\n- Team: $49", "- Basic: \\$9\n- Pro: \\$19\n- Team: \\$49"),
    ("| a | $5 |\n| b | $6 |", "| a | \\$5 |\n| b | \\$6 |"),
    ("$5", "\\$5"),
    # math: kept
    ("We know $5x = 10$, so x is 2.", "We know $5x = 10$, so x is 2."),
    ("About $10^6$ users.", "About $10^6$ users."),
    ("The roots are $1$ and $2$.", "The roots are $1$ and $2$."),
    ("Let $\\alpha$ be the rate.", "Let $\\alpha$ be the rate."),
    ("The sum $\\sum_{i=1}^n i$ equals $n(n+1)/2$.", "The sum $\\sum_{i=1}^n i$ equals $n(n+1)/2$."),
    ("Absolute value $|x|$ here.", "Absolute value $|x|$ here."),
    ("We have $\\text{if } x > 0$ then.", "We have $\\text{if } x > 0$ then."),
    # mixed
    ("Pay $5 if $x>5$ holds.", "Pay \\$5 if $x>5$ holds."),
    ("The cost $C$ is $100 per unit.", "The cost $C$ is \\$100 per unit."),
    ("$a$ costs $5 and $b$ costs $6.", "$a$ costs \\$5 and $b$ costs \\$6."),
    ("Cheap at $5 vs. $x$ dollars.", "Cheap at \\$5 vs. $x$ dollars."),
    ("It costs $5, and $x$ is the count.", "It costs \\$5, and $x$ is the count."),
    # double dollars
    ("Pay $$5 or $$10 tip.", "Pay \\$\\$5 or \\$\\$10 tip."),
    ("Then $$x^2+y^2$$ follows.", "Then $$x^2+y^2$$ follows."),
    ("Run $$$ now", "Run \\$\\$\\$ now"),
    # already escaped
    ("Already escaped \\$5 and \\$10.", "Already escaped \\$5 and \\$10."),
    ("Cost \\$5 but $x$ is math.", "Cost \\$5 but $x$ is math."),
    # Korean and mixed scripts
    ("가격은 $5에서 $10으로 올랐다.", "가격은 \\$5에서 \\$10으로 올랐다."),
    ("$x$와 $y$의 합은 $x+y$이다.", "$x$와 $y$의 합은 $x+y$이다."),
    ("사과는 $3이고 배는 $4인데, 합은 $a+b$이다.", "사과는 \\$3이고 배는 \\$4인데, 합은 $a+b$이다."),
    ("가격은 $5이고 수식은 $x^2$ 이다.", "가격은 \\$5이고 수식은 $x^2$ 이다."),
    # pairs never cross a paragraph or a block boundary
    ("Costs $5\n\nand $6 later", "Costs \\$5\n\nand \\$6 later"),
    ("Costs $5\nand $x$ next line.", "Costs \\$5\nand $x$ next line."),
]


@pytest.mark.parametrize(("src", "expected"), CASES, ids=[c[0][:40] for c in CASES])
def test_decision_table(src, expected):
    assert mathfence.normalize(src) == expected


def test_no_dollar_means_identity():
    text = "plain text with `code`, a #hash and a back\\slash"
    assert mathfence.normalize(text) == text
    assert mathfence.normalize("") == ""


def test_decisions_name_the_rule():
    result = mathfence.analyze("It costs $5 and $x$.")
    got = [(d.action, d.kind, d.rule) for d in result.decisions]
    assert got == [
        ("escape", "currency", "body-edge-space"),
        ("keep_math", "inline", "math-pair"),
    ]
    first = result.decisions[0]
    assert (first.line, first.column, first.offset, first.source) == (1, 10, 9, "$")
    assert result.changed


def test_unchanged_input_is_reported_as_unchanged():
    result = mathfence.analyze("Solve $x^2$ now.")
    assert not result.changed
    assert result.text == "Solve $x^2$ now."


def test_decision_source_is_clipped():
    long_body = "x" * 500
    result = mathfence.analyze("```\n$" + long_body + "\n```")
    assert all(len(d.source) <= 120 for d in result.decisions)
    assert result.decisions[0].action == "protect"
