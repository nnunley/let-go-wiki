---
type: Concept
category: concept
title: "Type Inference and the Type Cache"
description: "How the let-go compiler infers types during IR lowering and uses a mergeable cache to make parallel lowering both fast and deterministic."
tags: [compiler, bytecode, runtime]
resource: "https://github.com/nooga/let-go/blob/main/docs/design/parallel-lowering-and-type-cache.md"
sources: ["design: parallel-lowering-and-type-cache.md, 2026-06-05"]
created: "2026-07-02"
updated: "2026-07-02"
status: stable
---

# Type Inference and the Type Cache

The let-go compiler infers types during lowering to optimize dispatch and reduce runtime overhead. When a function's input and return types are known, the compiler can emit direct native dispatch instead of slower generic calls. For large standard libraries, type inference is the slowest part of the bootstrap. The solution is a **mergeable type-discovery cache** that makes parallel lowering both fast *and* deterministic.

## The Lowering Challenge

The `lgbgen` tool lowers every function in the core namespace from let-go source to Go bytecode. This is the bottleneck in the bootstrap (~3 minutes). The per-function work is embarrassingly parallel:

```
expand → build IR → optimize → type-infer → lower → emit
```

Each step is independent across functions, but **type inference creates two problems**.

### Problem 1: Wall-Clock Budget Non-Determinism

Type inference uses a **wall-clock budget** (`*typeinfer-budget-ms*`, typically 2000 ms per function). When the budget runs out, the function returns a sound lower bound in the type lattice—a partial result.

Under parallel load (N workers contending for CPU), each typeinfer call gets less wall-time, hits the budget sooner, and bails with *less* type information. A function that qualifies for direct native dispatch sequentially falls back to generic dispatch in parallel—changing the imports and emitted Go code **run-to-run**. This non-determinism is unacceptable for reproducible builds.

**A time-based budget is inherently non-deterministic under variable CPU load.**

### Problem 2: Parallel Binding Overhead

Early attempts at parallel lowering with `pmap` (future-based parallel map) showed zero speedup, even with the gensym race fixed. The cause: every `future` calls `SnapshotBindings` + `RunWithBindings`, which copy every active dynamic binding per spawn. With ~50 lowering workers, this copying overhead serializes the work.

The fix came in two parts:

- **Lock-free `Var.Deref`** (atomic `root`/`curr` instead of global `bindingsMu`): dynamic-var reads no longer serialize.
- **`pmapv`** — an eager, synchronous parallel map that doesn't capture and reinstate the binding scope per spawn. Workers read the caller's bindings via the lock-free `Deref`, and the work becomes truly parallel.

Result: sequential 193 s → `pmapv` 155 s (1.24× speedup, ~1.9 effective cores).

## The Solution: A Mergeable Type-Discovery Cache

Rather than a deterministic *iteration* budget (which caps precision permanently), cache the type discoveries and **merge** them across runs.

### Why It's Sound

Type inference is **monotone**: `set-type-if-changed!` is a lattice **join**—types only move up (`:unknown → :int → :number → :any`), never down. The budget bails with a lower bound. Therefore:

- A cache entry is a point in the type lattice.
- Merging two entries is the **least upper bound** (LUB / join).
- Join is commutative, associative, idempotent ⇒ **merge order is irrelevant**.

Two parallel runs that each got partway merge to a result at least as precise as either, deterministically. Workers contribute discoveries to a shared cache, and the converged result is independent of scheduling.

### Shape and Convergence

- **Key**: A content hash of the function's IR (stable across runs; auto-invalidates when source changes).
- **Value**: Inferred signature (arg types, result type) ± per-instruction types.
- **Merge**: Per-field lattice join; concurrent writers compare-and-join per key.
- **Convergence**: Interprocedural—F's inference improves when its callees' cached signatures improve. Iterate to a whole-program fixpoint. Monotone + finite lattice height ⇒ terminates.
- **Committed artifact**: Like the lowered tree, commit the converged cache. A "warm to fixpoint" step (sequential, unbudgeted, correctness-over-speed) produces it; `make generate` runs it. Lowering then *reads* the cache—fast, parallel, reproducible.

### Comparison

| Approach | Deterministic? | Full precision? | Parallel-safe? | Decouples discovery from use? |
|---|---|---|---|---|
| Wall-clock budget (today) | No | Sometimes | — | No |
| Deterministic iteration budget | Yes | No (capped) | Yes | No |
| Mergeable type cache | Yes (once converged) | Yes | Yes | Yes |

## Why It Matters

The mergeable cache achieves:

- **Determinism**: Two lowering runs produce byte-identical Go code, enabling reproducible builds and CI/CD.
- **Full precision**: No permanent cap on type inference; the cache accumulates discoveries across runs.
- **Parallel speedup**: Workers contribute to the cache lock-free; `pmapv` + lock-free derefs enable real parallelism.
- **Separation of concerns**: Discovery (a background, unbudgeted phase) is separated from use (lowering reads the cache fast).

For the ~3-minute bootstrap, this unlocks parallel lowering as a production technique instead of a fragile optimization.

## Implementation Phases

1. Land the keepers: atomic gensym, `pmapv`, lock-free `Var.Deref`—correct independent of any cache.
2. Land deterministic naming: build-args by inst-id, strip gensym suffixes, sort imports.
3. Prototype the type cache: content-key + join-merge + fixpoint driver; measure convergence on `core`.
4. If convergence is cheap, wire lowering to read it, drop the wall-clock budget, and turn on `pmapv` for the speedup.

# Citations

[1] **Design findings**: Parallel lowering investigation and cache proposal  
https://github.com/nooga/let-go/blob/main/docs/design/parallel-lowering-and-type-cache.md

[2] **pkg/rt/parallel.go**: `pmap`, `pmapv`, and binding propagation  
https://github.com/nooga/let-go/blob/main/pkg/rt/parallel.go

[3] **pkg/vm/var.go**: `Var.Deref`, lock-free atomics  
https://github.com/nooga/let-go/blob/main/pkg/vm/var.go

[4] **Lowering**: The IR-to-Go code generation step  
https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/lower_go.lg

[5] **Type inference**: The typeinfer pass in the lowering pipeline  
https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/passes/typeinfer.lg

---

See also: [IR Pipeline](ir-pipeline.md), [Bytecode Compiler](bytecode-compiler.md), [Indexed-RPN IR](indexed-rpn-ir.md)
