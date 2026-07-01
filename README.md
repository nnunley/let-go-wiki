# let-go-wiki

A knowledge base for **developing and using** [let-go](https://github.com/nooga/let-go),
a Clojure dialect on a Go bytecode VM. Markdown + YAML frontmatter (llm_wiki ⊕ OKF),
agent-authored and agent-maintained, published as a styled static site.

## Use
- `lgx doctor` — validate pages against the schema
- `lgx viz` — regenerate the OKF graph (`viz.html`)
- `lgx site` — build the site into `site/`
- `lgx serve` — local preview

`lgx` is provided via [mise](https://mise.jdx.dev) (see `.mise.toml`): run `mise trust && mise install`, then `mise exec -- lgx <task>` (or `lgx <task>` with mise activated). All tasks also run directly, e.g. `python tools/build_site.py`.

See [AGENTS.md](AGENTS.md) for the page format and conventions.
