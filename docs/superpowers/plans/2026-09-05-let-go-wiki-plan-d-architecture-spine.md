# let-go-wiki — Plan D: Architecture spine + compiler-architecture capture

**Goal:** Fill the missing major architectural pieces of let-go as `concepts/`
pages, then capture the compiler-architecture work that landed on
`nooga/let-go` in July–September 2026 (mostly nnunley's PRs and epics) as
concepts, ideas, and sources. Every claim cites a public source (PR, issue,
or a file on `origin/main`), and pages are promoted to `stable` only after
checking against the code at a named SHA.

**Where we start (2026-09-05):** 73 pages, 179 links. Concepts cover the
VM, IR pipeline/passes/optimizations, values, exec context, runtime image,
interop, wasm, pods, nREPL. Nothing covers: the reader, namespaces/vars, the
`//lg:native` primitive surface, the three compile paths and their fallback
semantics, generated artifacts, the perf ratchet, the shipped Go backend,
the op catalog, structurize, block interface/liveness, bytecode lowering,
or the proposed `lg.compiler` namespace architecture. Five concept pages are
still `speculative`. The graph shows the gap: the compiler cluster is a ring
of six nodes around `ir-pipeline`, with nothing between "IR" and "Go".

## Global constraints

- **Public sources only.** Cite PRs/issues (`nooga/let-go#NNN`), files on
  `origin/main`, and `docs/**` on `origin/main`. Never cite a local path,
  a gitignored `docs/superpowers/**` file, or private conversation.
  `check_wiki` already rejects the second; the other two are on the author.
- **Pin the SHA.** `sources:` entries for code claims take the form
  `repo: nooga/let-go <path> @ <short-sha>, YYYY-MM-DD`. When `origin/main`
  moves, the pin says what the page was true of.
- **Executable claims get executed.** Where a claim can be demonstrated with
  `lg -e` (a dynamic var's default, a fallback message, a census row), the
  page shows the real output, per the population runbook.
- **Stable means checked, not written.** Drafts start `speculative`; an
  adversarial review pass (the runbook's step 6) promotes them. The reviewer
  re-reads the cited file at the pinned SHA, not the PR body.
- **Sources layer stays in step.** Each ingested PR cluster, issue, or doc
  gets a `sources/` page with a Derived-pages section, as the 2026-07-03
  layer established.
- **Follow the runbook mechanics** for authoring, gating, index/log
  bookkeeping, and publish
  (`docs/superpowers/runbooks/population-sprint.md`).

## Staleness first (before adding pages)

`origin/main` moved roughly 200 commits since the concept pages were written
(2026-07-01..06). Two changes are known to invalidate existing text:

- [x] `.lgb` format: `lg --version` on `main` reports
      `lgb: format 2 (default write), 3 (max)`, and #624 split debug info
      out of emitted bytecode (merged 2026-09-04). Re-verify
      `concepts/lgb-bytecode-format.md` (titled "v2") and
      `concepts/debug-info.md` against `pkg/vm` at the pinned SHA.
- [x] `//lg:native` hoist (#639/#640): pages describing core primitives as
      inline closures in `lang.go` are wrong now. Grep concepts for
      `lang.go` / `installLangNS` and fix.
- [ ] Run `lgx enhance` and work its "Needs review (LLM)" list for the five
      speculative concepts (`ir-optimizations`, `debug-info`,
      `deftype-and-protocols`, `go-structs`, `nrepl-server`): promote or fix.

## Batch 1 — the architecture spine (7 concepts)

Each is a `Concept` page with a mermaid diagram where there is a pipeline,
a "How to observe it" section (`lg -e` / `make` targets), and citations.

- [x] `concepts/reader.md` — `pkg/compiler/reader.go`: reader macros, `:lg`
      conditionals, set literals (#736), tagged/data readers (#770), raw Go
      fragments (#768). Mark in-flight PRs as such; do not describe unmerged
      behaviour as current.
- [x] `concepts/namespaces-and-vars.md` — vars, roots vs dynamic bindings
      (link `concurrency-model`), lazy var metadata (#781, open), the
      core-shadow warning (#734, open), alias resolution (#610, #548).
- [x] `concepts/native-primitives.md` — the `//lg:native` / `//lg:ns` /
      `//lg:bind` annotation surface, `lgprimgen` and per-package registrars
      (#639, #640, #654), contribute vs own mode, direct-call natives for the
      hot `clojure.core` surface (#613), what `native-prims-intact?` gates.
- [x] `concepts/compile-paths.md` — the three ways a form runs: the direct
      bytecode compiler (`pkg/compiler`), the IR path (`*ir-compile*` →
      `ir.lower` → bytecode), and the Go path (`lower_go`, `gogen_ir` tag).
      Fallback semantics and `*ir-compile-strict*`; the census numbers from
      #580 (70.7% bytecode-path vs 99.5% Go-path coverage at that date) as a
      dated measurement, not a permanent fact. Cross-link `ir-pipeline`.
- [x] `concepts/generated-artifacts.md` — `core_compiled.lgb`,
      `core_go_lowered/`, `generated.sums`, the provenance manifest and
      selective regeneration (#641), `make generate` / `check-generated`,
      the `bootstrap` tag universe and gogen's auxiliary embed (#557).
      Source: `docs/regenerating-generated-artifacts.md`.
- [x] `concepts/perf-ratchet.md` — anchor-relative benchmark ratchet
      (`docs/perf/ratchet.md`), `baseline.json`, the IR-stress and
      lowering-shape ratchets (#579, #580), pre-push gate and deterministic
      rebaseline (#780), bench-baton (#795, open), the #791 regression as
      the worked example of what the ratchet catches.
- [x] `concepts/go-backend.md` — the shipped Go backend as distinct from the
      `sources/design-go-aot-backend` proposal: `gogen`, `lower_go.lg`,
      `entry_frame.lg` and `--entry-frame` binaries (#729, #783 open),
      `lg-runtime` / `lg_no_http` (#652, #658), and how `lg-compile.md`
      drives it. Enhance `lg-compile.md` to link here instead of duplicating.

## Batch 2 — compiler architecture (nnunley's work)

- [x] `ideas/compiler-namespace-architecture.md` — the `lg.compiler` /
      `lg.compiler.ir.*` / `lg.compiler.backend.go` / `lg.commands.compile`
      proposal (#786): the seams it names (`ir.*`, `gogen`,
      `scripts/lg-compile`, #735's `lg.aotdriver`), the migration order, and
      the acceptance criteria. Status `active` as a proposal; it becomes a
      concept only when namespaces move.
- [x] `concepts/op-catalog.md` — `ops.lg` as the single source of op facts:
      the generated `OpByKeyword` switch (#612), `form_heads.lg` and the
      load-time coherence check (#667), per-op `needs-rt?` contribution
      rules (#666), fn-shape accessors (#712). The design rule these share:
      a fact lives in one catalog column and every consumer queries it.
- [x] `concepts/structurize.md` — the target-independent control tree
      (`:if`/`:loop`/`:seq`/`:break`/`:continue`/`:return`/`:tail`/`:goto`),
      which backend consumes it today and which does not, the `:try` gap,
      keyword-cond → Go switch (#675 open, #674). Source: #574.
- [x] `concepts/block-interface-and-liveness.md` — block args as the stack
      VM's accommodation for missing locals, `passes/liveness.lg` and
      `blockarg.lg`, the single-value resolver, `check-cross-block!`, the
      measured cost (DUP shuffle ≈ 67% of a 2× instruction bloat on
      branch-heavy code, 2026-07-18). Source: #575.
- [x] `concepts/bytecode-lowering.md` — `lower.lg` from low CFG to stack
      bytecode: junk-below accounting and block-junk agreement, RPO block
      order and deferrable-branch guards (#648), tail-call fusion (#649),
      the def+name* seam (#647), var-load re-emission (#579). This is the
      page that sits between `ir-pipeline` and `stack-vm` in the graph.
- [x] `ideas/ir-representation-roadmap.md` — EPIC-017 (#574) and EPIC-018
      (#575) as one roadmap page: the six ranked physical-layout findings,
      the story ledger with done/pending, the sequencing gate. Link #620
      (constant-space tail calls) and #519 (more of let-go in let-go).
- [x] `sources/` — one page each: `issue-786-compiler-namespaces`,
      `epic-574-ir-normalization`, `epic-575-block-interface`,
      `design-ir-dynamic-vars` (#555; the design doc exists on main but has
      no source page), `docs-perf-ratchet`,
      `docs-regenerating-generated-artifacts`, `pr-native-hoist-stack`
      (#627→#639→#640→#641), `pr-catalog-dispatch` (#612/#666/#667/#712),
      `pr-ir-lowering-seams` (#579/#580/#647/#648/#649),
      `pr-native-entry-gate` (#729).

## Progress (2026-09-05)

Batch 1 authored and reviewed (all seven stable). Batch 2 authored (review pending at time of writing). Sources layer: 11 pages. Remaining: the `lgx enhance` promotion of the older speculative pages (`ir-optimizations`, `deftype-and-protocols`, `go-structs`, `nrepl-server`), and the graph regeneration once the viz PR and this branch both land. Per-batch log entries are in `log.md`.

## Batch 3 — map and graph

- [x] `index.md` MOC: add a "Compiler architecture" line
      (`compile-paths` → `op-catalog` → `structurize` →
      `bytecode-lowering` / `go-backend`) and "Build & measure"
      (`generated-artifacts` · `perf-ratchet`). Catalog entries for every
      new page.
- [ ] Regenerate `viz.html`; confirm the compiler cluster now has a spine
      (`ir-pipeline` should no longer be the only hub between IR and Go).
- [ ] `log.md` ingest entries per batch; `lgx doctor` green; site builds
      `--strict`.

## Execution notes

- Author one page per subagent from a brief that names the pinned SHA, the
  files to read, the PRs to cite, and the sibling pages to link, per the
  runbook. Review with a second subagent that re-reads the code, not the
  brief. Two agents per page is the budget; do not fan out further.
- Batch size four to five pages per session; each batch ends with the gate,
  the review, the bookkeeping, and a push.
- Where a PR is open, the page says so and describes the merged state only.
  Re-check open PRs (#768, #770, #781, #734, #675, #795, #783) at the start
  of each session; several will have merged.

## Landing plan (2026-09-05): branches by confidence

Everything above was authored on one working branch. It lands as slices,
grouped by how confident we are that the page is both accurate and ours to
write. Accuracy is the adversarial review (a second agent re-reading the code
at the pinned SHA); ownership is whether the page restates someone else's
in-flight work.

| Slice | Branch / PR | Contents | Confidence | Action |
|---|---|---|---|---|
| 1 | `viz/graph-legibility`, PR #9 | graph viewer | high (tooling only) | land |
| 2 | `content/lgb-reverify` | `.lgb` format, debug-info, their sources page | high (Matt's own PRs, code he wrote) | land |
| 3 | `content/architecture-spine` | reader, namespaces-and-vars, native-primitives, compile-paths, generated-artifacts, perf-ratchet, go-backend; five sources pages; this plan | high on accuracy; two pages note code comments that are ahead of the code (guarded-root fast path not consulted by emitted call sites; the single-arity comment on `*ir-compile*`) | land, with a note to Norman about those two observations |
| 4 | `content/compiler-architecture` | op-catalog, structurize, block-interface-and-liveness, bytecode-lowering, plus the two roadmap ideas (`compiler-namespace-architecture`, `ir-representation-roadmap`) and their four sources pages | medium: accurate (two findings on review) but restates Norman's PRs and open proposals in our words | discuss with Norman first; land `active`, let him promote or rewrite |

Slice 4 carries the idea pages because the four concepts link to
`ideas/ir-representation-roadmap`; splitting them means breaking those links.
If Norman wants only the concepts, relink and drop the ideas.

Rules that carry forward: pages start `speculative`, one adversarial review
per batch promotes; public sources only, SHAs pinned in `sources:`; the root
`viz.html` snapshot is regenerated after PR #9 and the content slices have
both merged, never committed on a content branch.
