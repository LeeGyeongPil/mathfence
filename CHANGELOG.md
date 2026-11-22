# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0]

### Added
- `normalize()` and `analyze()`: rewrite `\( \)` and `\[ \]` to `$ $` and `$$ $$`, decide every other `$` by its pair, and escape currency and stray dollars as `\$`.
- Protected regions copied byte for byte: fenced code (also inside lists and quotes, also unclosed), indented code, code spans, HTML blocks and tags, autolinks, bare URLs.
- `StreamNormalizer` for token streams: holds a closing `$` at the end of the text until the next character arrives, leaves unclosed code spans alone and settles finished paragraphs and top-level list items whose settled part has no `$` or backslash so they are not processed again.
- Profiles `remark` (default) and `streamlit` (display math on its own lines, list and quote prefixes kept).
- `mathfence` command: `--explain` (table or JSON with a rule id per decision), `--check`, `--profile`, `--format`, `--lang en|ko`.
- English and Korean command line messages (`--lang`, `MATHFENCE_LANG`, `LC_ALL`, `LC_MESSAGES`, `LANG`).
- 94-case corpus, a lenient markdown-it-py judge and `bench/compare.py` comparing mathfence with no processing, escaping every `$` and a typical regex recipe.
- Streamlit replay example in `examples/streamlit_chat.py`.

[Unreleased]: https://github.com/LeeGyeongPil/mathfence/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/LeeGyeongPil/mathfence/releases/tag/v0.1.0
