---
type: Concept
category: concept
title: deftype & Protocols
description: Custom types and protocol-based polymorphism in let-go, unifying Clojure's deftype/defprotocol with native Go lowering.
tags: [clojure, runtime, stdlib]
resource: https://github.com/nooga/let-go/blob/main/pkg/rt/core/core.lg
sources:
  - design: docs/superpowers/specs/2026-06-14-deftype-defprotocol-native-lowering-design.md (local, 2026-07-02)
  - design: docs/superpowers/specs/2026-06-22-catalog-op-dispatch-deftype-iteration-design.md (local, 2026-07-02)
  - design: docs/superpowers/specs/2026-05-31-invokable-deref-protocols-design.md (local, 2026-07-02)
created: 2026-07-02
updated: 2026-07-02
status: speculative
---

# deftype & Protocols

## When it matters

**deftype** and **defprotocol** are let-go's primary tools for defining custom types and protocol-based polymorphism, mirroring Clojure's abstractions. Protocols enable open extension—any type can implement any protocol via `extend-type`—while deftypes bundle immutable structured data with inline method implementations. Together, they form the foundation for libraries that rely on type-driven dispatch (malli validators, dynaload-style delays, custom callables).

The work to **native-lower deftype/defprotocol** to Go types and interfaces is in-flight and foundational: it moves protocol dispatch from boxed runtime tables to compiled Go method calls where the concrete type is known, and makes IR ops themselves deftypes to eliminate hand-duplicated op handlers scattered across the compiler pipeline.

## Deftype: typed fields + methods

```clojure
(deftype Square [side]
  Shape
  (area [this] (* side side)))

(area (->Square 3))  ; => 9
```

`deftype` creates three artifacts:

1. **The type itself** — a value representing the type for protocol dispatch.
2. **Constructor `->TypeName`** — a positional function `(fn [fields...] ...)` creating instances.
3. **Method implementations** — any protocols named in the form receive inline implementations, rewritten by the macro to wire field access via receiver.

Fields are **immutable** and accessed via `.field-name` syntax (a get method, not mutation). Mutable fields (marked `^:mutable` or `^:unsynchronized-mutable`) are read via bare symbols in method bodies (rewritten to `.field recv`) and mutated with `(set! field v)` (rewritten to `(set-field! recv 'field v)`).

**Closure** — method bodies capture the receiver's fields, shadowing any outer bindings with the same name. For example, in `(area [this] (* side side))`, the bare `side` refers to the field, not an outer variable.

## Defrecord: typed fields + map API

```clojure
(defrecord Point [x y])

(->Point 1 2)       ; positional ctor
(map->Point {:x 1 :y 2})  ; map ctor
```

`defrecord` is like `deftype` but adds **map semantics**: instances are also maps, supporting `(x point-val)` keyword lookup, `assoc`, `seq`, and `count`. It generates both a positional constructor (`->`) and a map constructor (`map->`).

Records are lighter-weight than arbitrary maps when you need both structured data and occasional map operations; deftypes are used when you need only the structure and methods, not map interface.

## Defprotocol: open method dispatch

```clojure
(defprotocol Shape
  (area [this]))

(extend-type Square Shape
  (area [this] (* (.x this) (.y this))))
```

`defprotocol` defines a protocol—a named set of method signatures. Implementing a protocol on a type happens in two ways:

1. **Inline** (in the deftype/defrecord form): `(deftype Square [...] Shape (area [this] ...))`
2. **Open extension** (anywhere, anytime): `(extend-type Square Shape (area [this] ...))`

At a dispatch site like `(area (->Square 3))`, the VM looks up the type of the receiver and dispatches to the implementing method. For **known-concrete types** (e.g., the ctor is a literal `->Square`), the compiler can emit a **direct native call** when lowering to Go; for dynamic types, it routes through the runtime protocol table.

## Reify: anonymous inline types

```clojure
(reify
  Shape
  (area [this] 42))
```

`reify` creates a nameless type on-the-fly, implementing the named protocols. Each call to `reify` produces a fresh type. Useful for one-off implementations, particularly in higher-order functions.

## IFn & IDeref protocols (standard library)

Two core indirection protocols are provided:

- **`IFn`** — `(-invoke [this args])`. A type implementing IFn is callable: `(x arg1 arg2)` dispatches to `(-invoke x [arg1 arg2])`. This enables custom callables and libraries like malli to ship validators as functions.
- **`IDeref`** — `(-deref [this])`. A type implementing IDeref works with `@x` / `(deref x)`, enabling delays, promises, and custom lazy-evaluation types.

Both are wired by the runtime after core loads. See [value-representation](value-representation.md) for how the VM coerces invokable/derefable custom types into native Go function/reference wrappers on the bytecode path.

## Native lowering (in-flight)

The compiler is being restructured to lower deftype/defprotocol to Go structs and interfaces, replacing runtime table dispatch with compiled code. This happens in three stages:

1. **S0** — `deftype` → Go `struct` + field access + constructor.
2. **S1** — `defprotocol` → Go `interface`; protocol methods become Go methods; `extend-type` routes to interface implementations.
3. **S2** — Typeinfer learns "satisfies protocol P" to devirtualize broad call sites.

Currently **S0+S1 are in the walking-skeleton phase**: a single protocol (Shape) and type (Square) are being proven end-to-end through the bytecode **and** native (`-tags gogen_ir`) paths in parallel. The IR op-catalog unification (moving all 27 IR ops into deftypes with protocol-based behavior facets) rides on S0+S1 to eliminate the currently-scattered op handlers.

## Citations

[core.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/core.lg) — macro implementations of `deftype`, `defrecord`, `defprotocol`, `extend-type`, `reify`. Also defines core protocols `IFn` and `IDeref`.
