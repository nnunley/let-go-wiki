---
type: Concept
category: concept
title: "Indexed-RPN IR"
description: "let-go's intermediate representation: an indexed-RPN (postfix) encoding — an SSA-equivalent form — with block-parameter control flow."
tags: [compiler, bytecode, vm]
resource: "https://github.com/nooga/let-go/blob/main/pkg/ir/ir_ops.lg"
sources: ["repo: nooga/let-go pkg/ir/ir_ops.lg (source) + pkg/ir/op_generated.go (generated), 2026-07-02", "repo: nooga/let-go pkg/ir/ir_ops.lg pkg/ir/op_generated.go pkg/ir/ir_data.lg pkg/ir/op_lookup.go pkg/ir/op_exports.go Makefile @ b82588292b, 2026-10-20"]
created: "2026-07-02"
updated: "2026-10-20"
status: stable
---

# Indexed-RPN IR

The let-go compiler's IR is described in the header of `pkg/ir/op_generated.go` as an **indexed reverse Polish notation (RPN)** IR with **block-parameter SSA** control flow. In the RPN encoding, an operation's operands are the values produced by earlier instructions, and a value's identity is the index of the instruction that produced it. Values that cross basic-block boundaries travel as branch arguments and are received as **block parameters**. The IR lowers to bytecode (`irOpToBytecode` in `op_generated.go`, exported as `IROpToBytecode` in `op_exports.go`) and to Go (the `lower-go` facet in `ir_ops.lg`).

## Encoding

An instruction (`defirdata Inst` in `pkg/ir/ir_data.lg`) has an op keyword, a `refs` vector of instruction IDs, an `aux` value, its home block, source infos, and a type. Instruction IDs index the `insts` vector of the enclosing `Function`: the generated getter reads `(nth (:insts @f) nid)`. A consumer names a producer by putting that ID in its `refs`.

Each operation is one row of the `ops` vector in `pkg/ir/ir_ops.lg`. The row has these columns, in order:

- **name**: the bare op name. `Op<name>` is the Go constant.
- **stack-in**: number of operand values (`-1` for variable arity).
- **stack-out**: number of result values (0 or 1).
- **pure?**: whether the op is safe to CSE, fold, or hoist.
- **terminator?**: whether the op ends a basic block.
- **bytecode**: the corresponding `vm.OP_*` symbol, or `nil`.
- **cheap?**: whether lowering may re-emit the op on demand (`Const`, `LoadArg`, `LoadVar`, `LoadClosed`).
- **local-carry?**: whether lowering materializes the result into a Go local.
- **infer?** and **lower?**: whether the op's typeinfer facet and lower-go facet are reified on an `ir.ops` op-type.
- **display** and **comment**: the `opTable` name and a trailing comment.

The generated `opInfo` struct carries `name`, `stackIn`, `stackOut`, `pure`, `terminator`, `localCarrying`, `inferFacet`, and `lowerFacet`. The generated accessors are `String`, `IsTerminator`, `IsPure`, `StackOut`, `LocalCarrying`, `InferFacet`, and `LowerFacet`. `Op` is a `uint16`, and `OpInvalid` is the zero value. The `ops` order is load-bearing: the `iota` values are positional. Reordering rows shifts the `iota` values of the rows after the change and breaks code that references `Op<X>` constants.

The header comment of `op_generated.go` describes stack-in as the number of values popped from the RPN-walk stack. The in-memory `Inst` stores operands explicitly in `refs`.

### Representative Operations

**OpConst** (stack-in: 0, stack-out: 1, pure: true, cheap: true)
Pushes a constant. The constant is stored in `Aux` as a `vm.Value`. The `op_generated.go` comment states that lowering emits it as `OP_LOAD_CONST` with an interned pool index.

**OpAdd, OpSub, OpMul** (stack-in: 2, stack-out: 1, pure: true)
Binary arithmetic. Each pops two operands and pushes one result. The `pure` flag marks them as safe to CSE, fold, or hoist.

**OpCall** (stack-in: -1, stack-out: 1, pure: false)
Invokes a function with a variable number of arguments. `Refs[0]` is the function, `Refs[1:]` are the arguments, and `Aux` is the arity. `pure` is false, so the op is not marked safe to CSE, fold, or hoist. The catalogue groups `Call` under "Side-effecting". `infer?` is false.

**OpReturn** (stack-in: 1, stack-out: 0, terminator: true)
Pops one value (`Refs[0]`) and exits the function.

**OpBranch** (stack-in: 0, stack-out: 0, terminator: true) and **OpBranchIf** (stack-in: 1, stack-out: 0, terminator: true)
Terminators. `OpBranch` has a `*BranchTarget` in `Aux`. `OpBranchIf` takes its condition in `Refs[0]` and has a true target and a false target in `Aux`. Each `BranchTarget` holds a target block and a `args` vector of per-parameter arguments.

**OpTailCall** and **OpRecurFn** are also terminators. `OpRecurFn` carries replacement arguments and no callee, and maps to `OP_RECUR_FN`.

**OpBlockArg** (stack-in: 0, stack-out: 1, pure: true, no bytecode)
Reads a block parameter. It has no `Refs`. Its identity is the pair (block, parameter index), given by its position in `Block.Params`.

**OpTry**, **OpDot** (no bytecode) exist only on the IR-to-Go lowering path. `ir_ops.lg` states that the bytecode VM compiles `try` natively via `OP_TRY_PUSH/POP`, and that `Dot` has no bytecode counterpart.

## Block-Parameter Control Flow

A `Block` (`defirdata Block` in `pkg/ir/ir_data.lg`) has an `id`, an ordered `params` vector, `insts`, `preds`, and a terminator `term`. Within a block, operands are referenced by instruction ID. Values that cross a block boundary go through branch arguments: a `BranchTarget` carries `args`, one per target parameter. The target block receives each value as a `BlockArg` op, and the op's position in `Block.Params` selects which parameter it reads.

The `ops` catalogue describes `BlockArg` as the value "flowing in from a predecessor's branch-with-args". The `op_generated.go` header describes the whole IR as block-parameter SSA, and cites Swift SIL, Cranelift, and MLIR as using block-parameter SSA for cross-block value flow.

## Regeneration

`pkg/ir/op_generated.go` is marked `Code generated by pkg/ir/ir_ops.lg. DO NOT EDIT.` The `Makefile` `generate` target runs `scripts/generate.lg`, which regenerates `pkg/ir/op_generated.go`, `pkg/rt/ir_bridge_generated.go`, and `pkg/rt/core/ir/data/generated.lg` (lines 150-152 of `scripts/generate.lg` at b82588292b). The Makefile states that this target replaces the former `generate-ir-{ops,bridge,data}.sh` scripts. The header comment of `ir_ops.lg` still says `Run with: lg pkg/ir/ir_ops.lg` and names `scripts/generate-ir-ops.sh`; that script is not in the tree at b82588292b. Helpers that `op_exports.go` exposes from the generated file (`IROpToBytecode`, `IsCheapMaterializeOp`) are kept in `op_exports.go` so that the generated file can be rewritten without hand edits.

`OpByKeyword` (`pkg/ir/op_lookup.go`) maps kebab-case keyword names to `Op` values. Its fast path is the generated `opByKeywordExact` string switch. A fallback scan matches non-canonical spellings case-insensitively and dash-insensitively.

## Citations

[1] **Burak Emir, "Indexed Reverse Polish Notation"**
https://burakemir.ch
Cited in the `pkg/ir/op_generated.go` header as a design reference for the indexed RPN encoding.

[2] **Carbon Language Semantic IR**
https://github.com/carbon-language/carbon-lang/tree/trunk/toolchain/sem_ir
Cited in the `pkg/ir/op_generated.go` header as a design reference.

[3] **Swift SIL, Cranelift, MLIR**
Cited in the `pkg/ir/op_generated.go` header as using block-parameter SSA.

[4] **let-go IR source (op catalogue)**
[pkg/ir/ir_ops.lg](https://github.com/nooga/let-go/blob/main/pkg/ir/ir_ops.lg) — the operations are defined here (in let-go), and generated into `pkg/ir/op_generated.go` (which carries the design-references header).

[5] **let-go IR data types**
[pkg/ir/ir_data.lg](https://github.com/nooga/let-go/blob/main/pkg/ir/ir_data.lg) — `Function`, `Block`, `Inst`, and `BranchTarget`.

[6] **let-go regeneration target**
[Makefile](https://github.com/nooga/let-go/blob/main/Makefile) — the `generate` target.

---

See also: [Stack VM](stack-vm.md), [let-go](../entities/let-go.md)
