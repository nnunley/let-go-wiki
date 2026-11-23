---
type: Concept
category: concept
title: "Type Inference and the Type Cache"
description: "How the let-go compiler infers types during IR lowering, why the Go lowering step moved from a wall-clock budget to an unbounded fixpoint run (with a drain-count bound on other callers), and the proposed mergeable type cache for parallel lowering."
tags: [compiler, bytecode, runtime]
resource: "https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/docs/design/parallel-lowering-and-type-cache.md"
sources: ["design: parallel-lowering-and-type-cache.md, 2026-06-05", "repo: nooga/let-go docs/design/parallel-lowering-and-type-cache.md pkg/rt/core/ir/passes/typeinfer.lg pkg/rt/core/ir/lattice.lg pkg/rt/core/ir/passes/pipeline.lg pkg/rt/core/ir/lower_go.lg pkg/rt/core/core.lg pkg/rt/parallel.go pkg/rt/lang.go pkg/vm/var.go cmd/lgbgen/main.go Makefile @ b82588292b, 2026-10-20"]
created: "2026-07-02"
updated: "2026-10-20"
status: stable
---

# Type Inference and the Type Cache

The let-go compiler runs a type-inference pass (`typeinfer`) during IR lowering. The pass fills in `Inst.Type` for downstream optimizations ([typeinfer.lg](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/core/ir/passes/typeinfer.lg), header comment). When a function's input and return types are known, lowering can emit direct dispatch instead of generic calls. The design note records the Go lowering step (`lgbgen --target=go`) at about 3 minutes, the slowest step of the bootstrap, with type inference as one stage of the per-function work ([design note](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/docs/design/parallel-lowering-and-type-cache.md)).

The design note proposes a **mergeable type-discovery cache** so that parallel lowering is both fast and deterministic. The cache is not in the source at b82588292b. The sections below separate what is implemented from what is proposed.

## Status at b82588292b

| Item | Status | Where |
|---|---|---|
| Wall-clock typeinfer budget | Removed. Replaced by a drain-count bound | [typeinfer.lg](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/core/ir/passes/typeinfer.lg#L476-L483) |
| Go-lowering path runs typeinfer to fixpoint | Implemented | [pipeline.lg](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/core/ir/passes/pipeline.lg#L1573) |
| Atomic gensym counter | Implemented | [lang.go](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/lang.go#L816-L819) |
| Lock-free `Var.Deref` (atomic root) | Implemented | [var.go](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/vm/var.go#L42) |
| `pmapv` (eager, synchronous parallel map) | Implemented. Not used by Go lowering | [parallel.go](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/parallel.go#L18), [lang.go](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/lang.go#L3944) |
| Gensym-suffix canonicalization in emitted names | Implemented | [lower_go.lg](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/core/ir/lower_go.lg#L497-L524) |
| Sorted native imports | Implemented | [pipeline.lg](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/core/ir/passes/pipeline.lg#L1823) |
| Mergeable type-discovery cache (keys, join-merge, fixpoint driver, committed artifact) | Not implemented. No cache code found | (proposal in the design note) |
| Lowering that reads a converged cache | Not implemented | (proposal in the design note) |

## The Lowering Challenge

The file rule for `pkg/rt/core_go_lowered/ir/lower_go/lower_go.go` runs `go run -tags bootstrap ./cmd/lgbgen --target=go` ([Makefile](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/Makefile#L162)). `make generate` ([Makefile](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/Makefile#L172-L173)) runs `scripts/generate.lg`, which runs `go run -tags bootstrap ./cmd/lgbgen --target=both` when the bundle or the lowered tree is stale ([generate.lg](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/scripts/generate.lg#L190)). `runGoTarget` ([lgbgen main.go](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/cmd/lgbgen/main.go#L882)) is called from the dispatch at [main.go#L596](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/cmd/lgbgen/main.go#L596) and [main.go#L607](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/cmd/lgbgen/main.go#L607). It collects the defn forms of every embedded namespace that is not marked `lgbgen:skip-go`, then lowers them in one call to `lower-all-ns-to-go` ([pipeline.lg](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/core/ir/passes/pipeline.lg#L2006)), a wrapper that calls `lower-all-ns-to-go-result` ([pipeline.lg](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/core/ir/passes/pipeline.lg#L1953)). That function runs two phases, collect and then emit, and both phases use `mapv`, which is sequential ([pipeline.lg](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/core/ir/passes/pipeline.lg#L1969-L1996)).

The per-function work is `expand → build IR → optimize → type-infer → lower → emit`. Each function's work is independent of the others. Type inference creates two problems for parallel execution.

### Problem 1: Wall-Clock Budget Non-Determinism

The design note describes the earlier typeinfer design. Type inference used a wall-clock budget. When the budget ran out, the function returned a sound lower bound in the type lattice, a partial result. Under parallel load, each call got less wall time, bailed sooner, and returned less type information. The design note calls the wall-clock budget the root cause of the remaining non-determinism ([design note](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/docs/design/parallel-lowering-and-type-cache.md), section 3). The budget's numeric value is not recorded at b82588292b.

At b82588292b the wall-clock budget is gone. typeinfer bails on a drain count instead. `*typeinfer-max-drains*` defaults to 2,000,000 and counts worklist drains ([typeinfer.lg](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/core/ir/passes/typeinfer.lg#L476-L483)). The source states that a drain count does not depend on machine speed or load, so a bail point is a function of the source. When the cap fires, the pass prints `typeinfer: hit *typeinfer-max-drains*` with the function name and returns the partial state ([typeinfer.lg](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/core/ir/passes/typeinfer.lg#L535-L541)).

The Go-lowering path binds the cap to `nil`, so typeinfer runs to fixpoint. The source comment gives the reason: the Go path encodes inferred types into the rendered source, and a partial, time-dependent result would change the output ([pipeline.lg](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/core/ir/passes/pipeline.lg#L1530-L1573)). The same `nil` binding appears a second time, inside `collect-ns-exports` (defined at [pipeline.lg#L1852](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/core/ir/passes/pipeline.lg#L1852)), at [pipeline.lg#L1876](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/core/ir/passes/pipeline.lg#L1876).

**A time-based budget is inherently non-deterministic under variable CPU load.** This is the design note's principle, and the drain-count bound follows it.

### Problem 2: Parallel Binding Overhead

The first attempt at parallel lowering used `pmap`. The `pmap` in core is built on `future` ([core.lg](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/core/core.lg#L2956)). Each `future` calls `SnapshotBindings` and `RunWithBindings`, which copy every active dynamic binding per spawn. A future is asynchronous and may run after the caller's `binding` scope has ended, so it must capture and reinstate that scope ([parallel.go](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/parallel.go#L18-L30)). The design note records that this spawn cost serialized the work. Its measurements on the `core` lowering were: sequential 193 s, future-based `pmap` 213 s (0.90×), `pmapv` 155 s (1.24×, about 1.9 effective cores). These figures are from the design note's 2026-05-30 investigation. They were not re-run against b82588292b.

Two changes address this:

- **Lock-free `Var.Deref`.** The root binding is an `atomic.Pointer[Value]` ([var.go](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/vm/var.go#L42)). Dynamic (thread-local) bindings are not stored on the `Var`. They are held by the ExecContext binding stack ([var.go](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/vm/var.go#L37-L42)). The `Var` keeps an atomic head pointer, `rootBind`, to its ROOT-context binding chain ([var.go](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/vm/var.go#L56)). The design note reports ~670–720× faster parallel deref. That figure is not re-measured here.
- **`pmapv`.** `pmapv` is an eager, ordered, synchronous parallel map. It blocks until every element finishes, so the caller's `binding` scope stays live. Workers read the caller's bindings through the lock-free `Deref` and do not snapshot or reinstate them ([parallel.go](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/parallel.go#L18-L30)). It is registered as the `pmapv` builtin ([lang.go](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/lang.go#L3944)).

`pmapv` is not Clojure's `pmap`. Clojure's `pmap` is lazy and chunked with bounded lookahead. `pmapv` is eager and shares the caller's dynamic bindings. Its source comment limits it to workloads whose workers only read bindings. A worker that pushes its own `binding` would race the shared binding stack ([parallel.go](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/parallel.go#L30-L35)).

## The Mergeable Type-Discovery Cache (proposed)

The design note proposes to replace the deterministic budget with a cache of type discoveries that is merged across runs. A deterministic iteration budget would give determinism but cap precision on hard functions. The cache keeps precision and removes the budget from the lowering path. The rest of this section is the proposal. None of it is implemented at b82588292b.

### Why It Is Sound

Type inference is monotone. The join of two types is the least upper bound of the two in the lattice. `join-inst-fact!` joins a new fact into an instruction's fact and returns `true` when the fact changed ([lattice.lg](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/core/ir/lattice.lg#L481-L489)). The join itself is `type-join` ([lattice.lg](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/core/ir/lattice.lg#L344-L388)). The cases of `type-join`, in the order it checks them, are:

- `:bottom` is the identity. Equal kinds join to themselves.
- A dtype kind joins with an equal dtype kind to itself. Any other pair with a dtype kind gives `:any`.
- An array kind follows the same rule. Two different array kinds, or an array against anything else, give `:any`.
- `:any` absorbs every other kind.
- `:unknown` absorbs every other kind except `:any`. The checks run in this order: dtype, array, `:any`, then `:unknown`. So `:unknown` joined with a dtype or array kind gives `:any`, and `:unknown` joined with `:any` gives `:any`.
- `:int` joined with `[:const :int 0]` gives `:int`. `:float` joined with `[:const :float 0.0]` gives `:float`.
- `:bool` joined with `:true` or `:false` gives `:bool`.
- `:int` joined with `:float` (or with a constant zero of either) gives `:number`. `:number` absorbs `:int`, `:float`, `:number`, and the two zero constants.
- Any other pair of distinct kinds joins to a `[:union ...]` form.

The lattice is not a chain. `:int` joined with `:string` gives a union, not `:unknown`. The kind order in `type-order` ([lattice.lg](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/core/ir/lattice.lg#L25-L57)) is used for ranking union members, not for the join.

The design note states that a cache entry is a point in this lattice, merging two entries is their join, and join is commutative, associative, and idempotent, so merge order does not matter. It also states that a partial run returns a lower bound, so the drain-count bail stays sound. The source comment on the cap says the same ([typeinfer.lg](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/core/ir/passes/typeinfer.lg#L476-L483)). The algebraic laws are the design note's claims. They were not checked by running code here.

### Shape and Convergence

- **Key**: a content hash of the function's IR. The design note says this is stable across runs and invalidates when the source changes.
- **Value**: the inferred signature (argument types and result type), with or without per-instruction types.
- **Merge**: per-field lattice join. Concurrent writers compare-and-join per key.
- **Convergence**: interprocedural. A function's inference improves when its callees' cached signatures improve, so the design iterates to a whole-program fixpoint. Monotonicity over a finite lattice gives termination.
- **Committed artifact**: the design note proposes committing the converged cache, as is done for the lowered tree. A sequential, unbounded "warm to fixpoint" step would produce it, and `make generate` would run that step. Lowering would then read the cache.

Current inference already uses information from declarations rather than from a cache. A self-recursive call to a function with a declared return type takes that type from `*declared-return-types*` ([typeinfer.lg](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/core/ir/passes/typeinfer.lg#L84)). Constructor types for `deftype` come from `*deftype-ctor-types*` ([typeinfer.lg](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/core/ir/passes/typeinfer.lg#L50)).

### Comparison

| Approach | Deterministic? | Full precision? | Parallel-safe? | Decouples discovery from use? | Status at b82588292b |
|---|---|---|---|---|---|
| Wall-clock budget (former) | No | Sometimes | — | No | Removed |
| Deterministic drain-count budget (current) | Yes | No when the cap fires. Go-lowering binds the cap to `nil` | Yes (design note) | No | Implemented |
| Mergeable type cache (proposed) | Yes, once converged | Yes | Yes (design note) | Yes | Not implemented |

## Why It Matters

The design note expects the mergeable cache to provide:

- **Determinism**: two lowering runs produce the same Go code, which supports reproducible builds and CI.
- **Full precision**: no permanent cap on type inference, because the cache accumulates discoveries across runs.
- **Parallel speedup**: parallel writers compare-and-join per key. The design note's `pmapv` measurement (1.24×, about 1.9 effective cores) is from its 2026-05-30 investigation, not from a cache.
- **Separation of concerns**: discovery runs as a separate, unbounded phase, and lowering reads the converged cache.

The design note describes the bootstrap as the target for this work. The cache is not present at b82588292b, so the Go lowering step still runs sequentially, with the drain-count bound on the non-Go path.

## Caveats

The design note lists these caveats for the proposal.

1. **Warmup is non-deterministic until the cache converges.** The output is deterministic only given a committed, complete cache. The design note says a cache miss in CI should fail hard and force a regeneration, instead of falling back to bounded inference.
2. **Invalidation is interprocedural.** Keying by IR hash handles edited functions. A change to a callee's signature must invalidate its callers, which requires fixpoint dependency tracking.
3. **`pmapv` lowering would share AST nodes across goroutines.** `renderFset` in [pkg/rt/gogen.go](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/gogen.go#L2311) rewrites token positions in place, under a contract that each AST is rendered once. That contract is not enforced. The design note says this is safe under the sequential `mapv` lowering. If `pmapv` lowering shares AST nodes across goroutines, concurrent renders would race on the rewrite. The design note says either to verify that no AST node is reachable from two lowering units, or to make `renderFset` copy on render.

## Implementation Phases

The design note lists four phases. Status at b82588292b:

1. **Keepers: atomic gensym and `pmapv`** (design note, Sequencing step 1). Lock-free `Var.Deref` is described in the note's section 1 as landed separately. All three are implemented ([lang.go](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/lang.go#L816-L819), [parallel.go](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/parallel.go), [var.go](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/vm/var.go#L42)). `pmapv` is not used by the lowering pipeline.
2. **Deterministic naming: build-args by inst-id, strip gensym suffixes, sort imports.** Gensym suffixes are stripped from emitted names. `split-gensym`, `canonical-name` and `value-name` are in [lower_go.lg](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/core/ir/lower_go.lg#L497-L524). `gensym-renumber-map` is at [lower_go.lg#L3600](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/core/ir/lower_go.lg#L3600). Native imports are sorted ([pipeline.lg](https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/core/ir/passes/pipeline.lg#L1823)). The build-args-by-inst-id item is not confirmed at b82588292b.
3. **Prototype the type cache: content key, join-merge, fixpoint driver, convergence on `core`.** Not started. No cache code was found.
4. **Wire lowering to read the cache, drop the budget, and enable `pmapv` lowering.** Not started. The budget was already dropped from the Go path by the drain-count change described above.

The drain-count bound (Problem 1) is not one of the four phases. Section 3 of the design note describes it as "this PR", which replaces the wall-clock budget. Sequencing step 2 covers the naming work and does not mention the budget.

---

# Citations

[1] **Design note**: parallel lowering investigation and cache proposal
https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/docs/design/parallel-lowering-and-type-cache.md

[2] **pkg/rt/parallel.go**: `pmapv` and binding propagation
https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/parallel.go

[3] **pkg/vm/var.go**: `Var.Deref`, atomic root and binding chain
https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/vm/var.go

[4] **Lowering**: the IR-to-Go code generation step
https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/core/ir/lower_go.lg

[5] **Type inference**: the typeinfer pass in the lowering pipeline
https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/core/ir/passes/typeinfer.lg

[6] **pkg/rt/core/ir/lattice.lg**: type order, `type-join`, instruction fact joins
https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/core/ir/lattice.lg

[7] **pkg/rt/core/ir/passes/pipeline.lg**: Go-lowering entry points, `lower-all-ns-to-go-result`, sorted imports
https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/core/ir/passes/pipeline.lg

[8] **cmd/lgbgen/main.go**: `--target=go` driver
https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/cmd/lgbgen/main.go

[9] **pkg/rt/lang.go**: atomic `gensymID`, `pmapv` registration
https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/lang.go

[10] **pkg/rt/core/core.lg**: `pmap` built on `future`
https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/pkg/rt/core/core.lg

[11] **Makefile**: `generate` and the lowered-Go target
https://github.com/nooga/let-go/blob/b82588292b58ac70908895cc6d9b05e68401e261/Makefile

---

See also: [IR Pipeline](ir-pipeline.md), [Bytecode Compiler](bytecode-compiler.md), [Indexed-RPN IR](indexed-rpn-ir.md)
