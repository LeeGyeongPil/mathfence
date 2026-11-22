"""Replay recorded LLM answers token by token, with and without mathfence.

Run (no API key, no network needed once Streamlit is installed):

    uv run --with streamlit streamlit run examples/streamlit_chat.py

This is NOT a live model call: the answers below are recorded text that is
replayed a few characters at a time, which is enough to show what a Streamlit
screen does with them.  Open with ``?lang=ko`` for the Korean interface.
"""

import time

import streamlit as st

import mathfence

# ---- UI strings: one table, the same keys in both languages -------------------
TEXT = {
    "en": {
        "title": "mathfence replay",
        "note": "Recorded answers replayed token by token. This is not a live model call.",
        "language": "Language",
        "answer": "Recorded answer",
        "normalize": "Normalize with mathfence",
        "speed": "Characters per step",
        "replay": "Replay",
        "raw": "Raw text from the model",
        "on": "mathfence ON: prices stay text, formulas render.",
        "off": "mathfence OFF: the renderer pairs the dollar signs by itself.",
    },
    "ko": {
        "title": "mathfence 재생 화면",
        "note": "녹화해 둔 답변을 토큰 단위로 다시 흘려 보냅니다. 실제 모델 호출이 아닙니다.",
        "language": "언어",
        "answer": "녹화된 답변",
        "normalize": "mathfence 로 정규화",
        "speed": "한 번에 보내는 글자 수",
        "replay": "다시 재생",
        "raw": "모델이 낸 원문",
        "on": "mathfence 켬: 가격은 글자로, 수식은 수식으로 나옵니다.",
        "off": "mathfence 끔: 렌더러가 달러 기호를 알아서 짝지어 버립니다.",
    },
}
LANG_NAMES = {"en": "English", "ko": "한국어"}

# ---- recorded answers (data, not UI text) -------------------------------------
ANSWERS = {
    "Pricing and a formula": (
        "The plan costs $5 per seat and the cluster fee is $1,200, so the total is $5n + $1,200.\n\n"
        "With \\(n\\) seats the average cost per seat is\n\n"
        "\\[\n\\frac{5n + 1200}{n} = 5 + \\frac{1200}{n}\n\\]\n\n"
        "Shell users can check it with `echo $HOME` and the pricing page https://example.com/pricing?plan=$5.\n"
    ),
    "Euler and shell": (
        "Euler's identity is \\(e^{i\\pi} + 1 = 0\\), and $x^2 \\ge 0$ for every real $x$.\n\n"
        "```bash\ntotal=$((5 + 10))\necho \"costs $total\"\n```\n\n"
        "Pay $5 if $x>5$ holds, otherwise $10.\n"
    ),
    "가격과 수식 (Korean)": (
        "구독료는 월 $5이고 연간 결제는 $50입니다. 넓이는 \\(\\pi r^2\\) 이며 $x^2$ 처럼 씁니다.\n\n"
        "- 기본: $9\n- 합계: $a+b$\n"
    ),
}


def initial_language() -> str:
    """URL ?lang= wins, then the browser language, then English."""
    wanted = st.query_params.get("lang")
    if wanted in TEXT:
        return wanted
    locale = getattr(getattr(st, "context", None), "locale", None) or ""
    return "ko" if str(locale).lower().startswith("ko") else "en"


if "lang" not in st.session_state:
    st.session_state["lang"] = initial_language()

with st.sidebar:
    # The chosen language is kept in the session and in the URL (?lang=...).
    lang = st.selectbox(
        "Language / 언어",  # fixed label: stays correct right after switching
        list(LANG_NAMES),
        index=list(LANG_NAMES).index(st.session_state["lang"]),
        format_func=LANG_NAMES.get,
    )
    st.session_state["lang"] = lang
    st.query_params["lang"] = lang
    t = TEXT[lang]
    name = st.selectbox(t["answer"], list(ANSWERS))
    use_mathfence = st.checkbox(t["normalize"], value=True)
    step = st.slider(t["speed"], 1, 8, 3)
    replay = st.button(t["replay"], type="primary")

st.title(t["title"])
st.caption(t["note"])
st.info(t["on"] if use_mathfence else t["off"])

answer = ANSWERS[name]
view = st.empty()


def render(text: str) -> str:
    """Return what the screen should show for the text received so far."""
    return mathfence.normalize(text, profile="streamlit") if use_mathfence else text


if replay:
    stream = mathfence.StreamNormalizer(profile="streamlit")
    received = ""
    for i in range(0, len(answer), step):
        chunk = answer[i : i + step]
        received += chunk
        # With mathfence the stream keeps its own state; without it we show the raw text.
        view.markdown(stream.feed(chunk) if use_mathfence else received)
        time.sleep(0.03)
    view.markdown(stream.finish() if use_mathfence else received)
else:
    view.markdown(render(answer))

with st.expander(t["raw"]):
    st.code(answer, language="markdown")
