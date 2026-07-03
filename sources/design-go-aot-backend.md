---
type: Source
category: source
title: Go AOT backend
description: Design for a second backend that compiles let-go code to Go while preserving runtime semantics and enabling mixed compiled+interpreted execution.
tags: [compiler, go, interop, bytecode]
resource: "https://github.com/nooga/let-go/blob/main/docs/design/go-aot-backend.md"
sources: ["repo: nooga/let-go docs/design/go-aot-backend.md, 2026-07-03"]
created: "2026-07-03"
updated: "2026-07-03"
status: active
---

## What this source is

An architectural design document proposing a second compilation backend that generates Go code from let-go bytecode. Rather than shipping only a bytecode interpreter ([../concepts/bytecode-compiler.md](../concepts/bytecode-compiler.md)), this backend compiles let-go functions directly to Go while keeping the runtime (`pkg/vm` and `pkg/rt`) intact, enabling mixed compiled+interpreted systems and zero-I/O distribution via Go binaries.

## Key contributions

**Two-tier staged approach:**
1. Embedding tier: Emit Go that holds const pools and bytecode as static data, registering functions at `init()` without I/O.
2. Native lowering tier: Translate let-go operations to structured Go code (loops, direct calls) eliminating the bytecode interpreter for hot functions.

**Var-based interop boundary:** Compiled and interpreted code communicate via the same `Var` indirection mechanism, allowing dynamic redefinition and seamless calling in both directions. This is the critical design choice underlying mixed compiled+interpreted execution, central to [../ideas/self-hosting-aot.md](../ideas/self-hosting-aot.md).

**Code generation strategy:** Use Go's `ast` package to safely lower bytecode to Go functions with signatures `func f(env *vm.Env, args []vm.Value) (vm.Value, error)`, translating bytecode ops to control flow and calls to runtime helpers. Stack slots become local variables; tail-calls transform to loops preserving TCO semantics.

**Mixed execution semantics:** Compiled functions can call interpreted functions (and vice versa) through `Var` dereferencing, maintaining dynamic var semantics while extracting compilation benefits where profitable.

## Derived pages

[self-hosting-aot](../ideas/self-hosting-aot.md) · [bytecode-to-go-translation](../ideas/bytecode-to-go-translation.md) · [lg-compile](../concepts/lg-compile.md)

## Citations

- [../concepts/value-representation.md](../concepts/value-representation.md) — reuses `Value`/`Fn` interfaces and `vm.Int` fast paths
- [../concepts/runtime-image.md](../concepts/runtime-image.md) — embedding tier is a Go-native alternative to image I/O
- [../concepts/go-interop.md](../concepts/go-interop.md) — `NativeFn` registration and `Var` boundary design
- [../sources/design-value-representation.md](../sources/design-value-representation.md) — numeric performance design referenced for fast paths
