# let-go-wiki

A knowledge base for **developing and using** [let-go](https://github.com/nooga/let-go),
a Clojure dialect on a Go bytecode VM. Markdown + YAML frontmatter (llm_wiki ⊕ OKF),
agent-authored and agent-maintained, published as a styled static site.

## Prerequisites
- Python 3.13 (`make install` for deps).
- **`lg` ≥ 1.11.1** (the let-go binary) — the authoring engine reads `.lg` source
  through let-go's own reader and relies on `*command-line-args*` (added in
  1.11.0). Current release: [v1.11.1](https://github.com/nooga/let-go/releases).
  Install via `brew install nooga/tap/let-go` or a release tarball. (There is no
  mise registry entry for `lg` yet; `lgx` is pinned in `.mise.toml`, `lg` is not.)

## Use
- `lgx doctor` — validate pages against the schema
- `lgx viz` — regenerate the OKF graph (`viz.html`)
- `lgx site` — build the site into `site/`
- `lgx serve` — local preview

`lgx` is provided via [mise](https://mise.jdx.dev) (see `.mise.toml`): run `mise trust && mise install && lgx deps` (the last installs the Python deps into an auto-managed `.venv`), then `mise exec -- lgx <task>` (or `lgx <task>` with mise activated). All tasks also run directly, e.g. `python tools/build_site.py`.

See [AGENTS.md](AGENTS.md) for the page format and conventions.
