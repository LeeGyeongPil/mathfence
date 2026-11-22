"""AC-5: streaming never flashes math that the finished answer lacks."""

import random

import judge
import pytest

import mathfence
from fuzzgen import random_texts


def _spurious_math(screens, final):
    """Screens that contain a math node which is not (a prefix of) a final math node."""
    final_values = judge.math_values(final)
    bad = 0
    for screen in screens:
        for value in judge.math_values(screen):
            if not any(f.startswith(value) for f in final_values):
                bad += 1
                break
    return bad


SENTENCES = judge.load_streams()["sentences"]


@pytest.mark.parametrize("sentence", SENTENCES, ids=[f"s{i}" for i in range(len(SENTENCES))])
def test_char_by_char_has_no_spurious_math(sentence):
    sn = mathfence.StreamNormalizer()
    screens = [sn.feed(ch) for ch in sentence]
    final = sn.finish()
    spurious_math = _spurious_math(screens, final)
    print("spurious_math", spurious_math)
    assert spurious_math == 0
    assert final == mathfence.normalize(sentence)


def test_the_unprotected_approach_does_flash_math():
    # Guards the metric: normalizing each prefix statelessly with a naive escape would not be zero.
    sentence = "Between $5 and$10 exactly."
    screens = [sentence[:k] for k in range(1, len(sentence) + 1)]
    assert _spurious_math(screens, mathfence.normalize(sentence)) > 0


def test_closing_dollar_at_the_end_is_held_back():
    sn = mathfence.StreamNormalizer()
    assert sn.feed("Pay $5 if $") == "Pay \\$5 if \\$"
    assert sn.feed("x") == "Pay \\$5 if \\$x"
    assert sn.feed("$") == "Pay \\$5 if \\$x\\$"  # may still be followed by a digit
    assert sn.feed(" ok") == "Pay \\$5 if $x$ ok"


def test_closing_dollar_followed_by_a_digit_never_becomes_math():
    sn = mathfence.StreamNormalizer()
    screens = [sn.feed(c) for c in "Between $5 and$10 exactly."]
    assert all(judge.math_values(s) == [] for s in screens)
    assert sn.finish() == "Between \\$5 and\\$10 exactly."


def test_open_fence_stays_verbatim_while_streaming():
    sn = mathfence.StreamNormalizer()
    assert sn.feed("Run:\n\n```bash\necho $PATH\nprice=$5") == "Run:\n\n```bash\necho $PATH\nprice=$5"


def test_open_bracket_is_shown_as_written_until_it_closes():
    sn = mathfence.StreamNormalizer()
    assert sn.feed("Let \\(x + ") == "Let \\(x + "
    assert sn.feed("y\\)") == "Let \\(x + y\\)"  # closing bracket at the end: wait one more character
    assert sn.feed(" ok") == "Let $x + y$ ok"


def test_open_inline_code_is_not_turned_into_math():
    sn = mathfence.StreamNormalizer()
    screens = [sn.feed(c) for c in "`echo $5 and $x$` now"]
    assert all(judge.math_values(s) == [] for s in screens)
    assert sn.finish() == "`echo $5 and $x$` now"


def test_finish_equals_normalize_and_is_final():
    text = "Pay $5 and \\(x\\).\n\n\\[y\\]\n\nEnd $6"
    sn = mathfence.StreamNormalizer(profile="streamlit")
    for ch in text:
        sn.feed(ch)
    assert sn.text == text
    assert sn.finish() == mathfence.normalize(text, profile="streamlit")
    with pytest.raises(RuntimeError, match="finish"):
        sn.feed("more")


def test_settled_paragraphs_are_not_reprocessed():
    sn = mathfence.StreamNormalizer()
    sn.feed("First $5 here.\n\nSecond $x$ there.")
    assert sn.stats.committed_chars == len("First $5 here.\n\n")
    before = sn.stats.reprocessed_chars
    sn.feed(" More")
    assert sn.stats.reprocessed_chars - before == len("Second $x$ there. More")


def test_long_answer_work_is_bounded():
    spec = judge.load_streams()["long"]
    doc = judge.build_long_answer(spec)
    assert len(doc) >= spec["target_chars"]
    step = -(-len(doc) // spec["chunks"])
    chunks = [doc[i : i + step] for i in range(0, len(doc), step)]
    assert len(chunks) <= spec["chunks"]
    sn = mathfence.StreamNormalizer()
    for chunk in chunks:
        sn.feed(chunk)
    print("reprocessed", sn.stats.reprocessed_chars, "document", len(doc))
    assert sn.stats.reprocessed_chars <= len(doc) * 5
    assert sn.finish() == mathfence.normalize(doc)


def test_feed_rejects_non_strings():
    with pytest.raises(TypeError, match="chunk must be str"):
        mathfence.StreamNormalizer().feed(b"x")  # type: ignore[arg-type]


@pytest.mark.parametrize("profile", mathfence.PROFILES)
def test_random_chunking_matches_normalize(profile):
    rng = random.Random(7)
    for text in random_texts(300, seed=99):
        sn = mathfence.StreamNormalizer(profile=profile)
        i = 0
        while i < len(text):
            step = rng.randint(1, 6)
            sn.feed(text[i : i + step])
            i += step
        assert sn.finish() == mathfence.normalize(text, profile=profile), repr(text)


def test_settled_part_plus_tail_equals_normalize():
    # The paragraph-boundary shortcut must not change the result.
    from mathfence.core import run

    rng = random.Random(11)
    for text in random_texts(300, seed=5):
        sn = mathfence.StreamNormalizer()
        i = 0
        while i < len(text):
            step = rng.randint(1, 9)
            sn.feed(text[i : i + step])
            i += step
        assert sn._committed + run(sn._tail, "remark", False).text == mathfence.normalize(text), repr(text)


def test_long_list_without_blank_lines_is_settled():
    # A 30K-char bullet list used to be reprocessed on every feed (thousands of times).
    text = "".join(f"- item number {i} with some words\n" for i in range(800))
    sn = mathfence.StreamNormalizer()
    for i in range(0, len(text), 150):
        sn.feed(text[i : i + 150])
    assert sn.finish() == mathfence.normalize(text)
    assert sn.stats.reprocessed_chars <= 5 * len(text)


def test_list_items_with_math_markers_stay_unsettled_but_equal():
    text = "".join(f"- costs ${i} or $x_{i}$\n" for i in range(40))
    sn = mathfence.StreamNormalizer()
    for i in range(0, len(text), 7):
        sn.feed(text[i : i + 7])
    assert sn.finish() == mathfence.normalize(text)
