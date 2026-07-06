---
type: Source
category: source
title: "Clojure-like collections, seq tower, transients and transducers — Refactor Plan"
description: "Staged plan to refactor VM data structures toward Clojure semantics: persistent collections, seq tower, structural equality, and transducers."
tags: [clojure, runtime, compiler]
resource: https://github.com/nooga/let-go/blob/main/docs/clojurelike-refactor-plan.md
sources: ["repo: nooga/let-go docs/clojurelike-refactor-plan.md, 2026-07-03"]
created: "2026-07-03"
updated: "2026-07-03"
status: active
---

## What this is

The canonical five-phase refactor plan for let-go's collection semantics, authored by the maintainer. Captures the current gaps (ad-hoc collections, incorrect seq behavior, no structural equality), target interface hierarchy (proper Seq/Seqable separation, Indexed/Stack abstractions, MapEntry), and detailed migration strategy to minimize breakage while delivering Clojure semantics incrementally.

## Key takeaways

- **Seq tower alignment**: Collections should implement `Seqable` (expose a seq view), not `Seq` directly; builtins coerce via `seq()` and handle `nil`.
- **Persistent data structures**: Replace Go map-backed `Map`/`Set` with HAMT-backed `PersistentHashMap`/`Set`; rework `PersistentVector` to canonical 32-ary bit-partitioned trie with fixed-width nodes.
- **Structural equality & hashing**: Add `Equivable` { `Equiv(Value) bool` } and `Hashable` { `Hash() int` } interfaces; implement consistently across scalars, collections for map/set key safety.
- **Transients & transducers**: Introduce `Editable`/`TransientCollection` for high-performance bulk mutations (copy-free via edit tokens); add `Reducible` fast path and transducer functions (`transduce`, `eduction`, `sequence`, `completing`).
- **Four staged phases**: Phase 0 (interfaces + coercion), Phase 1 (PersistentVector), Phase 2 (maps/sets + equality), Phase 3 (replace core equality), Phase 4 (chunked seq + performance).

## Derived pages

- [clojurelike-refactor](../ideas/clojurelike-refactor.md)

---

## Citations

[Resource link](https://github.com/nooga/let-go/blob/main/docs/clojurelike-refactor-plan.md)
