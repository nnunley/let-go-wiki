---
type: Source
category: source
title: let-go Source Tree
description: "The core packages of the let-go bytecode compiler and stack VM."
tags: [runtime, vm, compiler, bytecode, reference]
resource: "https://github.com/nooga/let-go/tree/main/pkg"
sources: ["repo: nooga/let-go pkg/, 2026-07-03"]
created: "2026-07-03"
updated: "2026-07-03"
status: stable
---

The let-go project is a Clojure dialect compiled to bytecode and executed on a stack-based virtual machine, all written in Go. The source tree in `pkg/` contains the core compilation and runtime infrastructure.

## What the source is

The `/pkg` directory holds thirteen main packages forming the compilation pipeline and runtime:

**Compilation pipeline:**
- **`compiler/`** — the Clojure/Lisp reader and compiler. Parses source code into an AST, performs variable scoping and closure analysis, compiles forms to bytecode instructions emitted into code chunks. Handles macros, special forms, and error reporting.

- **`ir/`** — the intermediate representation (IR) layer: an SSA (static single-assignment) form with block-arg-style branches, sitting between the source compiler and bytecode VM. Includes IR optimization passes (in subdirectories and Lisp DSL files) for constant folding, common-subexpression elimination (CSE), dead-code elimination (DCE), loop-invariant code motion (LICM), and type inference. Passes run after IR is built and before lowering to bytecode.

- **`bytecode/`** — serialization and deserialization of compiled bytecode to/from `.lgb` binary format. The encoder and decoder handle the module format that bundles code chunks, constants, and metadata.

**Runtime:**
- **`vm/`** — the bytecode virtual machine. Defines opcodes, the stack-based execution engine, code chunks (instruction streams), constants tables, and runtime values (nil, symbols, keywords, numbers, collections).

- **`rt/`** — the core runtime and standard library. Includes `rt/core/` (.lg Clojure source stubs and Go-lowered implementations) for persistent data structures, lazy sequences, transducers, protocols, records, multimethods, `core.async`. Also contains native implementations in Go (http.go, json.go, os.go, pods.go, etc.) that are registered as built-in functions. The architecture is primarily Go-lowered: `core.lg` explicitly notes it has been compiled to Go, reducing Lisp implementation burden while retaining bootstrappable Clojure-like semantics.

**Distribution and tools:**
- **`bundle/`** — the standalone-binary format. Defines the trailer appended to `lg` executables when bundling programs with `lg -b`: contains the bytecode payload and optional resource archive, enabling self-contained distribution.

- **`nrepl/`** — an nREPL server for editor integration (Emacs/Calva/Neovim). Listens on a TCP port, processes evaluation requests, and routes output back to clients.

**Infrastructure and support packages:**
- **`api/`** — public Go API for embedding let-go in Go programs. Provides interfaces for running bytecode, managing execution contexts, and interoperating with Go functions and types.

- **`buildmeta/`** — build metadata and versioning. Captures compiler version, build timestamp, and other metadata embedded in compiled artifacts.

- **`errors/`** — error types and error handling utilities for compilation and runtime.

- **`genmanifest/`** — manifest generation for deployed programs. Tracks compiled artifacts, dependencies, and deployment metadata.

- **`perfdata/`** — performance profiling and metrics collection. Captures runtime statistics for optimization and debugging.

- **`resolver/`** — namespace and module resolution. Resolves imports, manages load paths, and handles module dependencies during compilation.

## Key takeaways

1. **Two-phase compilation**: source is first compiled to an intermediate IR representation for optimization, then lowered to bytecode instructions.

2. **IR-first optimization**: the IR layer includes optimization passes for constant folding, CSE, DCE, LICM, and type inference. Passes are implemented in Lisp (`.lg` DSL files in `rt/core/ir/passes/`) and as Go tests, keeping the compiler extensible.

3. **Go-lowered runtime**: the architecture is primarily Go-implemented. Core.lg has been Go-lowered for performance; most stdlib namespaces (http, json, os, pods, async, etc.) are implemented as native Go functions at the `/pkg/rt/` level and registered as built-ins. A small number of Clojure source stubs remain in `rt/core/` for code that benefits from Clojure semantics.

4. **Serializable bytecode**: the `bytecode` and `bundle` packages enable AOT compilation to `.lgb` files and standalone binaries, supporting distribution without the `lg` binary.

5. **nREPL integration**: the `nrepl` server bridges the VM to mainstream editors, unifying the REPL experience with Clojure tooling.

## Derived pages

[stack-vm](../concepts/stack-vm.md) · [bytecode-compiler](../concepts/bytecode-compiler.md) · [ir-pipeline](../concepts/ir-pipeline.md) · [nrepl-server](../concepts/nrepl-server.md) · [exec-context](../concepts/exec-context.md)

## Citations

**Resource**: https://github.com/nooga/let-go/tree/main/pkg  
**Repo path**: `/pkg` (13 main packages)  
**Date accessed**: 2026-07-03
