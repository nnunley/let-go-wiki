---
type: Concept
category: concept
title: "Go Structs via defgostruct"
description: "Defining and using Go structs from let-go via compile-time code generation."
tags: [go, interop, compiler]
resource: "https://github.com/nooga/let-go/blob/main/scripts/lginterop.lg"
sources: ["design: docs/superpowers/specs/2026-05-22-defgostruct.md (local, 2026-07-02)", "design: docs/superpowers/specs/2026-05-21-clojure-interop-alignment-design.md (local, 2026-07-02)"]
created: "2026-07-02"
updated: "2026-07-02"
status: speculative
---

# Go Structs via defgostruct

`defgostruct` is a Lisp macro that bridges Go-defined struct types into let-go, generating compile-time bridge code that creates field accessors, constructors, predicates, and setters. Rather than hand-writing hundreds of lines of Go bridge code, you declare the struct once in Lisp and the compiler produces the full interop layer.

## Problem & Design

Go structs (like `*ir.Function`, `*ir.Block`, `*ir.Inst`) need Lisp-side primitives to access and modify their fields. Before `defgostruct`, these primitives were hand-written in Go — error-prone and brittle when struct definitions changed. The macro inverts this: **the Lisp declaration is the source of truth; the Go code is generated from it**.

This applies the same pattern that let-go already uses for IR operations (`examples/go-gen/ir_ops.lg` → `pkg/ir/op_generated.go`).

## Usage: Declaring a Go Struct

Define a Go struct in the `defgostruct` macro by specifying:
- The fully-qualified Go type
- A Lisp namespace and short-name for generated primitives
- Field map in kebab-case (auto-converted to PascalCase for Go)
- Optional mutable fields and extra methods

```clojure
(defgostruct ir.Function
  :type "github.com/nooga/let-go/pkg/ir.Function"
  :ns "ir"
  :short-name "fn"
  
  :fields
    {:name          String
     :arity         Int
     :is-variadic   Bool
     :insts         [Inst]
     :blocks        [Block]
     :entry         BlockID}
  
  :mutable [:insts :blocks]
  
  :extras [{:name "dump" :args (Self) :returns (String) :calls "ir.Dump"}
           {:name "add-block" :args (Self) :returns (Int) :calls "AddBlock"}])
```

## Generated Primitives

The macro generates primitives on the declared namespace (`:ns "ir"`) with the short-name prefix (`:short-name "fn"`):

| Primitive                    | Kind       | Maps to Go                              |
|------------------------------|------------|------------------------------------------|
| `ir/new-fn`                  | constructor| `ir.NewFunction(name, arity, variadic, nil)` |
| `ir/fn?`                     | predicate  | Type check: `_, ok := v.Unbox().(*ir.Function)` |
| `ir/fn-name`                 | getter     | `f.Name` → string                       |
| `ir/fn-arity`                | getter     | `f.Arity` → int                         |
| `ir/fn-variadic?`            | getter     | `f.IsVariadic` → boolean                |
| `ir/fn-insts`                | getter     | `f.Insts` → vector of boxed `*Inst`     |
| `ir/fn-blocks`               | getter     | `f.Blocks` → vector of boxed `*Block`   |
| `ir/fn-entry`                | getter     | `int(f.Entry)`                          |
| `ir/fn-set-insts!`           | setter     | `f.Insts = newSlice; f.MarkUsesDirty()` |
| `ir/fn-set-blocks!`          | setter     | `f.Blocks = newSlice; f.MarkUsesDirty()` |
| `ir/fn-dump`                 | extra      | `ir.Dump(f)`                            |
| `ir/fn-add-block`            | extra      | `f.AddBlock()`                          |

**Boolean field naming**: Fields with Go type `bool` automatically get a `?` suffix in the Lisp name (`IsVariadic` → `ir/fn-variadic?`).

**Slice access helpers**: For slice-of-struct fields like `:insts [Inst]`, the macro also emits:
- `ir/fn-inst-at` — getter by index: `(ir/fn-inst-at f 3)` → boxed `*Inst` for `f.Insts[3]`
- `ir/fn-inst-count` — length: `len(f.Insts)`

When a slice field is in `:mutable`, also generates:
- `ir/fn-add-inst!` — append a new `*Inst` to the slice

## Type Conversions

**Simple types** (`String`, `Int`, `Bool`, `Float`) convert directly between Go and [value-representation](value-representation.md).

**Go type aliases** (`type BlockID int32`) are handled as primitive integers. The macro accepts them as field types and translates them to integers on the Lisp side.

**Slice fields** (`[Inst]`) are returned as Lisp vectors of boxed pointers, enabling iteration with `map`, `reduce`, etc.

## Field Mutability and Side Effects

Fields marked in `:mutable` get setter primitives (e.g., `ir/fn-set-insts!`) that:
1. Replace the Go field with a new slice
2. Call `MarkUsesDirty()` on the struct if it tracks changes

This bridges let-go's immutable semantics (setters return modified values) to Go's mutable structs (fields are replaced in-place).

## Extra Methods

The `:extras` list adds primitives for methods that don't map to single fields. Each entry specifies:
- `:name` — the Lisp function name suffix
- `:args` — Go types (use sentinel `Self` for the receiver)
- `:returns` — Go return types (supports `(T1 error)` for error returns)
- `:calls` — the Go expression to invoke (bare name = method; dotted = function)

Example:
```clojure
{:name "dump" :args (Self) :returns (String) :calls "ir.Dump"}
; generates: (ir/fn-dump f) → calls ir.Dump(f)
```

The generator automatically unboxes/boxes arguments and results based on type.

## Current State

The feature is **speculative** (design awaiting approval, not yet shipped). When implemented:

1. The macro and generator will live in `examples/go-gen/ir_bridge.lg`
2. A new `make generate-ir-bridge` target will regenerate `pkg/rt/ir_bridge_generated.go`
3. Hand-written bridge code in `pkg/rt/lang.go` will be replaced with a call to the generated `installIRBridgeBuiltins()` function

The IR types (`Function`, `Block`, `Inst`) are the initial scope; the macro is designed to extend to other Go structs later.

## Relationship to Clojure Interop

As part of the clojure-interop alignment effort, let-go also gains `.getBytes()` method support on strings and improved hex literal handling, enabling cross-platform code sharing between let-go and Clojure JVM. (See sources for design doc details.)

# Citations

[1] **defgostruct design** — spec for codegen-driven Go-struct ↔ Lisp bimap  
(local, 2026-05-22)

[2] **lginterop generator** — Go package reflection and wrapper generation  
https://github.com/nooga/let-go/blob/main/scripts/lginterop.lg

[3] **clojure-interop-alignment design** — Clojure JVM compatibility improvements  
(local, 2026-05-21)

---

See also: [Go Interop](go-interop.md), [lginterop](lginterop.md), [value-representation](value-representation.md), [let-go](../entities/let-go.md)
