"""Messages for the command line, in English and Korean.

All user-visible strings live in :data:`MESSAGES`.  The language is chosen by
``--lang`` > ``MATHFENCE_LANG`` > ``LC_ALL`` > ``LC_MESSAGES`` > ``LANG``;
anything that is not Korean means English.
"""

from __future__ import annotations

from collections.abc import Mapping

LANGS: tuple[str, ...] = ("en", "ko")
ENV_VAR = "MATHFENCE_LANG"

_HELP_EN = """\
usage: mathfence [FILE ...] [--profile NAME] [--explain] [--format text|json]
                 [--check] [--lang en|ko] [--version] [-h]

Make LLM Markdown safe for $-math renderers: turn \\( \\) and \\[ \\] into $ and $$,
escape currency dollar signs as \\$, and leave code, URLs and HTML untouched.

arguments:
  FILE               Markdown file to read. Use "-" or no FILE to read standard input.

options:
  --profile NAME     Renderer profile: remark (default) or streamlit.
  --explain          Print a table of every decision with its rule instead of the text.
                     Accepts a single input.
  --format FORMAT    text (default) or json. json prints file, changed, text and
                     decisions (line, column, action, rule, ...) for a single input.
  --check            Print the files that would change and exit 1 if there are any
                     (0 if none). Prints no normalized text.
  --lang LANG        Message language: en or ko. Default: MATHFENCE_LANG, then
                     LC_ALL, LC_MESSAGES, LANG; anything but Korean means English.
  --version          Show the version and exit.
  -h, --help         Show this help and exit.

exit status: 0 ok, 1 --check found changes, 2 input or usage error.
"""

_HELP_KO = """\
사용법: mathfence [FILE ...] [--profile NAME] [--explain] [--format text|json]
                  [--check] [--lang en|ko] [--version] [-h]

LLM 마크다운을 $ 수식 렌더러에 안전하게 넘기도록 고칩니다. \\( \\) 와 \\[ \\] 를 $ 와 $$ 로
바꾸고, 가격 달러 기호는 \\$ 로 이스케이프하며, 코드·URL·HTML 은 건드리지 않습니다.

인자:
  FILE               읽을 마크다운 파일. "-" 이거나 FILE 이 없으면 표준 입력을 읽습니다.

옵션:
  --profile NAME     렌더러 프로필: remark(기본) 또는 streamlit.
  --explain          결과 텍스트 대신 모든 판정과 규칙을 표로 출력합니다. 입력은 하나만 받습니다.
  --format FORMAT    text(기본) 또는 json. json 은 입력 하나에 대해 file, changed, text,
                     decisions(line, column, action, rule, ...)를 출력합니다.
  --check            바뀔 파일 이름을 출력하고, 있으면 종료 코드 1(없으면 0)을 돌려줍니다.
                     정규화된 텍스트는 출력하지 않습니다.
  --lang LANG        메시지 언어: en 또는 ko. 기본값: MATHFENCE_LANG, 그다음 LC_ALL,
                     LC_MESSAGES, LANG 순이며, 한국어가 아니면 영어입니다.
  --version          버전을 보여 주고 끝냅니다.
  -h, --help         이 도움말을 보여 주고 끝냅니다.

종료 코드: 0 정상, 1 --check 에서 바뀔 것 있음, 2 입력·사용법 오류.
"""

MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "help.text": _HELP_EN,
        "error.file_not_found": "mathfence: error: file not found: {path}\n  Check the path, or pass '-' to read standard input.",
        "error.not_a_file": "mathfence: error: not a readable file: {path}\n  Pass a Markdown file, or '-' to read standard input.",
        "error.not_utf8": "mathfence: error: {path} is not valid UTF-8 text.\n  Convert it first, e.g. `iconv -f <encoding> -t UTF-8 {path}`.",
        "error.profile": "mathfence: error: unknown profile '{value}'.\n  Choose one of: {choices}.",
        "error.format": "mathfence: error: unknown format '{value}'.\n  Choose one of: text, json.",
        "error.lang": "mathfence: error: unknown language '{value}'.\n  Choose one of: en, ko.",
        "error.single_input": "mathfence: error: {option} accepts a single input.\n  Run it once per file.",
        "error.usage": "mathfence: error: {detail}\n  Run `mathfence --help` for usage.",
        "error.unknown_option": "mathfence: error: unrecognized arguments: {option}\n  Run `mathfence --help` for usage.",
        "error.missing_value": "mathfence: error: option {option} needs a value.\n  Run `mathfence --help` for usage.",
        "error.usage_generic": "mathfence: error: invalid command line.\n  Run `mathfence --help` for usage.",
        "check.would_change": "{path}: would change",
        "check.clean": "{count} file(s) checked, nothing to change.",
        "explain.col.position": "line:col",
        "explain.col.action": "action",
        "explain.col.rule": "rule",
        "explain.col.source": "source",
        "explain.col.reason": "reason",
        "explain.none": "No dollar signs, \\( \\) or \\[ \\] to decide on.",
        "explain.summary": "{total} decision(s) in {path}",
        "stdin.name": "<stdin>",
        "reason.math-pair": "A matching $ closes it and the text between looks like a formula: kept as math.",
        "reason.close-followed-by-digit": "The closing $ is followed by a digit, so this reads as prices, not math: escaped.",
        "reason.close-followed-by-dollar": "The next $ starts a $$ run, so there is no clean closing $: escaped.",
        "reason.body-empty": "Nothing between the dollars: escaped.",
        "reason.body-edge-space": "The text between the dollars starts or ends with a space: escaped as currency or stray $.",
        "reason.body-words": "Two plain words in a row between the dollars: it is prose, not a formula: escaped.",
        "reason.body-ends-operator": "The text between the dollars ends with an operator or punctuation: escaped.",
        "reason.body-block-boundary": "The pair would cross a list item, quote, heading or table row: escaped.",
        "reason.no-closing": "No closing $ in the same paragraph: escaped.",
        "reason.double-currency": "A $$ pair whose text starts with a digit and has no TeX: prices, escaped.",
        "reason.dollar-run": "Three or more dollars in a row: escaped.",
        "reason.stream-pending": "Held back while streaming: the next character decides it. Shown escaped for now.",
        "reason.display-own-line": "Display math moved onto its own lines (keeping list and quote prefixes).",
        "reason.bracket-inline": "\\( \\) rewritten as $ $.",
        "reason.bracket-inline-double": "\\( \\) rewritten as $$ $$ because $ $ would be misread next to the text around it.",
        "reason.bracket-display": "\\[ \\] rewritten as $$ $$.",
        "reason.bracket-has-dollar": "\\( \\) contains a $, so it is rewritten as $$ $$.",
        "reason.bracket-ambiguous": "Left as written: no safe $ form exists for this body.",
        "reason.code-fence": "Fenced code: copied unchanged.",
        "reason.code-span": "Inline code: copied unchanged.",
        "reason.indented-code": "Indented code: copied unchanged.",
        "reason.autolink": "Autolink: copied unchanged.",
        "reason.bare-url": "URL: copied unchanged.",
        "reason.html-block": "HTML block: copied unchanged.",
        "reason.html-tag": "HTML tag: copied unchanged.",
    },
    "ko": {
        "help.text": _HELP_KO,
        "error.file_not_found": "mathfence: 오류: 파일을 찾을 수 없습니다: {path}\n  경로를 확인하거나, 표준 입력을 읽으려면 '-' 를 넘기세요.",
        "error.not_a_file": "mathfence: 오류: 읽을 수 있는 파일이 아닙니다: {path}\n  마크다운 파일을 넘기거나, 표준 입력을 읽으려면 '-' 를 넘기세요.",
        "error.not_utf8": "mathfence: 오류: {path} 은(는) UTF-8 텍스트가 아닙니다.\n  먼저 변환하세요. 예: `iconv -f <인코딩> -t UTF-8 {path}`.",
        "error.profile": "mathfence: 오류: 알 수 없는 프로필 '{value}'.\n  다음 중에서 고르세요: {choices}.",
        "error.format": "mathfence: 오류: 알 수 없는 형식 '{value}'.\n  다음 중에서 고르세요: text, json.",
        "error.lang": "mathfence: 오류: 알 수 없는 언어 '{value}'.\n  다음 중에서 고르세요: en, ko.",
        "error.single_input": "mathfence: 오류: {option} 은(는) 입력을 하나만 받습니다.\n  파일마다 한 번씩 실행하세요.",
        "error.usage": "mathfence: 오류: {detail}\n  사용법은 `mathfence --help` 로 확인하세요.",
        "error.unknown_option": "mathfence: 오류: 알 수 없는 인자: {option}\n  사용법은 `mathfence --help` 로 확인하세요.",
        "error.missing_value": "mathfence: 오류: {option} 옵션에는 값이 필요합니다.\n  사용법은 `mathfence --help` 로 확인하세요.",
        "error.usage_generic": "mathfence: 오류: 명령줄이 올바르지 않습니다.\n  사용법은 `mathfence --help` 로 확인하세요.",
        "check.would_change": "{path}: 바뀔 내용이 있습니다",
        "check.clean": "파일 {count}개를 확인했고 바뀔 내용이 없습니다.",
        "explain.col.position": "줄:칸",
        "explain.col.action": "동작",
        "explain.col.rule": "규칙",
        "explain.col.source": "원문",
        "explain.col.reason": "이유",
        "explain.none": "판정할 달러 기호, \\( \\), \\[ \\] 가 없습니다.",
        "explain.summary": "{path}: 판정 {total}건",
        "stdin.name": "<표준 입력>",
        "reason.math-pair": "짝이 되는 $ 가 있고 그 사이가 수식처럼 보여 수식으로 유지했습니다.",
        "reason.close-followed-by-digit": "닫는 $ 뒤에 숫자가 와서 수식이 아니라 가격으로 보고 이스케이프했습니다.",
        "reason.close-followed-by-dollar": "다음 $ 가 $$ 묶음의 시작이라 깔끔하게 닫을 수 없어 이스케이프했습니다.",
        "reason.body-empty": "달러 사이가 비어 있어 이스케이프했습니다.",
        "reason.body-edge-space": "달러 사이 내용이 공백으로 시작하거나 끝나 통화·낱개 $ 로 보고 이스케이프했습니다.",
        "reason.body-words": "달러 사이에 평범한 단어 두 개가 이어져 있어 수식이 아닌 문장으로 보고 이스케이프했습니다.",
        "reason.body-ends-operator": "달러 사이 내용이 연산자나 문장부호로 끝나 이스케이프했습니다.",
        "reason.body-block-boundary": "짝이 목록 항목·인용·제목·표 행을 가로질러 이스케이프했습니다.",
        "reason.no-closing": "같은 문단에 닫는 $ 가 없어 이스케이프했습니다.",
        "reason.double-currency": "숫자로 시작하고 TeX 가 없는 $$ 짝이라 가격으로 보고 이스케이프했습니다.",
        "reason.dollar-run": "달러가 세 개 이상 이어져 이스케이프했습니다.",
        "reason.stream-pending": "스트리밍 중이라 보류했습니다. 다음 글자가 와야 정해지며, 지금은 이스케이프해서 보여 줍니다.",
        "reason.display-own-line": "블록 수식을 자기 줄로 옮겼습니다(목록·인용 접두사 유지).",
        "reason.bracket-inline": "\\( \\) 를 $ $ 로 바꿨습니다.",
        "reason.bracket-inline-double": "\\( \\) 를 $$ $$ 로 바꿨습니다. 주변 글자와 붙으면 $ $ 가 잘못 읽히기 때문입니다.",
        "reason.bracket-display": "\\[ \\] 를 $$ $$ 로 바꿨습니다.",
        "reason.bracket-has-dollar": "\\( \\) 안에 $ 가 있어 $$ $$ 로 바꿨습니다.",
        "reason.bracket-ambiguous": "이 내용에는 안전한 $ 형태가 없어 그대로 두었습니다.",
        "reason.code-fence": "펜스 코드라 그대로 복사했습니다.",
        "reason.code-span": "인라인 코드라 그대로 복사했습니다.",
        "reason.indented-code": "들여쓰기 코드라 그대로 복사했습니다.",
        "reason.autolink": "자동 링크라 그대로 복사했습니다.",
        "reason.bare-url": "URL 이라 그대로 복사했습니다.",
        "reason.html-block": "HTML 블록이라 그대로 복사했습니다.",
        "reason.html-tag": "HTML 태그라 그대로 복사했습니다.",
    },
}


def resolve_lang(explicit: str | None = None, environ: Mapping[str, str] | None = None) -> str:
    """Pick ``"en"`` or ``"ko"``.

    Order: ``explicit`` (the ``--lang`` value), then ``MATHFENCE_LANG``,
    ``LC_ALL``, ``LC_MESSAGES``, ``LANG``.  The first non-empty value wins;
    it means Korean if it starts with ``ko``, otherwise English.
    """
    if explicit:
        return "ko" if explicit.strip().lower().startswith("ko") else "en"
    env = environ if environ is not None else {}
    for name in (ENV_VAR, "LC_ALL", "LC_MESSAGES", "LANG"):
        value = (env.get(name) or "").strip()
        if value:
            return "ko" if value.lower().startswith("ko") else "en"
    return "en"


def message(lang: str, key: str, **fields: object) -> str:
    """Look up ``key`` in ``lang`` and fill in ``fields``."""
    text = MESSAGES[lang][key]
    return text.format(**fields) if fields else text
