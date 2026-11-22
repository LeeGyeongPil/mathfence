"""AC-1 and the corpus half of AC-2: score the corpus with the lenient judge."""

import judge
import mathfence


def _failures(cases):
    bad = []
    for case in cases:
        out = mathfence.normalize(case["src"])
        if not judge.same_math(judge.math_values(out), case["expect"]):
            bad.append((case["id"], out))
    return bad


def test_corpus_has_enough_cases():
    cases = judge.load_cases()
    assert len(cases) >= 80
    assert len({c["id"] for c in cases}) == len(cases)


def test_corpus_score():
    cases = judge.load_cases()
    bad = _failures(cases)
    score = 1 - len(bad) / len(cases)
    print(f"pass {score:.3f} ({len(cases) - len(bad)}/{len(cases)})")
    assert score >= 0.95, bad
    failing_ids = {i for i, _ in bad}
    # The two cases the research prototype got wrong must pass.
    assert "bracket-list" not in failing_ids
    assert "h-bracket-blockquote" not in failing_ids


def test_verbatim_fragments():
    for case in judge.load_cases():
        out = mathfence.normalize(case["src"])
        for fragment in case["verbatim"]:
            assert fragment in out, (case["id"], fragment, out)


def test_corpus_is_stable_under_both_profiles():
    for case in judge.load_cases():
        for profile in mathfence.PROFILES:
            once = mathfence.normalize(case["src"], profile=profile)
            assert mathfence.normalize(once, profile=profile) == once, case["id"]
