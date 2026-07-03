---
type: Source
category: source
title: "Block-Parameter SSA Family"
description: "Swift SIL, Cranelift, and MLIR — three compiler IRs that employ block parameters instead of phi nodes for SSA-style cross-block value threading."
tags: [compiler, bytecode, reference]
resource: "https://mlir.llvm.org/"
sources: ["https://mlir.llvm.org/", "https://docs.wasmtime.dev/", "https://github.com/apple/swift"]
created: "2026-07-03"
updated: "2026-07-03"
status: speculative
---

# Block-Parameter SSA Family

Three compiler intermediate representations — **Swift SIL**, **Cranelift**, and **MLIR** — share a common approach to control flow: they use **block parameters** to express SSA-style value threading across block boundaries, rather than explicit phi nodes.

## Shared Concept

Traditional SSA uses phi functions as merge points at block entries to reconcile values from multiple predecessors. The block-parameter family instead expresses this structurally: a block declares an entry parameter sequence, and each branching predecessor passes arguments to that block. The values are bound as parameters at block entry, accessed within the block as `OpBlockArg` or similar. This approach is SSA-equivalent (single-assignment, producer–consumer tracking) but avoids the explicit renaming overhead and is more naturally aligned with instruction-stream encodings (like indexed-RPN or linear IR).

## Design Contribution

By decoupling intra-block computation (value numbering on a postfix stack or linear sequence) from inter-block value flow (block parameters), this family achieves:

- **Compact representation**: Values flowing between blocks are bound structurally, not via intermediate rename maps.
- **Direct analysis**: A block's entry parameters directly reveal its dependencies, and dominance/control-flow analysis works on the block graph without resolving phi functions.
- **SSA equivalence**: Each value has exactly one definition point and may be consumed anywhere reachable from that definition, maintaining single-assignment semantics.

Let-go's indexed-RPN IR adopts the same pattern: indexed-RPN handles intra-block computation, and block parameters handle inter-block value flow.

## Derived pages

- [Indexed-RPN IR](../concepts/indexed-rpn-ir.md)

## Citations

[1] **Swift SIL** (Apple)  
https://github.com/apple/swift  
Swift's compiler intermediate representation that employs block parameters for SSA-form control flow.

[2] **Cranelift** (Bytecode Alliance)  
https://docs.wasmtime.dev/  
A code generator for WebAssembly (embedded in Wasmtime) that uses block parameters as the foundation of its IR's SSA representation.

[3] **MLIR** (LLVM)  
https://mlir.llvm.org/docs/LangRef/  
The Multi-Level Intermediate Representation framework, which uses block arguments (block parameters) as a central structural element across its dialects for SSA-form control flow.
