---
type: Concept
category: concept
title: "Indexed-RPN IR"
description: "let-go's intermediate representation: an indexed-RPN (postfix) encoding — an SSA-equivalent form — with block-parameter control flow."
tags: [compiler, bytecode, vm]
resource: "https://github.com/nooga/let-go/blob/main/pkg/ir/ir_ops.lg"
sources: ["repo: nooga/let-go pkg/ir/ir_ops.lg (source) + pkg/ir/op_generated.go (generated), 2026-07-02"]
created: "2026-07-02"
updated: "2026-07-02"
status: stable
---

# Indexed-RPN IR

The let-go compiler generates an intermediate representation using **indexed reverse Polish notation (RPN)** — a postfix encoding where a value's identity is determined by its position (index) on the RPN evaluation stack. This is an SSA-equivalent form: each value flows exactly once from producer to consumer, enabling program analysis without resorting to explicit SSA renaming. Control flow is managed through **block parameters**, which provide an SSA-style channel for values crossing block boundaries. Together, indexed-RPN encoding and block-parameter control flow form a compact, analyzable IR suitable for bytecode generation and Go code emission.

## Encoding

Indexed-RPN encodes computation as a sequence of operations that work on an implicit postfix stack during a single linear walk. Each operation pops a fixed number of operand values (its **stack-in** arity) and pushes either zero or one result value. A value's identity is its **position** — the index of the instruction that produced it — not an explicit name. This indexing scheme gives indexed-RPN its SSA-equivalence: the producer of a value is implicit (the defining instruction), and consumers simply reference the index.

Each operation in let-go's IR is catalogued in `pkg/ir/ir_ops.lg` and generated into `pkg/ir/op_generated.go`. The catalogue defines four properties per operation:

- **`name`** — human-readable operation kind (e.g., `Add`, `Call`, `Return`)
- **`stackIn`** — number of operand values popped from the stack (or `-1` for variable arity)
- **`stackOut`** — number of result values pushed (0 or 1)
- **`pure`** — boolean flag controlling whether this operation is eligible for common subexpression elimination (CSE), constant folding, or loop hoisting

### Representative Operations

**OpConst** (stack-in: 0, stack-out: 1, pure: true)  
Pushes a constant value. The constant itself is stored in the operation's `Aux` field as a `vm.Value`. Lowering materializes it as `OP_LOAD_CONST` with an interned pool index.

**OpAdd, OpSub, OpMul** (stack-in: 2, stack-out: 1, pure: true)  
Binary arithmetic operations. Pop two operands from the stack, push their computed result. Marked `pure` so optimization passes may fold constant operands, hoist invariant arithmetic out of loops, or eliminate redundant computations via CSE.

**OpCall** (stack-in: -1, stack-out: 1, pure: false)  
Invokes a function with a variable number of arguments. The function operand and arguments are in `Refs`; the arity is in `Aux`. Marked not pure (side-effecting), so optimization passes will not eliminate or relocate calls.

**OpReturn, OpBranch, OpBranchIf** (stack-out: 0, terminator: true)  
Control-flow operations that end basic blocks. `OpReturn` pops a value and exits the function; `OpBranch` and `OpBranchIf` direct control to successor blocks (potentially with arguments).

## Block-Parameter Control Flow

While indexed-RPN encoding provides value numbering within a block, **block parameters** handle values that cross block boundaries. When a block is branched into, its entry parameters receive values from the predecessor's branch arguments. This mirrors SSA φ functions but is expressed structurally: a block's parameter list is a sequence of entry points, each bound to an argument passed by a branching predecessor.

In contrast to the indexed-RPN encoding (where producers and consumers are in the same linear sequence), block parameters create a distinct channel: a value produced in block A may flow to block B via a branch with arguments, where it is bound as a parameter in B's entry sequence and accessed via `OpBlockArg`. This design cleanly separates **intra-block computation** (indexed RPN) from **inter-block value flow** (block parameters), both grounded in SSA principles but avoiding the explicit renaming overhead of full SSA.

## Citations

[1] **Burak Emir, "Indexed Reverse Polish Notation"**  
https://burakemir.ch  
The foundational design for positional value numbering in postfix form.

[2] **Carbon Language Semantic IR**  
https://github.com/carbon-language/carbon-lang/tree/trunk/toolchain/sem_ir  
A reference implementation of block-parameter SSA.

[3] **Swift SIL, Cranelift, MLIR**  
All employ block-parameter control flow for cross-block SSA-style value threading.

[4] **let-go IR source (op catalogue)**  
[pkg/ir/ir_ops.lg](https://github.com/nooga/let-go/blob/main/pkg/ir/ir_ops.lg) — the operations are defined here (in let-go), and generated into [pkg/ir/op_generated.go](https://github.com/nooga/let-go/blob/main/pkg/ir/op_generated.go) (which carries the design-references header).

---

See also: [Stack VM](stack-vm.md), [let-go](../entities/let-go.md)
