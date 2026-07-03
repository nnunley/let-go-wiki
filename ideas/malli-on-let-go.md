---
type: Idea
category: idea
title: "malli on let-go"
description: "Feasibility of running metosin's malli (Clojure data-schema library) on let-go via Babashka-compatible reader branches and Go-backed interop."
tags: [clojure, lisp, interop]
resource: "https://github.com/metosin/malli"
sources: ["docs/superpowers/MALLI_PORT_ANALYSIS.md", "docs/superpowers/specs/2026-05-30-malli-on-let-go-design.md"]
created: "2026-07-02"
updated: "2026-07-02"
status: speculative
---

# malli on let-go

[**malli**](https://github.com/metosin/malli) is metosin's popular data-schema library for Clojure: schemas for validation, generation, transformation, and serialization of structured data. Running **stock, released malli** (no fork) on let-go is feasible — and far cheaper than building a custom schema system — because malli already ships Babashka reader branches that sidestep JVM-internal assumptions.

## Why feasible

malli's maintainers wrote `:bb` (Babashka) reader conditionals specifically for non-JVM hosts. let-go, also non-JVM, can leverage these fallbacks:

- **No JAR loading needed**: malli is pure Clojure; load `.cljc` source directly.
- **Zero external runtime deps**: core malli (validation, transformation) depends only on core Clojure.
- **`:bb` reader branches avoid JVM internals**: malli uses conditional branches like:
  ```clojure
  #?(:bb (vec arr)           ; Babashka fallback
     :clj (LazilyPersistentVector/createOwning ...))  ; JVM path
  ```
  let-go can match the `:bb` feature to load these branches.

## Core validation works unmodified

Scalar, collection, and map schemas work with minimal shims:

```clojure
(require '[malli.core :as m])

(m/validate :int 42)                              ; ✅ scalar
(m/validate [:map [:x :int] [:y :string]] 
            {:x 1 :y "hi"})                       ; ✅ collection/map
(m/validate [:cat :int :string] [1 "a"])          ; ⚠️  sequence (regex engine)
```

## Implementation roadmap (v1: core validation)

### 1. Reader: match `:bb` feature (keystone)
- Add `:bb` to let-go's reader feature set (alongside existing `:clj`).
- Surgical change in `pkg/compiler/reader.go`.
- **Impact**: malli's non-JVM fallbacks activate automatically.

### 2. Smoke test & shims
- Load `(require '[malli.core :as m])`.
- Install small shims for host constructors that malli assumes:
  - `clojure.lang.MapEntry.` → return a let-go map-entry.
  - `hash-combine` → trivial Clojure/Go shim.
  - `compare-and-set!` → missing builtin (atoms have mutex; add as primitive).

### 3. Regex engine (sequence schemas)
- **Hard part**: malli's regex engine uses mutable `deftype` fields (`^:unsynchronized-mutable` + `set!`).
- let-go `deftype` is currently immutable-only.
- **Two paths**:
  - **A**: Add mutable-field support to let-go `deftype` (more general; enables other ports).
  - **B**: Fork `regex.cljc` to use `volatile!` (atoms) instead of mutable fields.
  - Both are doable; A is cleaner.

### 4. Extended features (v2+)
- Error messages, transformers, generators (test.check), `:fn` schemas (SCI evaluation).
- These are separable follow-ups.

## Interop strategy: three layers

### Layer 1: `:bb` reader lens
malli automatically takes Babashka-compatible code paths. No interop code needed.

### Layer 2: Native shims
Small let-go implementations:
- `MapEntry` constructor (already a first-class value type in let-go).
- `hash-combine` (numeric operation).
- `compare-and-set!` (atomic compare-and-swap).

### Layer 3: Go-backed constructors
For Java classes that malli constructs at runtime:
- Use `gojava` (Go reimplementations of `java.*` classes).
- Only needed if malli calls `(java.util.ArrayDeque.)` or similar (tied to regex engine).

## Effort estimate

- **Scalar + map/collection schemas**: 2–4 days
  - Reader `:bb` matching
  - Three shims (MapEntry, hash-combine, compare-and-set!)
  - Smoke tests
  
- **Full core incl. sequence schemas**: +3–5 days
  - Regex engine mutable-deftype work (dominant cost)
  - Comprehensive tests
  
- **Generators/`:fn`/error formatting**: separate, deferred efforts

## Why this matters

- **Ecosystem reuse**: malli is battle-tested, maintained, and widely used in production Clojure.
- **Data validation**: let-go can validate configurations, API schemas, and domain data without rolling custom.
- **Honest port**: stock malli (zero forks) means upstream compatibility and low maintenance burden.
- **Precedent for other libraries**: proof that Babashka-compatible libraries work on let-go; opens doors to plumatic/schema, spec-tools, and others.

## Risks and mitigations

- **Reader branches drift**: malli's `:bb` path could diverge from let-go needs. Mitigation: stay close to Babashka; upstream liaison if branch coverage gaps emerge.
- **Mutable deftype complexity**: if letting let-go support mutable fields, must not break immutability guarantees for persistent collections. Mitigation: isolate to `^:unsynchronized-mutable` annotation; comprehensive tests.
- **Performance**: regex engine is hot path. Mitigation: profile and optimize after core is working; Go-backed fallbacks available if needed.

# Citations

[1] **docs/superpowers/MALLI_PORT_ANALYSIS.md**: Feasibility analysis (local source)  
/Users/ndn/development/let-go/docs/superpowers/MALLI_PORT_ANALYSIS.md

[2] **docs/superpowers/specs/2026-05-30-malli-on-let-go-design.md**: Design document (local source)  
/Users/ndn/development/let-go/docs/superpowers/specs/2026-05-30-malli-on-let-go-design.md

[3] **metosin/malli**: GitHub repository  
https://github.com/metosin/malli

[4] **Babashka pods & reader** (this wiki)  
[../concepts/pods.md](../concepts/pods.md)

[5] **let-go** (this wiki)  
[../entities/let-go.md](../entities/let-go.md)

---

See also: [lginterop](../concepts/lginterop.md), [clojure-compat](../references/clojure-compat.md)
