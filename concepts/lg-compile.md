---
type: Concept
category: concept
title: "lg-compile"
description: "Ahead-of-time compilation of let-go source files to Go packages with cross-package function calls."
tags: [compiler, tooling, go]
resource: "https://github.com/nooga/let-go/blob/main/scripts/lg-compile"
sources: ["repo: nooga/let-go scripts/lg-compile, pkg/rt/core/ir/lower_go.lg (lowering), 2026-07-02"]
created: "2026-07-02"
updated: "2026-07-02"
status: stable
---

# lg-compile

`lg-compile` is a let-go script that AOT-compiles a set of `.lg` source files into Go packages. Unlike the standard bytecode compiler (which produces `.lgb` files or standalone binaries), `lg-compile` generates a tree of `.go` files with **direct inter-package function calls** (`pkg.Fn(ec, ...)` in Go) instead of runtime trampoline indirection.

This is useful for embedding let-go-authored code as native Go libraries, reusing let-go logic from Go programs, or compiling multi-file let-go projects to a Go package hierarchy.

## Usage

```bash
./lg scripts/lg-compile <out-dir> <import-prefix> <file.lg>...
```

**Parameters:**

- `<out-dir>` — output directory for the generated Go package tree
- `<import-prefix>` — Go import path prefix (each package is `<import-prefix>/<reldir>`)
- `<file.lg>...` — one or more `.lg` files to compile

**Example:**

```bash
./lg scripts/lg-compile /tmp/out github.com/example/generated-api \
  api/core.lg api/handlers.lg
```

Each `.lg` file's namespace becomes a Go package under `<out-dir>`. For example:

- `api/core.lg` (ns `api.core`) → `<out-dir>/api/core/core.go` (package `core`)
- `api/handlers.lg` (ns `api.handlers`) → `<out-dir>/api/handlers/handlers.go` (package `handlers`)

The generated Go packages are importable:

```go
import "github.com/example/generated-api/api/core"

// Call compiled let-go functions directly
result, err := core.MyFunction(ec, arg1, arg2)
```

## Compile Paths Comparison

| Path | Command | Output | Use Case |
|------|---------|--------|----------|
| **Bytecode** | `lg -c app.lgb app.lg` | `.lgb` (binary module) | Distribute bytecode, run with `lg app.lgb` |
| **Standalone binary** | `lg -b myapp app.lg` | Self-contained executable | Single-file distribution, no let-go runtime needed |
| **WASM** | `lg -w site app.lg` | `index.html` (~6MB, embedded bytecode + WASM) | Web apps, browser deployment |
| **Go package** | `lg scripts/lg-compile <out> <prefix> app.lg` | `.go` package tree | Embed in Go programs, direct function calls |

## How It Works

`lg-compile` (a let-go script) orchestrates the full-program lowering pipeline:

1. **Parse** each `.lg` file into source forms
2. **Intern** all namespaces (so cross-namespace symbol resolution works)
3. **Compile** each form through the standard IR pipeline (`ir.passes.pipeline/compile-form`)
4. **Lower to Go AST** using `ir.lower-go/lower` (converting IR to Go code)
5. **Emit `.go` files** organized by namespace/package, with:
   - Go function stubs for each let-go defn (accepting `*ExecutionContext` as first argument)
   - Direct inter-package calls where both functions are in the generated tree
   - Fallback trampolines for functions not eligible for direct calls (e.g., variadic functions)
   - Necessary imports and Go build scaffolding

The generated code is valid Go that can be imported and linked into any Go program. Functions accept an `*ExecutionContext` (runtime state) and return `(vm.Value, error)`.

## Cross-Package Calls

When function A (in package `api.core`) calls function B (also in the generated tree, in package `api.handlers`), `lg-compile` emits a direct Go call:

```go
result, err := handlers.MyFunction(ec, arg1, arg2)  // direct call, not trampoline
```

This avoids runtime Var lookups and enables inlining by Go's compiler. Functions not eligible for direct calls (e.g., variadic) fall back to cached-var trampolines at runtime.

## Citations

[1] **lg-compile** — AOT compiler to Go packages (let-go script)  
https://github.com/nooga/let-go/blob/main/scripts/lg-compile

[2] **ir.lower-go** — IR → Go AST lowering (let-go module)  
https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/lower_go.lg

[3] **Bytecode Compiler** (this wiki)  
[bytecode-compiler.md](bytecode-compiler.md)

[4] **WASM Compilation** (this wiki)  
[wasm-compilation.md](wasm-compilation.md)

[5] **let-go** (this wiki)  
[../entities/let-go.md](../entities/let-go.md)

---

See also: [Bytecode Compiler](bytecode-compiler.md), [WASM Compilation](wasm-compilation.md), [let-go](../entities/let-go.md)
