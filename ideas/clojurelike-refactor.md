---
type: Idea
category: idea
title: "Rewriting Internals in let-go (Clojure-like Refactor)"
description: "Aligning let-go's collection semantics with Clojure through persistent data structures; Phases 1–3 shipped, Phase 4 (transducers) in progress."
tags: [runtime, clojure, lisp, compiler]
resource: "https://github.com/nooga/let-go/blob/main/docs/clojurelike-refactor-plan.md"
sources: ["docs/clojurelike-refactor-plan.md"]
created: "2026-07-03"
updated: "2026-07-03"
status: active
---

# Rewriting Internals in let-go (Clojure-like Refactor)

**Status**: Phases 1–3 (PersistentVector, PersistentHashMap/Set, Equiv/Hash interfaces) are shipped. Phase 4 (transducers, ChunkedSeq, Reducible fast path) is in progress.

**Aligning let-go's runtime with Clojure's collection semantics and persistence model** is an ongoing refactor: replace mutable Go maps with persistent data structures (vectors, hash maps, sets), introduce correct seq-tower semantics, add transients for efficient bulk building, and implement transducers for lazy, composable transformations. This improves both semantics correctness and performance while maintaining interoperability with existing Go code.

## Current state: gaps and antipatterns

Today's let-go deviates from Clojure in several key ways:

- **Collections implement `Seq` directly** instead of `Seqable`, causing `first`/`next`/`rest` to skip proper `seq` coercion. Non-sequence types (maps, sets) cannot be treated uniformly.
- **Mutable Go maps and sets** back `Map` and `Set` types via copy-on-write assoc/dissoc; no structural sharing, no persistent versions.
- **`PersistentVector` exists but deviates** from Clojure's canonical 32-ary bit-partitioned trie in node width, edge-case handling, and chunked seqs.
- **No equality/hash abstractions**: `=` uses raw Go equality; no `Equiv`/`Hash` for value-based key lookups in maps/sets; no structural equality across types.
- **Reader builds `ArrayVector`** for vector literals; maps are mutable copies.

These gaps mean user code must work around Clojure-like idioms or accept silent correctness bugs when using collections as keys or relying on structural equality.

## Target design: interface hierarchy and semantics

The refactor introduces a Clojure-aligned interface hierarchy:

**Core abstractions:**
- `Equivable` and `Hashable` for structural equality and stable hashing across all value types (numbers by value, sequences element-wise, maps/sets by entries).
- `Seq` (for sequence values only), `Seqable` (for all collections) to enforce proper coercion via `seq`.

**Collections:**
- `Indexed` for vectors: `Nth(i)`, `NthOr(i, default)`.
- `Stack` for lists/vectors: `Peek()`, `Pop()`.
- `IMapEntry` to abstract key-value pairs (replacing the current 2-vector convention).

**Transients (performance-friendly mutability):**
- `Editable` → `AsTransient()` to convert persistent to mutable.
- `TransientCollection`, `TransientAssociative` APIs: `conj!`, `assoc!`, `dissoc!`, `persistent!`.
- Edit tokens stored in nodes to enforce single-owner semantics and refuse operations after `persistent!`.

**Reductions and transducers:**
- `Reducible` fast path for `reduce` to avoid intermediate seqs.
- `Reduced` wrapper for early termination.

## Migration strategy: phased approach

**Shipped phases (Phases 1–3):**

### Phase 1: PersistentVector correctness ✓
Canonical 32-ary BPTR with correct `Pop`, `Peek`, and seq traversal, `TransientVector` with edit tokens. Reader vector literals switched to persistent.
- **Shipped**: `pkg/vm/persistent_vector.go`, transient builtins in `pkg/rt/lang.go:4410`

### Phase 2: Persistent maps and sets ✓
`Equivable`/`Hash` for core value types. `PersistentHashMap` (HAMT) and `PersistentHashSet` with structural sharing. Constructors and reader updated to persistent versions.
- **Shipped**: `pkg/vm/persistent_map.go`, `PersistentHashSet` with transient variants

### Phase 3: Equality and hashing in core ✓
Structural `Equiv` replacing raw equality; `contains?` and `get` use new semantics.
- **Shipped**: `pkg/vm/hash.go:15` with Hashable interface and Equiv on core value types

**In-progress phase:**

### Phase 4: Transducers and performance (ongoing)
Add `ChunkedSeq` for vectors/ranges. Implement `Reducible` fast path for `reduce`. Introduce `transduce`, `eduction`, `sequence`, `completing`. Refit `into`, `mapv`, `keep`, `group-by` to use transducers. Benchmarks verify no intermediate allocations and improved throughput.

**Note on Phase 0**: Interfaces and adapters (seq coercion, `nil` handling, `MapEntry`) were folded into the shipped phases where applicable.

## Testing philosophy

High-value test coverage includes:
- **Seq coercion**: `(first [])`, `(next {})`, `(more nil)` correctness.
- **Conj semantics** across list/vector/map/set; map `conj` accepting `IMapEntry`.
- **Vector boundaries**: exact multiples of 32, assoc/pop at edges, random access.
- **Map correctness**: deep updates/removals, collision nodes, insertion-order independence.
- **Transients**: error on use-after-persistent, persistent result equivalence, bulk-build efficiency.
- **Transducers**: `transduce (map inc)` equivalence, `into` composability, `eduction` laziness.

## Compatibility and rollout

- Maintain `ArrayVector` and current map/set types during transition; builtins accept both via interfaces.
- Flip reader for vectors/maps/sets only when persistent implementations pass comprehensive tests.
- No changes to public function arities or semantics; only expansion to support `nil`/`Seqable` coercion and new features.
- Clear error messages for transient misuse.

The dogfooding push: moving runtime/compiler internals from Go into let-go itself (self-hosting). This refactor is a prerequisite: persistent data structures and correct semantics enable let-go to be bootstrapped from let-go source, not hand-written Go.

# Citations

[1] **docs/clojurelike-refactor-plan.md**: Full refactor plan with phases, interface definitions, and work items  
https://github.com/nooga/let-go/blob/main/docs/clojurelike-refactor-plan.md

[2] **let-go** (this wiki)  
[../entities/let-go.md](../entities/let-go.md)

[3] **IR pipeline** (this wiki)  
[../concepts/ir-pipeline.md](../concepts/ir-pipeline.md)

[4] **Runtime image** (this wiki)  
[../concepts/runtime-image.md](../concepts/runtime-image.md)

[5] **Value representation** (this wiki)  
[../concepts/value-representation.md](../concepts/value-representation.md)

---

See also: [self-hosting-aot](self-hosting-aot.md), [master-plan-roadmap](master-plan-roadmap.md)
