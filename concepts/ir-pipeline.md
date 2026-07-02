---
type: Concept
category: concept
title: "IR Pipeline"
description: "let-go's compiler IR framework, written in let-go itself: building, optimizing, and lowering to bytecode."
tags: [compiler, bytecode, vm]
resource: "https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/README.md"
sources: ["repo: nooga/let-go pkg/rt/core/ir/README.md, pkg/rt/core/ir/*.lg (implementation), 2026-07-02"]
created: "2026-07-02"
updated: "2026-07-02"
status: stable
---

# IR Pipeline

let-go's intermediate representation (IR) sits between the source compiler and the bytecode VM. It is an SSA-equivalent form with block-parameter-style control flow, and **the entire IR framework is written in let-go**—demonstrating the language's capability for meta-programming and compiler construction.

The pipeline transforms source forms through IR stages, applies optimizations, and emits bytecode. Go provides only a small substrate (op table, chunk emission, value constructors) via bridge primitives in the `ir/` namespace; all algorithms and data structures live in Lisp.

## Pipeline Overview

```
    forms
      │
      ▼
ir.build/build-fn  ──►  Lisp-atom IR Function  ──►  ir.passes.pipeline/optimize-fn
                                                           │
                                                           ▼
                                                    optimized IR Function
                                                           │
                                                           ▼
                                                      ir.lower/lower
                                                           │
                                                           ▼
                                                     vm.CodeChunk (bytecode)
```

## Architecture

The IR framework spans multiple let-go files in `pkg/rt/core/ir/`:

| File | Role |
|------|------|
| `data.lg` | IR data layer: Function/Block/Inst atom shape, constructors, structural mutators, def→use cache |
| `data/generated.lg` | Mechanical field accessors (generated from Go spec) |
| `zipper.lg` | Fn-scoped cursor over instructions in block-order |
| `build.lg` | `ir.build/build-fn` — transforms source Lisp form to IR Function |
| `dump.lg` | Text dump for debugging |
| `dominance.lg` | Cooper/Harvey/Kennedy immediate-dominator analysis |
| `lower.lg` | IR → bytecode via chunk-emission bridge primitives |
| `passes.lg` | `defpass` DSL; binds `*current-fn*`, `*current-inst*`, `*current-zip*` |
| `passes/dce.lg` | Dead-code elimination |
| `passes/constfold.lg` | Constant folding + algebraic identities + commutative canonicalization |
| `passes/cse.lg` | Per-block common-subexpression elimination |
| `passes/licm.lg` | Loop-invariant code motion |
| `passes/thread-block-args.lg` | Pre-lower fixup for cross-block direct refs |
| `passes/typeinfer.lg` | Abstract-interpretation type inference |
| `passes/pipeline.lg` | Orchestrates passes; defines `compile-form` (end-to-end entry point) |

## Compilation Pipeline

**Step 1: Build**

```clojure
(ir.build/build-fn '(defn add [a b] (+ a b)))
; => Lisp atom with :name :arity :entry :blocks :insts :consts fields
```

The builder lowers Clojure forms into IR primitives: constants, block arguments, arithmetic ops, calls, and control-flow terminators.

**Step 2: Optimize**

```clojure
(ir.passes.pipeline/optimize-fn f)
; Applies: dce, constfold, cse, licm, typeinfer, thread-block-args in sequence
; Returns: optimized IR Function (same atom)
```

Each pass is defined with the `defpass` DSL, which binds a cursor over instructions and provides helpers like `replace-refs!`, `replace-aux!`, and `remove!`. Passes run in a fixed order, with some iterating until a fixed point.

**Step 3: Lower**

```clojure
(ir.lower/lower f)
; => boxed *vm.CodeChunk (bytecode)
```

Lowers the optimized IR to stack-machine bytecode via chunk-emission primitives (`ir/chunk-emit`, `ir/chunk-emit-with-arg`, etc.).

## Passes (via defpass DSL)

Each pass is a let-go function using the `defpass` macro:

```clojure
(defpass my-pass
  "Brief description."
  [inst]  ; binds inst to the current InstId
  (let [f  ir.passes/*current-fn*
        op (ir/op inst f)]
    (when (= op :add)
      ;; mutate or replace the current inst
      )))
```

The `defpass` macro binds:
- `*current-fn*` — the IR Function being optimized
- `*current-inst*` — the instruction ID
- `*current-zip*` — cursor for in-order block traversal

Helpers available:
- `replace-refs!` — change operand references
- `replace-aux!` — change auxiliary data
- `remove!` — delete the instruction

Built-in passes include:

- **DCE** — Remove unused instructions (marked non-pure, or with no consumers)
- **Constant Folding** — Evaluate pure ops with constant operands at compile time
- **CSE** — Eliminate redundant subexpressions within a block
- **LICM** — Hoist loop-invariant computations using dominance analysis
- **Type Inference** — Abstract-interpret types to guide dispatch decisions
- **Thread Block Args** — Pre-lower fixup to handle cross-block references

## IR Data Model

An IR Function is a Lisp atom:

```clojure
(ir/fn-name f)          ; => symbol
(ir/fn-arity f)         ; => int
(ir/fn-variadic? f)     ; => bool
(ir/fn-entry f)         ; => block-id (entry block)
(ir/fn-blocks f)        ; => vector of block-ids
(ir/block-insts bid f)  ; => vector of instruction-ids in order
(ir/block-term bid f)   ; => terminator instruction-id
```

Never reach into `@f` directly; use the accessor functions—they maintain abstraction and enable future optimizations.

## Extension: Adding an Optimization Pass

Create a new pass file, e.g., `passes/my-optimization.lg`:

```clojure
(ns ir.passes.my-optimization
  (:require [ir.passes :refer [defpass replace-refs!]]))

(defpass my-optimization
  "My new optimization."
  [inst]
  (let [f  ir.passes/*current-fn*
        op (ir/op inst f)]
    (when (some-condition? op)
      (replace-refs! [new-ref1 new-ref2]))))
```

Then add it to `passes/pipeline.lg`:

```clojure
(defn optimize-fn [f]
  ...
  (my-optimization f)
  ...
  f)
```

Wire it into the runtime bundle via `pkg/rt/irpasses.go` and `cmd/lgbgen/main.go`.

## Bridge Primitives (Go ↔ Lisp)

Go provides only the op-table queries and chunk-emission primitives:

- **Op Table**: `ir/op-terminator?`, `ir/op-pure?`, `ir/op-cheap-load?`, `ir/op-stack-out`
- **Chunk Emission**: `ir/chunk-emit`, `ir/chunk-emit-with-arg`, `ir/chunk-update!`, `ir/chunk-length`, `ir/chunk-max-stack!`
- **Value Constructors**: `ir/new-fn`, `ir/new-block`, `ir/new-inst`

Everything else (data structures, passes, analysis) is implemented in Lisp.

## Loading Order

The IR layer's load-time dance is normally invisible but worth knowing:

- `data.lg` is **not** in the precompiled bundle; it loads from source. The intern block at the bottom needs live function values to register accessors.
- `ir.build` declares `(:require ir.data)`, so loading build automatically triggers data's source load.
- At precompile time (`lgbgen`), `data.lg` is bootstrapped first so downstream namespaces can resolve `ir/*` symbols.

If you see "nil is not a function" errors during compilation, the most likely cause is that `data.lg` didn't finish loading before the caller compiled. Add `ir.data` to a `:require` clause or load it explicitly.

## Citations

[1] **IR framework README**  
https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/README.md

[2] **ir/ source code** (let-go implementations)  
https://github.com/nooga/let-go/tree/main/pkg/rt/core/ir

[3] **ir/lower_go.lg** — IR → Go AST lowering (for AOT compilation)  
https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/lower_go.lg

[4] **Indexed-RPN IR** (this wiki)  
[indexed-rpn-ir.md](indexed-rpn-ir.md)

[5] **Bytecode Compiler** (this wiki)  
[bytecode-compiler.md](bytecode-compiler.md)

[6] **Stack VM** (this wiki)  
[stack-vm.md](stack-vm.md)

[7] **let-go** (this wiki)  
[../entities/let-go.md](../entities/let-go.md)

---

See also: [Indexed-RPN IR](indexed-rpn-ir.md), [Bytecode Compiler](bytecode-compiler.md), [Stack VM](stack-vm.md), [let-go](../entities/let-go.md)
