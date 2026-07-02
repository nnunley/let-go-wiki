# Maintaining let-go-wiki (AGENTS.md)

This repo is an **LLM wiki** about developing and using **let-go** (a Clojure
dialect on a Go bytecode VM). It follows the llm_wiki pattern harmonized with
Google's Open Knowledge Format (OKF). Humans curate and ask; agents write and
maintain pages. This file is the canonical, model-agnostic schema — Claude,
Codex, Cursor, Gemini all read it (CLAUDE.md just points here).

## Page format (every non-reserved .md)

    ---
    type: Concept            # OKF-required; capitalized kind (Concept/Entity/Function/
                             #   Macro/Namespace/Package/Reference/Project/Idea)
    category: concept        # llm_wiki: concept|entity|idea|project|source|reference
    title: "Stack VM"
    description: "One sentence; used verbatim in index.md."
    tags: [vm, bytecode]     # from _meta/taxonomy.md, max 5
    resource: "https://github.com/nooga/let-go/tree/main/pkg/vm"  # source URI
    sources: ["repo: nooga/let-go pkg/vm, 2026-07-01"]
    created: "2026-07-01"
    updated: "2026-07-01"
    status: speculative      # speculative|active|stable|archived
    ---

- Cross-links are **file-relative** markdown links (`[stack vm](../concepts/stack-vm.md)`), never `/absolute`.
- `resource`/`sources` must cite where a claim comes from. Agent drafts start `speculative`; promote to `stable` only after checking against the actual code/runtime.

## Directories
`concepts/` (how it works / internals), `entities/` (the things),
`projects/` (programs built with let-go), `ideas/` (roadmap), `sources/`
(one page per ingested source), `references/` (OKF reference docs).

## Bookkeeping
- `index.md` = catalog by category; add one line per page: `[[path/slug]] — summary`.
- `log.md` = append-only; entries start `## [YYYY-MM-DD] <op> | <subject>`.
- Validate before commit: `python tools/check_wiki.py` (or `lgx doctor`).

## Build & publish
- `lgx doctor` — validate pages.  `lgx viz` — regenerate the graph.
- `lgx site` — build the styled site into `site/`.  `lgx serve` — local preview.

(lgx is provided via mise — `mise exec -- lgx <task>`, or just `lgx <task>` with mise activated.)
The site renders only content dirs + index.md; tooling/process files are excluded.

## Populate
Author new pages with the repeatable loop in
[docs/superpowers/runbooks/population-sprint.md](docs/superpowers/runbooks/population-sprint.md):
`lgx enrich` → `lgx status` → `lgx next` → author via subagents (real `lg -e`
output) → `lgx doctor` → accuracy-review → promote to `stable` → publish. When
reading source repos, skip non-useful large files (debug logs, media, binaries)
and use the `rlm` skill to subdivide large *useful* files.
