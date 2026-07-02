# let-go-wiki Log

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
