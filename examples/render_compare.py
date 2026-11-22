"""Write static HTML pages that show what a ``$``-math renderer does with an answer.

    uv run python examples/render_compare.py

Output: docs/demo/before-after.en.html, before-after.ko.html, streaming.en.html, streaming.ko.html

The renderer is markdown-it-py + dollarmath (a dev dependency).  Math is drawn
as a highlighted italic box (no KaTeX needed), so a price that was wrongly
paired as a formula is easy to see.  Not a live model call: the answer is recorded.
"""

from __future__ import annotations

import html
from pathlib import Path

from markdown_it import MarkdownIt
from mdit_py_plugins.dollarmath import dollarmath_plugin

import mathfence

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "demo"

ANSWER = (
    "The plan costs $5 per seat and the cluster fee is $1,200, so the total is $5n + $1,200.\n\n"
    "With \\(n\\) seats the cost per seat is $x = 5 + 1200/n$.\n\n"
    "Shell users can check it with `echo $HOME`.\n"
)

STREAM_CHUNKS = ["The fee is $", "5 and the tax is $", "10, area $x", "^2$."]

TEXT = {
    "en": {
        "t1": "Same answer, same renderer",
        "off": "mathfence OFF",
        "on": "mathfence ON",
        "off_note": "Prices got paired into formulas (highlighted boxes); the bracket math stays as plain text.",
        "on_note": "Prices stay text, real formulas are math, the code span is untouched.",
        "legend": "Highlighted italic box = what the renderer treats as a formula",
        "t2": "Streaming: what the screen shows after each chunk",
        "chunk": "chunk",
        "raw": "raw text",
        "fixed": "with StreamNormalizer",
        "stream_note": "Raw text flashes a fake formula as soon as a second $ arrives; the stream holds it back.",
    },
    "ko": {
        "t1": "같은 답변, 같은 렌더러",
        "off": "mathfence 끔",
        "on": "mathfence 켬",
        "off_note": "가격이 수식으로 짝지어졌고(강조 상자), 괄호 수식은 글자 그대로 남습니다.",
        "on_note": "가격은 글자로, 진짜 수식은 수식으로, 코드 조각은 그대로입니다.",
        "legend": "강조된 기울임 상자 = 렌더러가 수식으로 본 부분",
        "t2": "스트리밍: 조각이 올 때마다 화면에 보이는 모습",
        "chunk": "조각",
        "raw": "원문 그대로",
        "fixed": "StreamNormalizer 사용",
        "stream_note": "원문은 두 번째 $ 가 오자마자 가짜 수식이 번쩍이고, 스트림은 그것을 붙들어 둡니다.",
    },
}

CSS = """
body{font:17px/1.55 system-ui,sans-serif;margin:24px;color:#1f2328;background:#fff}
h1{font-size:22px;margin:0 0 14px}
.row{display:flex;gap:20px}
.card{flex:1;border:1px solid #d0d7de;border-radius:8px;padding:14px 18px}
.card h2{font-size:16px;margin:0 0 6px}
.off h2{color:#cf222e}.on h2{color:#1a7f37}
.note{font-size:14px;color:#57606a;margin:0 0 10px}
.math{font-style:italic;background:#ddf4ff;border:1px solid #54aeff;border-radius:4px;padding:0 4px}
code{background:#eaeef2;border-radius:4px;padding:0 4px}
.legend{font-size:14px;color:#57606a;margin-top:12px}
table{border-collapse:collapse;width:100%}
td,th{border:1px solid #d0d7de;padding:8px 12px;text-align:left;vertical-align:top}
th{background:#f6f8fa;font-size:14px}
td.n{width:90px;color:#57606a}
"""


def make_renderer() -> MarkdownIt:
    md = MarkdownIt("commonmark").use(
        dollarmath_plugin, allow_space=True, allow_digits=True, double_inline=True
    )
    md.add_render_rule(
        "math_inline",
        lambda self, tokens, i, o, e: f'<span class="math">{html.escape(tokens[i].content)}</span>',
    )
    md.add_render_rule(
        "math_inline_double",
        lambda self, tokens, i, o, e: f'<span class="math">{html.escape(tokens[i].content)}</span>',
    )
    md.add_render_rule(
        "math_block",
        lambda self, tokens, i, o, e: f'<p><span class="math">{html.escape(tokens[i].content)}</span></p>',
    )
    return md


def page(title: str, body: str, lang: str) -> str:
    return (
        f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">'
        f"<title>{html.escape(title)}</title><style>{CSS}</style></head><body>{body}</body></html>"
    )


def before_after(lang: str, md: MarkdownIt) -> str:
    t = TEXT[lang]
    off = md.render(ANSWER)
    on = md.render(mathfence.normalize(ANSWER))
    body = (
        f"<h1>{t['t1']}</h1><div class='row'>"
        f"<div class='card off'><h2>{t['off']}</h2><p class='note'>{t['off_note']}</p>{off}</div>"
        f"<div class='card on'><h2>{t['on']}</h2><p class='note'>{t['on_note']}</p>{on}</div>"
        f"</div><p class='legend'><span class='math'>x</span> {t['legend']}</p>"
    )
    return page(t["t1"], body, lang)


def streaming(lang: str, md: MarkdownIt) -> str:
    t = TEXT[lang]
    stream = mathfence.StreamNormalizer()
    received = ""
    rows = []
    for n, chunk in enumerate(STREAM_CHUNKS, 1):
        received += chunk
        shown = stream.feed(chunk)
        rows.append(
            f"<tr><td class='n'>{t['chunk']} {n}<br><code>{html.escape(chunk)}</code></td>"
            f"<td>{md.renderInline(received)}</td><td>{md.renderInline(shown)}</td></tr>"
        )
    body = (
        f"<h1>{t['t2']}</h1><table><tr><th></th><th>{t['raw']}</th><th>{t['fixed']}</th></tr>"
        f"{''.join(rows)}</table><p class='legend'>{t['stream_note']}<br>"
        f"<span class='math'>x</span> {t['legend']}</p>"
    )
    return page(t["t2"], body, lang)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    md = make_renderer()
    for lang in TEXT:
        (OUT / f"before-after.{lang}.html").write_text(before_after(lang, md), encoding="utf-8")
        (OUT / f"streaming.{lang}.html").write_text(streaming(lang, md), encoding="utf-8")
        print(f"wrote docs/demo/before-after.{lang}.html, streaming.{lang}.html")


if __name__ == "__main__":
    main()
