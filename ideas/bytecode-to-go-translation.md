---
type: Idea
category: idea
title: "Bytecode-to-Go Translation"
description: "Translate let-go bytecode (.lgb) to idiomatic Go source code, enabling faster/native execution paths alongside the stack VM."
tags: [compiler, go, bytecode]
resource: "https://github.com/nooga/let-go#goals"
sources: ["repo: nooga/let-go README (Goals), pkg/rt/core/ir/lower_go.lg (existing Go lowering), pkg/compile (bytecode compiler), 2026-07-02"]
created: "2026-07-02"
updated: "2026-07-02"
status: speculative
---

# Bytecode-to-Go Translation

## What It Is

Translate let-go **bytecode** (`.lgb` binary format) into idiomatic Go source code. This is separate from and complementary to [lg-compile](../concepts/lg-compile.md), which AOT-compiles `.lg` **source** files to Go. This idea targets the other direction: take a pre-compiled `.lgb` file and emit Go code that directly executes the same bytecode instructions.

The result is a `.go` file (or package) with Go functions that inline the bytecode dispatch logic, allowing the compiled form to run natively without the [Stack VM](../concepts/stack-vm.md) interpreter overhead.

## Why It Matters

- **Performance**: Bytecode interpretation has inherent dispatch overhead. Native Go code for tight loops can be substantially faster.
- **Integration**: Go projects can ship precompiled `.lgb` artifacts and generate Go bindings at build time, bridging compiled Clojure and native Go without requiring the VM.
- **Optimization opportunity**: The Go compiler can inline, branch-predict, and apply escape analysis to the generated code, further accelerating hot paths.
- **Single-binary deployment**: A let-go project can be AOT-compiled to `.lgb`, then translated to Go and bundled as a native binary with no runtime layer.

## Building Blocks in Place

- **[Bytecode Compiler](../concepts/bytecode-compiler.md)**: The `.lg` → `.lgb` pipeline exists and produces a well-defined bytecode format. The bytecode instruction set is stable and documented.
- **[Stack VM](../concepts/stack-vm.md)**: The reference interpreter (dispatch loop in Go) implements every bytecode opcode. The VM semantics define what the translated code must replicate.
- **[IR Pipeline](../concepts/ir-pipeline.md)** and existing **Go lowering** (`pkg/rt/core/ir/lower_go.lg`): The IR framework already has a `lower_go` path that emits Go code from the intermediate representation. This leg of the pipeline is a related building block for reference.
- **[lg-compile](../concepts/lg-compile.md)**: Existing tool that emits Go from `.lg` source. The infrastructure for Go code generation (Go AST, formatting, packages) is proven.

## Key Distinction from lg-compile

| Aspect | lg-compile | Bytecode-to-Go |
|--------|-----------|-----------------|
| **Input** | `.lg` source files | `.lgb` bytecode binary |
| **Compilation stage** | Source → IR → Go (skips bytecode) | Bytecode → Go (post-compile) |
| **Use case** | Reusable let-go libraries in Go projects | Deployment-time artifact → native binary |
| **Line-level source info** | Available (source forms) | Lost (only bytecode remains) |

## Open Questions

- **Instruction translation strategy**: Inline each bytecode op as Go code (switch + case per op), or generate a custom dispatch loop?
- **Value representation**: Reuse let-go's runtime `Value` type, or generate specialized Go types (for known numeric, string, or data types)?
- **Error handling**: How to map bytecode exception handling to Go panics / error returns?
- **Module/function boundaries**: Does each bytecode function become a Go function, or is the entire module one Go function?
- **Debuggability**: Without source locations in bytecode, how can the generated Go code preserve stack traces or source maps?

## Roadmap Motivation

From the README Goals: `[ ] Stretch: let-go bytecode → Go translation`. Marked as "Stretch" because it requires both understanding the full bytecode semantics and engineering a non-trivial code generator, but it unlocks a powerful deployment mode.

---

# Citations

[1] **README Goals** — the unchecked roadmap item  
https://github.com/nooga/let-go#goals

[2] **Bytecode Compiler** (this wiki)  
[bytecode-compiler.md](../concepts/bytecode-compiler.md)

[3] **Stack VM** (this wiki)  
[stack-vm.md](../concepts/stack-vm.md)

[4] **IR Pipeline** (this wiki)  
[ir-pipeline.md](../concepts/ir-pipeline.md)

[5] **lg-compile** (this wiki)  
[lg-compile.md](../concepts/lg-compile.md)

[6] **pkg/rt/core/ir/lower_go.lg** — existing Go lowering in the IR pipeline  
https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/lower_go.lg

[7] **pkg/compiler** — bytecode compiler  
https://github.com/nooga/let-go/tree/main/pkg/compiler

[8] **let-go** (this wiki)  
[let-go.md](../entities/let-go.md)

---

See also: [let-go](../entities/let-go.md), [Bytecode Compiler](../concepts/bytecode-compiler.md), [Stack VM](../concepts/stack-vm.md), [lg-compile](../concepts/lg-compile.md)
