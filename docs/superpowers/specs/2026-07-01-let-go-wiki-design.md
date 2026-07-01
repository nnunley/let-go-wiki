---
title: "let-go-wiki — Design Spec"
date: "2026-07-01"
status: draft
authors: ["ndn", "Claude (Opus 4.8)"]
---

# let-go-wiki — Design Spec

## 1. Overview

A standalone, git-tracked knowledge base at `~/development/let-go-wiki` for
**developing and using** the [let-go](https://github.com/nooga/let-go)
ecosystem. It follows the user's existing **llm_wiki pattern** (agent-authored,
agent-maintained markdown wiki) **harmonized with Google's Open Knowledge
Format (OKF)** so a single corpus of markdown files works with the user's own
`llm-wiki` tooling *and* with OKF tooling.

Audience: **humans first, agent-consumable second.** Humans browse a styled
static site; agents load the raw markdown into context and maintain it.

### Goals

- One canonical corpus of markdown + YAML frontmatter, authored/maintained by
  agents, versioned in its own git repo, shareable with let-go contributors.
- Strong maintenance tooling: reuse the user's `llm-wiki` CLI and
  `~/pkm/.claude/skills/wiki/*`, plus a vendored OKF graph visualizer.
- An automated authoring engine — `enrich`, recast for let-go — that mints one
  structured doc per code/runtime concept, then crawls curated docs to enrich.
- A published, **styled** human surface: a GitHub Pages site matching let-go's
  own published-page fonts and colors.

### Non-goals

- No GCP / BigQuery / Gemini / ADK dependency. We reuse OKF's *format*, its
  *visualizer*, and the *workflow discipline* of `enrich` — not its cloud code.
- No pure GitHub Wiki (Gollum) target. Superseded by the GitHub Pages site
  (§8), which gives full control over style. (A wiki mirror could be added
  later but is out of scope.)
- Not a hand-authored wiki. The human curates sources and asks questions; the
  agent writes and maintains pages.

## 2. Architecture — three layers

Mirrors the `~/pkm/llm_wiki.md` model.

1. **Raw sources (source of truth, read-only):** the upstream repos and
   curated external docs. Never modified by the wiki. See §5.
2. **The canonical wiki (agent-owned):** `~/development/let-go-wiki/` — markdown
   + frontmatter pages the agent creates and maintains. §3, §4.
3. **Consumption / publication (generated):** local browse (Obsidian/editor),
   the vendored OKF `viz.html` graph, and the styled GitHub Pages site. §7, §8.

The **schema layer** (per llm_wiki) is **model-agnostic**: the canonical
maintenance instructions live in a root **`AGENTS.md`** (the neutral,
cross-tool standard read by Codex and others), with **`CLAUDE.md` a thin
pointer** (`See AGENTS.md`) so Claude Code picks it up too. Any coding agent —
Claude, Codex, Cursor, Gemini — gets the same instructions from one source.

### 2.1 Multi-party repo hygiene

The repo is maintained by multiple parties and published as a static site, so a
clone must be **self-contained** regardless of a contributor's *global* git
ignore. The authoring machine's `~/.config/git/ignore` excludes `/*.md` (all
root markdown: `index.md`, `log.md`, `AGENTS.md`, `CLAUDE.md`, `README.md`),
`.claude/`, and `docs/superpowers/`. Mitigation: an **authoritative repo-root
`.gitignore` with negation rules** (`!/index.md`, `!/AGENTS.md`, …) — negations
in a repo-root `.gitignore` outrank `core.excludesFile`, so these files stay
trackable by a normal `git add` for everyone. Generated output (`site/`) stays
ignored and is deployed via CI / a `gh-pages` branch.

## 3. Canonical format — llm_wiki ⊕ OKF

OKF's SPEC §10 explicitly names "LLM wiki repositories" as its closest sibling,
so the formats harmonize. Every page carries **both** vocabularies so all
tooling reads one file:

```yaml
---
type: Concept                 # OKF-required; capitalized concept kind
category: concept             # llm_wiki: concept | entity | idea | project | source
title: "Stack VM"
description: "One-sentence summary; used verbatim in generated index.md."
tags: [vm, bytecode]          # from _meta/taxonomy.md (max 5)
resource: "https://github.com/nooga/let-go/tree/main/pkg/vm"  # OKF canonical URI
sources: ["repo: nooga/let-go pkg/vm, 2026-07-01"]            # llm_wiki provenance
created: "2026-07-01"
updated: "2026-07-01"
status: speculative           # speculative | active | stable | archived
---
```

- `type` (OKF-required) is the capitalized form of `category`, or a finer kind
  (`Function`, `Macro`, `Namespace`, `Package`, `Reference`, `Project`).
- `resource` cites the exact source path/URI; `sources` carries llm_wiki-style
  provenance. Both point back to code so every claim is traceable.
- `status` starts `speculative` for agent-drafted pages; promoted to `stable`
  only after review against the actual code/runtime.

**Cross-links:** file-relative markdown links (e.g. `[stack vm](../concepts/stack-vm.md)`),
**not** `/absolute` links — this keeps links working when browsed as plain
files on GitHub and when rendered by the static-site generator. (This follows
OKF's reference-agent link rule, which favors relative paths for GitHub
rendering, over the SPEC's `/absolute` recommendation.)

**Conformance:** every non-reserved `.md` file has parseable frontmatter with a
non-empty `type` — satisfying OKF v0.1 §9 so the visualizer works unmodified.

## 4. Directory structure

```
let-go-wiki/
  index.md                 # catalog by category (maintained by llm-wiki CLI)
  log.md                   # append-only chronological log (llm-wiki CLI)
  AGENTS.md                # CANONICAL schema/maintenance instructions (model-agnostic)
  CLAUDE.md                # thin pointer: "See AGENTS.md"
  _meta/
    taxonomy.md            # let-go-specific tag vocabulary (fresh, not PKM's)
  concepts/                # HOW it works — implementation & language internals
                           #   (developing let-go): compiler, bytecode, stack VM,
                           #   runtime, persistent data structures, transducers,
                           #   Go interop model, AOT→binary, WASM build, core.async
  entities/                # the THINGS: let-go, xsofy, lgx, let-go-lab, lgcr,
                           #   nooga, Clojure, jank-test-suite, WASM, sixel, qmd
  ideas/                   # roadmap & speculative: nREPL-in-browser,
                           #   bytecode→Go translation
  projects/                # USAGE case studies (using let-go in anger):
                           #   xsofy, lgx, let-go-lab
  sources/                 # one page per ingested source repo + key external docs
  references/              # OKF-style reference docs minted by enrich pass 2
                           #   (clojure-compat, transducers, interop rules, …)
  tools/
    viz/                   # vendored OKF viewer (generator.py + viz.html template)
    letgo_source.py        # LetGoSource: enumerate concepts from repos + runtime
    build_site.py          # render canonical markdown → styled GitHub Pages site
  site/                    # generated static site output (gitignored or gh-pages)
  docs/superpowers/specs/  # this spec and future ones
```

The user's two branches map onto existing llm_wiki dirs rather than inventing
top-level dirs: **developing let-go → `concepts/`**; **using let-go →
`projects/` + `entities/`**. Only `references/` is added, matching OKF.

## 5. Source catalog

| Source | Repo | Role in wiki |
|---|---|---|
| let-go | github.com/nooga/let-go (local `~/development/let-go`) | The language/VM. Feeds `concepts/` (internals) and `entities/let-go`, plus the stdlib API in `concepts/`/`references/`. |
| xsofy | github.com/nooga/xsofy (local `~/development/xsofy`) | A roguelike written *in* let-go. `projects/xsofy` — usage case study, idioms, WASM. |
| let-go-lab | github.com/mparrett/let-go-lab | Sixel/terminal-graphics/WASM experiments on let-go. `projects/let-go-lab`. |
| lgx | github.com/abogoyavlensky/lgx | Git-based package/project manager for let-go (`lgx.edn`: deps/run/test/build/scaffold). `projects/lgx` + `entities/lgx`; the "how to manage a let-go project" story. |

External doc seeds (for enrich pass 2): let-go README, clojure.org /
clojuredocs (compat semantics), the jank clojure-test-suite, nooga's posts.

## 6. Maintenance tooling

The "strong skills and tooling" requirement. Bookkeeping is owned by tools, not
hand edits (per `llm_wiki.md`: hand-editing index/log/manifest is *not* the path).

- **`llm-wiki` CLI** (`~/pkm/llm_wiki.py`, run via `uv run` from `~/pkm`):
  `page register`, `index entry`, `log close-session`, `manifest show`. Wire
  this new repo as an `llm-wiki` project (config/path) so the CLI maintains its
  `index.md` / `log.md` / manifest. Verify subcommands with `--help` first;
  fall back to direct markdown ops if a case isn't covered.
- **`~/pkm/.claude/skills/wiki/*`**: reuse `wiki-check-name.py` (name-collision
  guard — run before every new page), `wiki-doctor.py` (health/lint),
  ingest/lint/query skill docs.
- **Root `AGENTS.md`** (canonical, model-agnostic) + **`CLAUDE.md`** (pointer):
  instruct agents here to (a) maintain via the CLI + wiki skills, (b) follow the
  harmonized frontmatter, (c) run the enrich discipline (§7) when authoring,
  (d) never hand-edit index/log. Written once in `AGENTS.md` so Claude, Codex,
  Cursor, Gemini, etc. all share one schema.
- **qmd** (optional): hybrid BM25/vector search + MCP server; kicks in past a
  few hundred pages. `llm-wiki index update` wraps it.
- **Vendored OKF visualizer** (`tools/viz/`): copy
  `okf/src/reference_agent/viewer/{generator.py, templates/viz.html}` (no GCP
  deps) + a thin wrapper. Regenerates `viz.html` — a self-contained
  force-directed graph — restyled with the let-go house style (§8). Our dual
  frontmatter makes every page OKF-conformant, so it works unmodified.

## 7. Authoring engine — `enrich`, recast for let-go

Google's `enrich` is a **source-pluggable, two-pass, guardrailed
knowledge-authoring loop**. We drop its ADK/Gemini/BigQuery code and reuse its
*shape* and *prompt discipline*, re-expressed in our stack. The `Source` ABC is
the seam where "Google-specific" lived; we replace it with `LetGoSource`.

### Pass 1 — structured pass (system-of-record → one doc per concept)

`LetGoSource` (`tools/letgo_source.py`) enumerates typed concepts from **the
repos + the running `let-go` runtime**:

| enrich (`Source`) | `LetGoSource` |
|---|---|
| `list_concepts()` → BQ tables/datasets | namespaces (`Namespace`), functions/macros/special-forms (`Function`/`Macro`/`Special Form`), Go-interop bindings (`Go Interop`), internal packages `pkg/vm`,`pkg/compiler` (`Package`), example programs (`Project`) |
| `read_concept()` → schema metadata | arglists + `:doc` docstring (let-go carries Clojure-style var metadata) + source location |
| `sample_rows()` → query the table | **eval the form in the `let-go` REPL** and capture real output |

Per concept, a **Claude subagent** (adapted `reference_instruction.md`) reads
any existing doc (refine, don't rewrite), reads raw metadata, evals a sample,
sees siblings for cross-linking, and writes exactly one doc:
prose "grain" → `# Signature` → `# Examples` (real REPL transcripts) →
`# Citations`. Writes go through the `llm-wiki` CLI (`page register`,
`index entry`) which regenerates index/log.

**Eval backend for `# Examples` (live REPL, v1):** v1 shells out to the
`let-go` binary to evaluate example forms and capture real output, each eval
sandboxed with a timeout; a failed/hanging eval is recorded as
"example errored" rather than blocking the doc. **Forward upgrade:** migrate to
**nREPL** once the in-progress nREPL effort on let-go proper lands — a
persistent session (evaluate many forms without per-call process spawn) with
structured values/stdout/error streams. The wiki does **not** block on nREPL;
it's a soft dependency tracked in `ideas/nrepl` and swapped into `LetGoSource`
behind the same sampling interface when ready.

The initial population ("parallel agents, one per repo") **is** pass 1: dispatch
read-only Claude subagents over let-go, xsofy, let-go-lab, lgx.

### Pass 2 — web/docs pass (crawl curated docs to enrich)

A Claude subagent (adapted `web_ingestion_instruction.md`) self-crawls from
seed URLs under **hard guardrails** (max-pages, allowed-hosts, path-prefixes,
denied-substrings, max-depth). Per page it routes to: **enrich** an existing doc
(strict augmentation — preserve every existing heading, add alongside),
**mint** a `references/<slug>` doc (only past the **four gates**:
referenceable-by-name, not-meta, citation-test, reuse-test — bias to skip), or
**skip**. Guardrails are enforced in the fetch wrapper (our `WebFetch`), not
just the prompt.

**let-go-shaped "must-capture" extractions** (the analog of enrich's
metric/dimension/join extractions that bypass the gates):

- **Clojure-compat notes** — where let-go diverges from Clojure JVM →
  `references/clojure-compat/<slug>.md`, cited from affected function docs.
- **Interop rules** — Go↔let-go calling conventions → `references/interop/…`.
- **Known limitations / edge-cases** — the README's "Known limitations" and
  failing test-suite cases → `references/limitations/…`.

### What's actually reused vs. rebuilt

- **Reused (ported near-verbatim):** the four-gate reference test, the strict
  augmentation rules, the crawl-guardrail model, the OKF doc shape, the
  `viz.html` viewer.
- **Rebuilt for let-go:** `LetGoSource` (repo walk + REPL introspection), the
  two prompts recast SQL→Clojure, Claude subagents in place of ADK agents,
  writes through the `llm-wiki` CLI.

## 8. Published surface — styled GitHub Pages site

Primary human-facing surface (user preference: a `github.io` site, not a pure
wiki). `tools/build_site.py` renders the canonical markdown → a static site
deployed to GitHub Pages.

**House style** — matched to let-go's own published page (`let-go/wasm/index.html`):

```css
--serif: "Boldonse", "Iowan Old Style", Georgia, serif;   /* display/headings */
--mono:  "JetBrains Mono", ui-monospace, "SF Mono", Menlo, monospace; /* body/code */

/* light (warm off-white) */
--bg:#f4ecdb; --fg:#1d180f; --muted:#877a5e; --rule:#d6c8a8; --accent:#b45309;
--term-bg:#1a1610; --term-fg:#ede1c4; --term-cursor:#f5b041;
/* dark */
[data-theme=dark]: --bg:#1a1610; --fg:#ede1c4; --muted:#7a6d52; --rule:#34291c; --accent:#f5b041;
```

Fonts via Google Fonts (`Boldonse`, `JetBrains Mono`); light/dark toggle with
`prefers-color-scheme` + `localStorage`, same as let-go's page. The vendored
`viz.html` graph is restyled with the same tokens and embedded/linked from the
site.

**Generator (recommended: MkDocs Material)** — rationale: Python (matches the
`llm-wiki`/viewer toolchain), trivial GitHub Pages deploy, custom CSS via
`extra_css` for the house tokens, built-in client-side search, nav derived from
the directory tree, frontmatter-aware. Alternative considered: **Hugo** (Go
affinity with let-go, hand-rolled templates for pixel-exact parity with
let-go's page) — more control, more work. *Decision point for review.*

Frontmatter is consumed by the generator (title/description/tags/nav) and not
shown as raw text. Relative `.md` links (§3) resolve directly.

**Runnable examples (WASM REPL playground):** let-go compiles *itself* to WASM,
and its published page already embeds an xterm.js + WASM REPL terminal. The site
reuses that widget so `# Examples` code blocks are **runnable in-browser** —
static REPL transcripts by default (from §7 sampling), with a "Run" affordance
as a progressive enhancement that boots the let-go VM in WASM and evaluates the
form live. This directly matches let-go's own published-page tech and advances
the roadmap item *nREPL in the browser (let-go VM in WASM)*. Phase-2 relative to
first content; the static transcripts stand alone without it.

**What the site publishes:** only the wiki-content dirs — `concepts/`,
`entities/`, `ideas/`, `projects/`, `sources/`, `references/` — plus `index.md`
(landing). **Excluded from the rendered site** (machinery / internal process
docs, but still git-tracked for contributors): `docs/superpowers/` (design
specs & plans), `tools/`, `_meta/`, `.claude/`, `AGENTS.md`/`CLAUDE.md`. The
generator's `docs_dir`/`nav` is scoped to the content dirs so process artifacts
never leak into the published output.

## 9. Build sequence (this session)

Per user choice, scaffold **and** generate in this session.

1. `git init` the repo; create dirs (§4); write `_meta/taxonomy.md` (fresh
   let-go tags: `clojure`, `lisp`, `vm`, `bytecode`, `compiler`, `go`, `wasm`,
   `interop`, `stdlib`, `roguelike`, `tooling`, plus type tags), `index.md`,
   `log.md`, root `AGENTS.md` (canonical) + `CLAUDE.md` pointer.
2. Wire the `llm-wiki` CLI to this repo as a project; verify `--help`.
3. Vendor the OKF viewer into `tools/viz/`; restyle `viz.html` with §8 tokens.
4. Implement `LetGoSource` (pass-1 enumeration + live REPL sampling via `let-go`
   binary shell-out, sandboxed with timeouts).
5. **Pass 1:** dispatch parallel read-only Claude subagents (one per repo:
   let-go, xsofy, let-go-lab, lgx) drafting `entities/`, `concepts/`,
   `projects/` pages (`status: speculative`, `resource`/`sources` cited),
   writing through the CLI.
6. **Review pass:** validate drafted pages against actual code/runtime; promote
   accurate ones to `status: stable`. Run `wiki-check-name.py` on every new page
   and `wiki-doctor.py` for health.
7. **Pass 2 (optional this session):** docs crawl to enrich + mint `references/`.
8. Build `tools/build_site.py` (MkDocs Material scaffold + house-style CSS);
   generate `site/`; regenerate `viz.html`.
9. Regenerate `index.md`, append `log.md`, commit.

## 10. Risks / open decisions

- **`llm-wiki` CLI multi-project support** — confirm it can target a repo
  outside `~/pkm/wiki`. If not, either point `WIKI` config at this repo or fall
  back to direct markdown ops (always safe).
- **REPL sampling** — DECIDED: live REPL in v1. Backend = `let-go` binary
  shell-out now (sandboxed with timeouts; failures captured as "example
  errored"), upgrading to **nREPL** when that effort lands. Soft dependency,
  non-blocking (`ideas/nrepl`).
- **WASM playground** — Phase-2 progressive enhancement reusing let-go's
  existing WASM REPL widget; confirm licensing/vendoring of that widget from the
  let-go repo when we build it.
- **Accuracy of agent-drafted pages** — mitigated by `status: speculative` gate
  + mandatory review before `stable`; every page cites `resource`.
- **Static-site generator choice** — MkDocs Material (recommended) vs Hugo;
  confirm at review.
- **Name collisions** — flat-ish page slugs across dirs; `wiki-check-name.py`
  before each new page.

## 11. Success criteria

- `~/development/let-go-wiki` is a git repo with the §4 structure, a fresh
  taxonomy, and CLI-maintained `index.md`/`log.md`.
- ≥1 accurate `stable` page per source repo, each citing its `resource`.
- `viz.html` renders the graph in the let-go house style.
- `tools/build_site.py` produces a styled GitHub Pages site (fonts/colors match
  let-go's published page) with working nav, search, and relative links.
- The enrich discipline (four gates + augmentation rules) is captured in
  `AGENTS.md` (with `CLAUDE.md` pointing to it) so future authoring stays
  consistent across any coding agent.
