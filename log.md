# let-go-wiki Log

## [2026-07-05] expand | concept: Stack VM
Fleshed out concepts/stack-vm from stub to full internals page, authored from pkg/vm/vm.go
(opcode table, CodeChunk bytecode encoding, Frame, Frame.Run dispatch loop, specialized
arithmetic fast-paths, frame pooling, recur/tail-call/exception handling, debug info). All
four examples verified with `lg -e` (3, 7, 10, 15). Promoted to stable.

## [2026-07-01] init | scaffold
Created repo structure, taxonomy, schema docs (AGENTS.md/CLAUDE.md), and seed pages.

## [2026-07-01] build | tooling foundation
Added validator, restyled OKF viewer, MkDocs house-style site, lgx tasks, Pages CI.
Built viz.html and site/ from the two seed pages.

## [2026-07-02] ingest | stdlib batch 1 (5 concepts)
Authored references/clojure.core/{apply,fn,let,when,defn} with real `lg -e` examples;
accuracy-reviewed (all examples verified) and macro signatures corrected to usage form. Promoted to stable.

## [2026-07-02] ingest | concept: Indexed-RPN IR
Authored concepts/indexed-rpn-ir (developing-let-go internals) from pkg/ir/op_generated.go + ir_ops.lg.
Documents the indexed-RPN (SSA-equivalent, NOT SSA) encoding + block-parameter control flow; external refs
(Burak Emir, Carbon sem_ir, Swift SIL/Cranelift/MLIR). All 9 ops verified real. Promoted to stable.

## [2026-07-02] ingest | project: xsofy
Authored projects/xsofy (using-let-go case study) from the xsofy README — browser+terminal roguelike whose
magic system is a Lisp; persistent data structures, WASM, no deps, ~6ms startup. Promoted to stable.

## [2026-07-02] ingest | stdlib batch 2 (6 concepts)
Authored references/clojure.core/{map,filter,comp,inc,mapv,partial} with real lg -e examples;
accuracy-reviewed (all 18 examples verified), promoted to stable. Published stdlib coverage: 11.

## [2026-07-02] ingest | breadth batch (4 projects + 3 internals)
Authored projects/{lgcr,lgx,legmacs,let-go-lab} (README-grounded) and
concepts/{bytecode-compiler,wasm-compilation,go-interop} (from let-go source).
Accuracy-reviewed (6/7 clean; legmacs line-count corrected to ~4,000). Promoted to stable.

## [2026-07-02] ingest | internals deep-dive (lginterop / lg-compile / IR pipeline)
Authored concepts/{lginterop,lg-compile,ir-pipeline} — usage-first (let-go primary, Go reference):
lginterop (wrapping Go pkgs to call Go FROM let-go), lg-compile (AOT to Go packages), the IR framework
(written in let-go). Cited .lg/README sources. Promoted to stable.

## [2026-07-02] ingest | ideas (roadmap)
Authored ideas/{nrepl-in-browser,bytecode-to-go-translation,clojure-at-your-go-dayjob} from let-go's
README Goals (unchecked roadmap). Speculative by nature (unbuilt); cross-linked to existing concepts.

## [2026-07-02] ingest | design-doc capture (9 pages)
From ~/development/let-go/docs: concepts value-representation, exec-context, io-host-decoupling,
runtime-image, type-inference, pods; references/clojure-compat; ideas malli-on-let-go, self-hosting-aot.
Grounded in docs/design + docs/guide + shareable superpowers analyses. Concepts/ref → stable; ideas speculative.

## [2026-07-02] ingest | Tier-1 design capture via multi-agent workflow (7 concepts)
Authored + adversarially source-verified: concurrency-model, deftype-and-protocols, lgb-bytecode-format,
debug-info, go-structs, ir-passes, ir-optimizations. Workflow verify pass caught faithfulness/framing
defects in 4/6 auto-verified pages; fix pass repaired them. ir-passes verified separately (schema retry).
Sources: docs/superpowers/specs/* (gitignored — cited by local path) + public pkg/rt/core/ir/passes/*.lg impls.

## [2026-07-03] ingest | Tier-2 roadmap capture via workflow (5 pages) + nrepl backlink
Authored + Opus-4.8-adversarially-verified from PUBLIC docs: references/testing-conformance,
ideas/{clojurelike-refactor, jvm-compat, master-plan-roadmap}, concepts/nrepl-server (cites pkg/nrepl/server.go).
Opus verifier flagged framing/faithfulness issues on all 5; fix pass repaired all (remaining []).
Repointed ideas/nrepl-in-browser's "nREPL Server" link to the new concepts/nrepl-server page (was stale → stack-vm).

## [2026-07-03] lint | fix non-public citations + harden check_wiki
Repaired 8 dead let-go GitHub URLs across 4 pages (exec-context, type-inference, bytecode-to-go-translation,
nrepl-in-browser): gitignored docs/superpowers/* and guessed/nonexistent paths → real public sources
(pkg/vm/exec_context.go, pkg/vm/binding_stack.go, pkg/rt/core/ir/lower_go.lg + passes/typeinfer.lg,
pkg/compiler, pkg/nrepl/server.go, wasm/main.go). Added check_wiki rule: flag github.com/nooga/let-go URLs
under gitignored prefixes (docs/superpowers/, CI-safe) + optional missing/ignored-path check vs a local
let-go checkout. +5 tests (50 total).

## [2026-07-03] update | viz upgrade, top-bar nav, mermaid diagrams
Bumped cytoscape 3.28.1->3.34.0 + added fcose force layout (declutters the graph); fixed marked 12->18
UMD path. Put Graph + sections on a sticky top bar (navigation.tabs). Enabled mermaid diagrams via
pymdownx superfences custom fence (sentinel-swapped python/name tag in build_site); added a pipeline
flowchart to concepts/bytecode-compiler. Browser-verified: labels legible, fcose spread, tabs, diagram render.

## [2026-07-03] fix | render mermaid in the viz detail panel
The graph detail panel renders page markdown via marked, which left ```mermaid as raw code.
Added mermaid@11.16.0 to viz.html + a renderMermaid() pass (theme-matched, securityLevel loose) that
converts code.language-mermaid blocks to rendered SVG after each panel populate. Browser-verified.

## [2026-07-03] ingest | sources/ provenance layer (21 pages) + curated overview
Populated sources/ (one page per ingested source: README, codebase map, 8 design docs, 4 guides,
4 roadmap docs, 3 external IR refs), each with a Derived-pages backlink section, authored + adversarially
verified (external refs Opus-verified — caught 2 bad resource URLs + fabrication, fixed). Rewrote index.md:
curated altitude-grouped Map of Content on top (human path) + full flat catalog below (LLM retrieval path),
now including the Sources section. Graph: 49 -> 70 nodes. Sources tab now on the top bar.

## [2026-07-05] lint | well-formedness audit + check_wiki hardening
Audited all 70 pages (frontmatter validity, balanced fences, dup keys, date formats, placeholders):
only issue was 5 pages with unquoted dates (parsed as YAML date objects) — quoted them. Hardened
check_wiki with well-formedness gates: status/category controlled vocab, created/updated must be
quoted YYYY-MM-DD strings, no duplicate frontmatter keys, single-line title/description, balanced
code fences. +7 tests (59 total).

## [2026-07-05] ingest | focused lgx import (usage + compilation, 4 pages)
From a clone of abogoyavlensky/lgx (README + docs/ARCHITECTURE, branch master): expanded projects/lgx
(hub; noted lgx is itself written in let-go), added references/lgx-commands (new/run/repl/build/test),
references/lgx-edn (lgx.edn config: paths/main/lg-version/deps/tasks/contexts), and concepts/lgx-build-model
(git dep resolution + how build/run drive let-go compilation). Adversarially verified — caught invented flags
+ overstated compilation claims, fixed. Surfaced lgx in the MOC Build & run line. Graph 70 -> 73 nodes.

## [2026-07-06] tooling | add `enrich enhance` (existing-page improvement driver)
Built tools/enrich/enhance.py (+ lgx enhance task): scores existing pages on structural deficits
(thin body, no outbound/inbound links, no citations, still speculative) and writes briefs splitting
mechanical fixes from a "Needs review (LLM)" worklist (promotion/staleness/grounding/contradiction).
Includes a no-regression guard (regressed(): a re-authored page must not lose citations/sections),
mirroring the Google OKF driver's completeness guardrail + llm_wiki's Lint suggestions. +6 tests (65 total).
On the current wiki it flags 36/73 pages (thin stdlib refs, an uncited source page, speculative nrepl-server).
