---
type: Source
category: source
title: Parallel IR lowering, and a mergeable type-discovery cache
description: Investigation into parallelizing IR lowering passes and a proposed mergeable type-discovery cache for deterministic, full-precision parallel compilation.
tags: [compiler, runtime, reference]
resource: https://github.com/nooga/let-go/blob/main/docs/design/parallel-lowering-and-type-cache.md
sources:
  - "repo: nooga/let-go docs/design/parallel-lowering-and-type-cache.md, 2026-07-03"
created: "2026-07-03"
updated: "2026-07-03"
status: active
---

# Parallel IR lowering, and a mergeable type-discovery cache

A design note capturing the 2026-05-30 investigation into parallelizing the IR passes during `lgbgen --target=go`. The per-defn work (expand → build IR → optimize → typeinfer → lower) is embarrassingly parallel across function definitions in a namespace, but naive parallelization with `pmap` and `future` blocked on:

1. **Binding spawn cost** — snapshots and reinstatement of dynamic bindings serialized the work; fixed via lock-free `Var.Deref` and a new eager `pmapv` primitive (1.24× speedup, ~1.9 effective cores on the `core` namespace lowering).

2. **Non-deterministic output** — gensym counters and wall-clock type-inference budgets introduced scheduling-dependent variation in generated code. Deterministic naming (strip gensym suffixes, sort imports) addresses symbol sources; the wall-clock budget remains the fundamental blocker.

## Key contribution

A **mergeable type-discovery cache** that decouples type inference results from execution pressure. Because type inference is monotone (types only move up the lattice), the cache can merge discoveries across parallel workers deterministically. The cache converges to a fixpoint via interprocedural iteration, is committed as a build artifact (like the `.lgb` bundle and lowered tree), and enables parallel lowering that is both fast and reproducible without capping inference precision.

# Citations

| Source | Date | Status |
|--------|------|--------|
| [Parallel IR lowering and type-discovery cache design](https://github.com/nooga/let-go/blob/main/docs/design/parallel-lowering-and-type-cache.md) | 2026-06-05 | Active |
