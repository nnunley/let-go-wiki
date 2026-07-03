---
type: Idea
category: idea
title: "Closing the JVM-Clojure Compatibility Gap"
description: "A phased plan to run real-world Clojure libraries in let-go by mapping JVM symbol shapes to let-go runtime values."
tags: [clojure, interop, runtime]
resource: "https://github.com/nooga/let-go/blob/main/docs/jvm-compat-plan.md"
sources:
  - "https://github.com/nooga/let-go/blob/main/docs/jvm-compat-plan.md"
created: "2026-07-03"
updated: "2026-07-03"
status: speculative
---

## Overview

The goal is to load real-world Clojure libraries (hiccup, fipp, medley, and others) from source without forking them. Rather than embedding Java or running on the JVM, the plan maps *symbol shapes* that libraries use into let-go [runtime](../references/clojure-compat.md) values—allowing pure-Clojure code to run unmodified.

The success metric is `test/compat/run.lg`, the compatibility regression suite. After each implementation phase, corpus pass rate reveals what works.

---

## The Concrete Wall

The clearest blocker emerges from hiccup's `util.clj`, which uses four JVM-shaped constructs that the current runtime cannot represent:

1. **Class-symbol resolution** — code like `clojure.lang.Keyword` needs to map to a known type.
2. **Protocol fallback to `Object`** — `extend-protocol` with an `Object` clause for default dispatch.
3. **Method invocation** — `(.startsWith p "/")` syntax and delegation.
4. **Constructor sugar** — `(URI. s)` syntax for instantiating types.

These four form the spine; the rest of the corpus uses subsets of the same patterns.

---

## Non-goals

The plan explicitly does not:
- Run on the JVM or embed Java; we map *symbol shapes* libraries use into let-go runtime values.
- Support reflection (`Class/forName`, `.getClass`).
- Achieve full clojure.core parity—only what the corpus actually touches.
- Support `cljs/*` namespaces. (`.cljc` with `:clj` reader conditionals is in scope; `.cljs` is not.)

---

## Layered Architecture

The solution is three independent layers, each useful alone and shippable separately:

### Layer 1: Class Symbol → ValueType Registry

Populate namespaces like `clojure.lang`, `java.lang`, and `java.net` with vars that root to let-go `ValueType`s:

| Clojure symbol | let-go value |
|---|---|
| `clojure.lang.Keyword` | `KeywordType` |
| `clojure.lang.Symbol` | `SymbolType` |
| `clojure.lang.Ratio` | `RatioType` |
| `clojure.lang.PersistentVector` | `PersistentVectorType` |
| `clojure.lang.PersistentHashMap` | `PersistentMapType` |
| `clojure.lang.IPersistentCollection` | `AnyCollType` (sentinel) |
| `clojure.lang.IFn` | `FnType` |
| `java.lang.String` | `StringType` |
| `java.lang.Object` | `AnyType` (sentinel) |
| `java.lang.Throwable` | `ErrorType` |
| `java.lang.Number` | `NumberType` (sentinel) |
| `java.lang.Long` / `Integer` | `IntType` |
| `java.lang.Double` | `FloatType` |

Sentinel types act as dispatch keys and are handled specially by protocol lookup. Cost: one shim namespace, ~50 vars, plus 1–2 sentinel types. Unblocks most `extend-protocol`/`extend-type` failures.

### Layer 2: Protocol Fallback Dispatch

Extend `Protocol.Lookup` to walk registered "interface" sentinels when a direct type hit misses:

1. Direct hit on `target.Type()` (current behavior).
2. Check sentinel predicates (`NumberType`, `AnyCollType`) for satisfaction.
3. Fall back to `AnyType` impl if registered.
4. nil — current `nilImpl` path.

Cost: ~50 lines in protocol dispatch. Unblocks `Object`-fallback `extend-protocol` clauses.

### Layer 3: Method Invocation and Constructor Syntax

The compiler already rewrites `(.member instance args)` to `instance.InvokeMethod(member, args)` and `(Class. args)` to constructor form. What's missing is populating the implementations:

1. Built-in value types (`String`, `PersistentVector`, etc.) need `InvokeMethod` implementations with a small method table delegating to existing builtins.
2. Shim "Java types" (`URI`, `URLEncoder`) need tiny defrecord-shaped wrappers in shim namespaces, exposing methods like `.getHost` via `InvokeMethod`.

Cost: ~50 lines per built-in type; ~30 total corpus methods. Reflection is explicitly out of scope—the registry is hand-curated. Unblocks nearly all interop usage in the corpus.

---

## Phasing Strategy

Each phase is shippable and measurable:

**Phase A** — Layer 1 (class registry). Add `pkg/rt/jvm_shim.go` defining `clojure.lang` + `java.lang` shim namespaces. Mark non-existing types with stub sentinels. Run corpus → expect fixable shifts and new passes.

**Phase B** — Layer 2 (protocol fallback). Add sentinels and extend `Protocol.Lookup` walk. Wire sentinel resolution. Run corpus → expect hiccup/util.clj to load if Layer 3 isn't needed (it is).

**Phase C** — Layer 3 (Receiver implementations). Add `InvokeMethod` to built-in types and shim Java types. Hand-register the ~30 methods the corpus uses. Run corpus → hiccup loads end-to-end.

Stop after Phase C and re-evaluate. Layer 4 (deftype Java method bodies) only if remaining failures still pin on it.

---

## Test Strategy

- `test/compat/run.lg` is the regression suite; diff histograms before/after each phase.
- Per-phase: focused `.lg` integration tests (e.g., `test/jvm_shim_test.lg`) exercising the mechanism without third-party code.
- No mocks; real types and protocols.
- Bench load-string of a representative file (medley/core.cljc) to ensure no meaningful performance regression.

---

## Implementation Constraints

We explicitly will not:
- Auto-generate the class registry from JVM reflection. Hand-curated is faster and more honest about what we actually support.
- Attempt to make let-go a Clojure replacement. The bar is "load and run pure-Clojure libraries", not "be Clojure".
- Support multi-arity Java method overloading. Pick the most common signature; reject the rest.

See [Clojure Compatibility](../references/clojure-compat.md) for the broader scope of what is in view.

---

## Estimate

Phase A: 1 day. Phase B: 1 day. Phase C: 1–2 days (compiler dispatch already exists; only receiver tables remain). Total: **~3–5 working days** to land the spine, plus ongoing work each time the corpus surfaces a new method/class.

---

# Citations

**Primary source:**
- GitHub: https://github.com/nooga/let-go/blob/main/docs/jvm-compat-plan.md (status: active, last-verified 2026-06-05)
