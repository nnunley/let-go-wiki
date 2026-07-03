---
type: Concept
category: concept
title: "IR Optimization Passes"
description: "Lisp-implemented optimization passes that transform the semantic IR to improve runtime performance."
tags: [compiler, bytecode, vm]
resource: "https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/passes/pipeline.lg"
sources: ["design: docs/superpowers/specs/2026-05-22-sem-ir-passes-design.md (local, 2026-07-02)"]
created: "2026-07-02"
updated: "2026-07-02"
status: stable
---

## What they are

IR optimization passes are a pipeline of Lisp-implemented transformations that operate on [let-go](../entities/let-go.md)'s semantic intermediate representation (sem-IR). Each pass is a self-contained optimization: constant folding, dead-code elimination, loop hoisting, type inference. They run sequentially on a Function, mutating it in place, before the IR is lowered to bytecode or Go.

Individual pass implementations live in `/pkg/rt/core/ir/passes/` (constfold.lg, cse.lg, dce.lg, licm.lg, etc.), with the core DSL definition `passes.lg` at `/pkg/rt/core/ir/passes.lg`. All are written entirely in let-go's own dialect — a departure from the bytecode compiler (which is Go), and a step toward self-hosting.

## When they matter

Optimizations improve runtime performance by eliminating redundant computation. A trivial form like `(+ 1 2)` folds to the constant `3` at compile time. A loop that loads the same value repeatedly has that value hoisted outside the loop. Dead instructions from aggressive inlining get pruned away. Collectively, these passes can reduce the bytecode output significantly and improve the quality of the [indexed-rpn-ir](indexed-rpn-ir.md) that feeds the [stack-vm](stack-vm.md).

Optimization is mandatory in the production pipeline: every function built via compile-form* unconditionally chains `ir.build/build-fn` with `optimize-fn` (see `pkg/rt/core/ir/passes/pipeline.lg` lines 455, 466, 479). There is no runtime flag to disable passes for debugging.

## Pass DSL and structure

All passes use a unified macro called `(defpass ...)`, defined in `passes.lg`. The macro abstracts away the zipper-based traversal logic and provides three helpers:

- `(replace-refs! refs)` — rewrite an instruction's operand references
- `(replace-aux! aux)` — change auxiliary data (constants, jump targets, etc.)
- `(remove!)` — drop the current instruction from its block

A pass author writes only the pattern-matching and rewrite logic:

```clojure
(defpass my-optimization
  "One-sentence summary."
  [inst]                    ; inst is the current InstId
  (let [f  ir.passes/*current-fn*
        op (ir/op inst f)]
    (when (= op :some-op)
      ;; analyze inst, then mutate it via helpers above
      )))
```

Inside the body, three dynamic variables are bound: `*current-fn*` (the Function being transformed), `*current-inst*` (the InstId of this instruction), and `*current-zip*` (the zipper cursor for multi-block traversals).

## The standard pipeline

The production optimization pipeline (`optimize-fn` in `passes/pipeline.lg`) runs in this order:

1. **Type inference** (`typeinfer` + `infer-arg-types`) — abstract-interpret types across the function
2. **Constant folding** — fold arithmetic over constants and apply algebraic identities like `(+ x 0) → x`
3. **Common-subexpression elimination (CSE)** — within a block, reuse the result of identical expressions
4. **Constant folding** (again) — CSE may expose new foldable patterns
5. **Loop-invariant code motion (LICM)** — hoist pure instructions out of loops to pre-headers
6. **Constant folding** (again) — LICM rearrangement may enable new folds
7. **Dead-code elimination (DCE)** — remove effect-free instructions with no uses
8. **Type inference** (again) — refine types after all rewriting

Multiple constant-folding passes exploit a key insight: CSE and LICM rearrange code in ways that create new folding opportunities. Running fold multiple times catches these cascading optimizations without explicit fixed-point iteration.

## Key passes

### Constant folding

Reduces Const-to-Const operations at compile time. Three strategies, tried in order:

1. **Primitive fold**: `(+ 3 5)` → `8`
2. **Algebraic identities**: `(* x 1)` → `x`, `(+ x 0)` → `x`, `(* x 0)` → `0`
3. **Commutative canonicalization**: `(+ 5 x)` → `(+ x 5)` (constants shift right for stable comparison)

Implemented in `passes/constfold.lg`.

### Dead-code elimination (DCE)

Removes effect-free instructions that have no uses. DCE is iterative: removing one instruction can make its operands dead. Uses the purity analysis (`purity.lg`) to determine which instructions are safe to remove.

Implemented in `passes/dce.lg`.

### Common-subexpression elimination (CSE)

Within a single block, if two instructions have the same opcode and operands, only compute once and reuse the result. CSE deliberately stays within block boundaries — cross-block CSE would require dominance-based analysis and is deferred.

Implemented in `passes/cse.lg`.

### Loop-invariant code motion (LICM)

For instructions whose operands never change within a loop, hoist them to the loop pre-header (the unique block that dominates the loop entry and is not part of the loop). LICM uses dominance analysis and is the key proof that block-arg threading (cross-block value threading via branch arguments) works correctly.

Implemented in `passes/licm.lg` and requires dominance computation from `dominance.lg`.

### Type inference

Abstract-interprets the types of values through the function, tracking whether each instruction is an integer, function, vector, etc. Type inference is two-phase: first pass over block arguments to infer parameter types, then a general forward pass. Results are stored in each instruction's `:type` field and inform other passes (e.g., DCE uses type stability to determine if a load is safe to remove).

Implemented in `passes/typeinfer.lg` and `passes/infer-arg-types.lg` with lattice operations in `lattice.lg`.

## IR mutation invariants

All passes obey these rules:

- **Instruction identity is stable.** Once `ir/add-inst` assigns an InstId, that ID never refers to a different instruction in the same Function. Removals mark the slot invalid but don't compact the array (following the Carbon language design).
- **Uses cache invalidates on mutation.** Any mutation (rewrite, remove) flips a dirty flag. The next call to `ir/uses` rebuilds the def→use index.
- **Span union on replacement.** When an instruction is replaced, its source-info spans are merged with the spans of the new instruction (preserving debugging fidelity).
- **Mutations are side-effects in place.** IR is mutable; passes return the same Function atom, now transformed.

## IR data layer

Passes interact with the IR through accessor functions defined in `data.lg` and exposed under the `ir/` namespace:

- **Inspection**: `ir/op`, `ir/refs`, `ir/aux`, `ir/blocks`, `ir/block-insts`, `ir/block-params`, `ir/block-preds`
- **Mutation**: `ir/replace-op!`, `ir/set-refs!`, `ir/set-aux!`, `ir/replace-all-uses!`, `ir/remove-inst!`
- **Uses index**: `ir/uses`, `ir/invalidate-uses!`

The Function is represented as a Lisp atom holding a map with `:name`, `:arity`, `:insts` (vector of instructions), `:blocks` (vector of blocks), and metadata. Each instruction is a tuple `[op refs aux block source-infos type]`.

## Design notes

The pass pipeline was redesigned (spec in `2026-05-22-sem-ir-passes-design.md`) to solve a critical limitation in the prior implementation: block-arg threading. The old design couldn't express cross-block value flow (e.g., a loop-hoisted instruction used in multiple blocks). The new design makes block arguments first-class in the IR, allowing passes like LICM to express their transformations correctly and for Lower to emit correct bytecode.

Writing passes in Lisp (not Go) is part of a longer self-hosting trajectory: eventually, the entire compilation pipeline (Build, passes, lowering) will live in let-go's dialect, with Go providing only the VM substrate and interop bridges.

# Citations

**Resource**: [pkg/rt/core/ir/passes/pipeline.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/passes/pipeline.lg) — the main pipeline driver and pass composition.

**Passes** (each in `pkg/rt/core/ir/passes/`):
- `constfold.lg` — constant folding + algebraic identities
- `cse.lg` — per-block common-subexpression elimination
- `dce.lg` — dead-code elimination (iterative)
- `licm.lg` — loop-invariant code motion with dominance
- `typeinfer.lg` and `infer-arg-types.lg` — type inference
- `purity.lg` — effect analysis (used by DCE and others)

**Infrastructure**:
- `passes.lg` — `defpass` macro and pass-author helpers
- `data.lg` — IR data structure and accessor functions
- `zipper.lg` — block-order cursor over instructions
- `dominance.lg` — immediate dominators and postdominators
- `dump.lg` — debugging dump format

**Design doc**: `docs/superpowers/specs/2026-05-22-sem-ir-passes-design.md` (local, 2026-07-02) — comprehensive spec covering architecture, per-pass detail, phasing, and testing strategy.
