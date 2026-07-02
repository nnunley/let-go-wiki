# Population sprint runbook

The repeatable loop for authoring, reviewing, and publishing wiki pages, proven
end-to-end in Plan C (stdlib batch, the Indexed-RPN IR page, the xsofy case
study). Re-run it to grow coverage.

## Prerequisites
- `lg` ≥ 1.11.1 on PATH; the `~/development/let-go` checkout present.
- `make install` (or `pip install -r requirements.txt`).

## The loop

1. **Refresh the manifest** (the stdlib work-list):
   `python -m tools.enrich.prepare --source-root ../let-go`  (or `lgx enrich`)
2. **See coverage / what's pending:**
   `python -m tools.enrich.status`  (or `lgx status`)
3. **Generate N authoring briefs** for the next pending concepts:
   `python -m tools.enrich.next_batch --count N`  (or `lgx next`)
   Each brief (`.enrich/briefs/<id>.md`) carries the concept's signature,
   docstring, target page path, sibling ids, and the allowed tag vocabulary.
4. **Author** — dispatch one Claude authoring subagent per brief, using
   `tools/enrich/prompts/reference_instruction.md`. The subagent constructs 1–3
   example forms, runs `lg -e '<form>'`, and uses the **real** output (never
   invented). Stdlib/reference pages go to `references/<ns>/<name>.md`; internals
   concepts to `concepts/<slug>.md`; projects to `projects/<name>.md`.
5. **Gate:** `python tools/check_wiki.py .` — must print `check_wiki: OK`. It
   enforces required frontmatter, tags ⊆ `_meta/taxonomy.md` (≤5), file-relative
   links, **no broken internal links**, and **no orphan pages** (every page must
   be linked from `index.md` or another page).
6. **Accuracy review** — dispatch a reviewer subagent that **re-runs every
   `lg -e` example** and compares to the claimed `;; =>` output, checks the
   description against the source docstring, and verifies signatures. For
   **macros**, confirm the signature shows the *usage* form, not the raw
   `defmacro` parameter vector (e.g. `(when test & body)`, not
   `(when [condition & forms])`). Fix flagged pages; promote accurate ones from
   `status: speculative` → `status: stable`.
7. **Bookkeeping:** add each page to `index.md` under its category (one bullet
   with the frontmatter `description`); append a `log.md` ingest entry.
8. **Publish:** `python tools/viz/render_viz.py . viz.html` (regenerate the
   graph), `python tools/build_site.py` (must build `--strict` clean).
9. **Commit + push:** `git add … && git commit && git push`. The Pages CI
   rebuilds the site and regenerates a fresh `site/viz.html` on push to `main`.
   Verify a new page returns 200, e.g.
   `curl -so /dev/null -w '%{http_code}' https://nnunley.github.io/let-go-wiki/references/clojure.core/apply/`.

## Reading source repos (avoid the xsofy stall)

When a subagent authors from a source repo:

- **Skip non-useful large files** — debug logs (`debug.log`), media (`*.gif`,
  screenshots, `*.png`), binaries, `.jj`/`.git` internals. Reading these wastes
  context and can hang the subagent (xsofy ships a 15 MB `debug.log` and a 4 MB
  gif — do not read them).
- **For large *useful* files** (a big source file, a long design doc), use the
  **rlm** skill to subdivide/chunk the file rather than reading it whole.
- Point subagents at the high-signal files explicitly (README, the main `.lg`
  entrypoint, relevant `docs/` design notes), not "read the whole repo."

## Scope beyond the stdlib

- **Projects** (`projects/`): one page per repo — xsofy, lgcr, lgx, legmacs,
  let-go-lab. Read the README + main source; skip large artifacts per above.
- **Internals** (`concepts/`): read the Go packages (`pkg/vm`, `pkg/ir`,
  `pkg/compiler`) + the gitignored `let-go/docs/superpowers/**` design docs.
  Internals pages must cite external references where they exist (papers,
  other-language IRs) in `# Citations`.
- **Docs-crawl pass** (`references/`): use
  `tools/enrich/prompts/web_ingestion_instruction.md` — the four-gate reference
  test + the let-go must-capture extractions (clojure-compat, interop,
  limitations).

## Notes

- Native/intrinsic functions registered in Go (e.g. `reduce`, `assoc`, `conj`)
  are **not** in `.lg` source, so `enrich prepare` cannot enumerate them — they
  need the deferred Go-internals path or a curated supplement.
- `.enrich/` and `site/` are generated and gitignored; `viz.html` is committed.
