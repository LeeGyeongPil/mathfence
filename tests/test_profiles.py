"""AC-6: renderer profiles and argument validation."""

import pytest

import mathfence


def test_profiles_constant():
    assert mathfence.PROFILES == ("remark", "streamlit")


def test_streamlit_puts_block_math_on_its_own_lines():
    out = mathfence.normalize("Area: \\[x^2\\] done", profile="streamlit")
    assert out == "Area:\n\n$$\nx^2\n$$\n\ndone"


def test_streamlit_keeps_list_and_quote_prefixes():
    assert mathfence.normalize("> see \\[x\\] now", profile="streamlit") == "> see\n>\n> $$\n> x\n> $$\n>\n> now"
    assert mathfence.normalize("- item \\[y\\]\n- b", profile="streamlit") == "- item\n\n  $$\n  y\n  $$\n- b"


def test_streamlit_splits_existing_inline_double_dollars_too():
    out = mathfence.normalize("$$x$$ then $$y$$", profile="streamlit")
    assert out == "$$\nx\n$$\n\nthen\n\n$$\ny\n$$"


def test_streamlit_leaves_tables_alone():
    assert mathfence.normalize("| a | $$x$$ |", profile="streamlit") == "| a | $$x$$ |"


def test_inline_results_match_the_remark_profile():
    src = "Pay $5 for \\(a+b\\) and $x^2$, then $6."
    assert mathfence.normalize(src, profile="streamlit") == mathfence.normalize(src, profile="remark")


def test_remark_only_lays_out_display_math_that_stands_alone():
    assert mathfence.normalize("\\[x\\]") == "$$\nx\n$$"
    assert mathfence.normalize("Area: \\[x\\] done") == "Area: $$x$$ done"


def test_unknown_profile_lists_the_allowed_values():
    with pytest.raises(ValueError, match=r"remark, streamlit"):
        mathfence.normalize("x", profile="gradio")
    with pytest.raises(ValueError):
        mathfence.analyze("x", profile="")
    with pytest.raises(ValueError):
        mathfence.StreamNormalizer(profile="nope")


@pytest.mark.parametrize("bad", [None, 5, b"bytes", ["x"]])
def test_non_string_input_is_a_type_error(bad):
    with pytest.raises(TypeError, match="text must be str"):
        mathfence.normalize(bad)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        mathfence.analyze(bad)  # type: ignore[arg-type]


def test_bytes_error_suggests_decoding():
    with pytest.raises(TypeError, match="decode"):
        mathfence.normalize(b"x")  # type: ignore[arg-type]
