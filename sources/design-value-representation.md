---
type: Source
category: source
title: "Value Representation and Numeric Performance"
description: "Design documentation on value representation in let-go and performance optimizations for numeric operations in Go."
tags:
  - runtime
  - vm
  - go
resource: "https://github.com/nooga/let-go/blob/main/docs/design/value-representation-and-numeric-performance.md"
sources:
  - "repo: nooga/let-go docs/design/value-representation-and-numeric-performance.md, 2026-07-03"
created: "2026-07-03"
updated: "2026-07-03"
status: active
---

## What this source is

This is a design document from the let-go repository that documents how values (especially numeric types) are represented in the let-go VM, their performance implications in Go, and a detailed checklist of actionable optimizations.

## Key takeaways and contributions

- **Current architecture**: Values are represented through a `Value` interface with `Type()`, `Unbox()`, and `String()` methods. The `Int` type is stored directly in interface words, avoiding heap allocation.

- **Performance characteristics**: Method calls on value receivers are cheap, but repeated `Unbox()` + type assertion in tight loops adds unnecessary overhead. Reflection in `BoxValue` is expensive and should be reserved for interop boundaries only.

- **Optimization opportunities**:
  - Replace `Unbox().(int)` patterns with direct `Int` assertions in numeric natives to eliminate redundant method calls and type assertions
  - Change `Int.String()` from `fmt.Sprintf` to `strconv.Itoa` for faster string conversion
  - Prefer `Wrap`/`WrapNoErr` over `Box` for native function registration in hot paths
  - Avoid calling `BoxValue` in loops; convert inputs once before iteration

- **Specific action items**: The document provides concrete optimizations for `pkg/vm/value.go`, `pkg/vm/int.go`, `pkg/rt/lang.go`, and `pkg/vm/native_func.go`, plus a checklist of microbenchmarks to validate improvements.

## Derived pages

- [value-representation](../concepts/value-representation.md)

# Citations

> **Source**: https://github.com/nooga/let-go/blob/main/docs/design/value-representation-and-numeric-performance.md
>
> Design document authored by the let-go team; status `active` and `human-verified` for `numeric-representation` and `int-unbox-paths` concerns (last verified 2026-06-05).
