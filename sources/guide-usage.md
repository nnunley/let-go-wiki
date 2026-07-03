---
type: Source
category: source
title: "let-go usage guide"
description: "Operational guide for running, compiling, and distributing let-go programs."
tags: [tooling, bytecode, wasm, compiler, reference]
resource: "https://github.com/nooga/let-go/blob/main/docs/guide/usage.md"
sources: ["repo: nooga/let-go docs/guide/usage.md, 2026-07-03"]
created: "2026-07-03"
updated: "2026-07-03"
status: stable
---

# guide-usage

Official documentation covering how to run, compile, and distribute [let-go](../entities/let-go.md) programs.

## What this covers

The guide documents the complete lifecycle of a let-go program:
- **Running programs**: REPL, expression evaluation, file execution with arguments
- **Bytecode and standalone binaries**: Compiling to [bytecode-compiler](../concepts/bytecode-compiler.md) format and bundling self-contained executables
- **WASM compilation**: Generating web apps with full terminal emulation via xterm.js and COOP/COEP headers for SharedArrayBuffer
- **Compile-time evaluation**: Controlling side effects via `*compiling-aot*` and `*in-wasm*` flags
- **Project management**: Using [lgx](../projects/lgx.md) as a dependency resolver, build tool, and test runner

## Key takeaways

- let-go supports interactive (REPL) and compiled (-c bytecode, -b binary, -w WASM) distribution modes
- Standalone binaries are portable copies of the `lg` runtime with bytecode appended—no let-go installation required at runtime
- WASM output includes a service worker for GitHub Pages compatibility and xterm.js for terminal programs
- The `*compiling-aot*` flag separates compile-time setup from runtime execution
- lgx provides a git-based, multi-file project workflow with scaffolding and task running

## Derived pages

[bytecode-compiler](../concepts/bytecode-compiler.md) · [let-go](../entities/let-go.md) · [wasm-compilation](../concepts/wasm-compilation.md) · [lgx](../projects/lgx.md)

## Citations

Source: https://github.com/nooga/let-go/blob/main/docs/guide/usage.md (verified 2026-07-03)
