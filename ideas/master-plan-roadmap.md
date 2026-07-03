---
type: Idea
category: idea
title: "let-go Master Roadmap"
description: "Consolidated roadmap toward the fastest and most useful Clojure-on-Go, spanning 9 phases from baseline semantics through Go AOT compilation."
tags: [clojure, runtime, compiler, vm, bytecode]
resource: "https://github.com/nooga/let-go/blob/main/docs/master-plan.md"
sources: ["docs/master-plan.md", "docs/contribution-policy.md"]
created: "2026-07-03"
updated: "2026-07-03"
status: active
---

# let-go Master Roadmap

The master plan consolidates let-go's existing strategic initiatives into a single, sequenced roadmap: VM performance, Clojure-like collections, numeric and value representation, and runtime images. It defines 9 phases with staged milestones and success criteria to deliver the fastest and most useful Clojure-on-Go implementation.

> **Note on authoritative sources:** This plan is marked `status: active` in its source document (master-plan.md). On direction questions — particularly the status of Phase 7 (Go AOT backend) — [contribution-policy.md](https://github.com/nooga/let-go/blob/main/docs/contribution-policy.md) is authoritative and supersedes this plan. Contribution-policy clarifies that Phase 7 is the committed deployment path (not optional), and establishes design contracts for interop, performance tracking, and the self-hosted compiler direction.

## Vision and success criteria

By the end of this roadmap:

- **Startup**: cold start with stdlib image < 50 ms on a typical laptop; warm start < 5 ms.
- **Throughput**: 2–3x improvement on core functional pipelines (`map`/`filter`/`reduce`) over current baseline; zero-regression guardrails in CI.
- **Allocation profile**: O(1) allocations for transducer-based pipelines over vectors and ranges; no unbounded retention from calling convention.
- **Semantics**: Clojure-aligned collections and seq tower; structural equality and hashing; transients and transducers.
- **Deployability**: precompiled stdlib image by default; app/runtime images supported and versioned; deterministic serialization.

## Guiding principles

- **Correctness first**: codify Clojure semantics via interfaces and tests before aggressive optimizations.
- **Tight hot paths**: specialize VM call paths and numeric primitives; avoid reflection and unnecessary boxing.
- **Incremental rollout**: adapters and compatibility layers to avoid big-bang rewrites; keep REPL usable throughout.
- **Benchmark-driven**: every phase ships microbenchmarks and end-to-end scenarios, with perf budgets enforced in CI.

## Phases overview

The roadmap is organized into nine phases, each with clear scope, dependencies, and acceptance criteria:

### Phases 0–1: Foundations (semantics and VM optimization)

**Phase 0** introduces core interfaces (`Equivable`, `Hashable`, `Indexed`, `Stack`, `IMapEntry`, `Reducible`, `Reduced`) and updates builtins to align with Clojure semantics (`seq` coercion, `nil` handling). It establishes the benchmark harness and CI performance gates.

**Phase 1** fixes VM calling conventions: argument slice copies, tail-call optimization (including closures), frame/stack pooling, and small-arity opcodes (`INVOKE_0/1/2/3`, `TAIL_CALL_0/1/2/3`).

### Phases 2–4: Collections and transduction

**Phase 2** replaces vectors with a canonical 32-ary [BPTR persistent vector](../concepts/indexed-rpn-ir.md), adds transients, and switches the reader to produce persistent types. **Phase 3** implements persistent hash maps/sets (HAMT-based) with structural equality and hashing. **Phase 4** adds transducer APIs (`transduce`, `eduction`, `sequence`) and chunked sequences, enabling O(1) allocation for reduction pipelines.

### Phases 5–6: Deployment and tooling

**Phase 5** defines runtime image schema and versioning, implements serialization for values/code/vars, and pre-builds a `stdlib.img` for fast boot. **Phase 6** polishes nREPL, audits interop patterns, and ships WASM support with instant startup.

### Phase 7: Go AOT backend (optional, high-impact)

Phase 7 adds a **second backend** that compiles let-go code to Go (see [Self-hosting AOT](./self-hosting-aot.md)). It starts with an embedding tier (bytecode/consts as Go data in `Var`s), progresses to native lowering of hot functions, and preserves dynamic `eval` via shared `Var`s. This enables mixed compiled+interpreted execution and eliminates interpreter overhead.

*Note: While this plan marks Phase 7 as optional, [contribution-policy.md](https://github.com/nooga/let-go/blob/main/docs/contribution-policy.md) (authoritative on direction) clarifies that the Go AOT backend (`gogen_ir` tags and native lowering) is the committed deployment path for the self-hosted compiler.*

### Phases 8–9: Polish and experimental optimization

**Phase 8** finishes `ChunkedSeq` across collections, optimizes iteration utilities with `Reducible`, and investigates specialized opcodes for common sequence ops. **Phase 9** (experimental) explores a register-based bytecode alongside the stack VM for further performance gains.

## Cross-cutting: benchmarks and CI

Every phase ships microbenchmarks (call overhead, TCO, vector/map ops, numeric arithmetic, transducer pipelines) and end-to-end scenarios (image load, HTTP JSON via natives, REPL cold/warm start). CI gates enforce <10% regressions on hot paths. Risks are managed through exhaustive tests for opcode variants, property tests for data structures, and versioned image schemas with migration paths.

## Immediate workboard

**Phase 0** focuses on core interfaces and `MapEntry` semantics, numeric fast paths via direct `vm.Int` assertions, and initial benchmarks. **Phase 1** implements arg copies, closure TCO, frame/stack pools, and small-arity opcodes. **Phases 2–4** are sequential: persistent vectors + transients, then maps/sets, then transducers. **Phase 5** builds the image schema and stdlib pre-compilation. **Phase 7** (once phases 0–4 stabilize) adds the Go AOT backend, starting with embedding tier and progressing to native lowering and self-hosting.

# Citations

[1] **docs/master-plan.md**: Master plan with full phase descriptions, dependencies, and immediate workboard (status: active)  
https://github.com/nooga/let-go/blob/main/docs/master-plan.md

[1a] **docs/contribution-policy.md**: Design contracts, regression checkpoints, and deployment direction (supersedes master-plan.md on direction; clarifies Phase 7 as committed deployment path)  
https://github.com/nooga/let-go/blob/main/docs/contribution-policy.md

[2] **Self-hosting AOT** (this wiki)  
[./self-hosting-aot.md](./self-hosting-aot.md)

[3] **let-go** (this wiki)  
[../entities/let-go.md](../entities/let-go.md)

[4] **Value representation and numeric performance** (this wiki)  
[../concepts/value-representation.md](../concepts/value-representation.md)

[5] **Runtime image** (this wiki)  
[../concepts/runtime-image.md](../concepts/runtime-image.md)

---

See also: [clojure-like-refactor](./clojurelike-refactor.md), [jvm-compat](./jvm-compat.md)
