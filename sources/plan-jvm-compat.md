---
type: Source
category: source
title: "JVM Compatibility Shim Plan"
description: "Three-layer architecture for loading real-world Clojure libraries in let-go via class-symbol resolution, protocol fallback, and receiver method dispatch."
tags: [clojure, runtime, interop]
resource: "https://github.com/nooga/let-go/blob/main/docs/jvm-compat-plan.md"
sources: ["repo: nooga/let-go docs/jvm-compat-plan.md, 2026-07-03"]
created: "2026-07-03"
updated: "2026-07-03"
status: stable
---

# JVM Compatibility Shim — Source

This document is the canonical plan for adding JVM interop shims to let-go, enabling unforked use of real-world Clojure libraries (hiccup, fipp, medley) that depend on JVM-specific language constructs.

## Key contribution

The plan defines a pragmatic three-layer architecture to support class-symbol resolution, protocol fallback dispatch, and method invocation:

**Layer 1: Class symbol → ValueType registry**  
Map JVM class symbols (`clojure.lang.Keyword`, `java.lang.String`, `java.lang.Object`, etc.) to let-go runtime value types via shim namespaces (`clojure.lang`, `java.lang`). Sentinel types like `AnyType` and `NumberType` serve as dispatch keys, not real types.

**Layer 2: Protocol fallback dispatch**  
Extend `Protocol.Lookup` to check sentinel types when direct type lookup fails, enabling `Object`-keyed `extend-protocol` clauses that provide fallback implementations for any type satisfying a predicate.

**Layer 3: Receiver method dispatch**  
Populate `InvokeMethod` on built-in value types and create shim constructors to handle `.method obj args` syntax and `(Class. args)` constructor sugar for a curated set (~30 total) of methods actually used by the corpus.

Each layer is independently shippable; Phase C completes the critical path (estimated 3–5 working days total).

## Concrete gap addressed

The hiccup library's `util.clj` blocks 7 of 9 hiccup files due to four JVM-shaped constructs: `extend-protocol` with `Object` fallback, `.method` invocation, `(Class. args)` constructor calls, and class-symbol resolution. This plan unblocks all four via a hand-curated registry (no reflection).

## Explicit non-goals

- Running on the JVM or embedding Java
- Supporting reflection (`Class/forName`, `.getClass`)
- Full clojure.core parity (only corpus-required subsets)
- ClojureScript (`.cljs` namespaces; `.cljc` reader conditionals are in scope)

## Derived pages

[jvm-compat](../ideas/jvm-compat.md) · [clojure-compat](../references/clojure-compat.md)

# Citations

- **Resource**: /Users/ndn/development/let-go/docs/jvm-compat-plan.md ([GitHub](https://github.com/nooga/let-go/blob/main/docs/jvm-compat-plan.md))
- **Status in source**: active, last verified 2026-06-05
