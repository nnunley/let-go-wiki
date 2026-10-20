---
type: Concept
category: concept
title: "IR Pipeline"
description: "let-go's compiler IR framework, written in let-go itself: building, optimizing, and lowering to bytecode."
tags: [compiler, bytecode, vm]
resource: "https://github.com/nooga/let-go/blob/b82588292b/pkg/rt/core/ir/README.md"
sources:
  - "repo: nooga/let-go pkg/rt/core/ir/README.md, pkg/rt/core/ir/*.lg (implementation), 2026-07-02 (commit not recorded)"
  - "repo: nooga/let-go cmd/lgbgen/main.go @ 83931029 (bundle-skip mechanism; ir.data bootstrap moved after the bundle write by #838), cmd/lgbstat on pkg/rt/core_compiled.lgb @ a9c183f9 and 83931029, 2026-09-10"
  - "repo: nooga/let-go pkg/rt/core/ir/ (README.md, data.lg, build.lg, lower.lg, lower_go.lg, passes.lg, passes/*.lg, validate.lg), pkg/ir/ir_ops.lg, pkg/ir/ir_data.lg, pkg/ir/ir_bridge.lg, pkg/rt/ir_bridge_generated.go, pkg/rt/core_embed_fs.go, cmd/lgbgen/main.go, scripts/generate.lg, Makefile @ b82588292b, 2026-10-20"
created: "2026-07-02"
updated: "2026-10-20"
status: stable
---

# IR Pipeline

let-go's intermediate representation (IR) sits between the source compiler and the bytecode VM. It is an SSA IR with block-argument-style branches [1]. The IR's algorithms and data structures are written in let-go under `pkg/rt/core/ir/`. Go supplies only a small substrate: the op table, chunk-emission primitives, source-info primitives, and the constructors for the VM-side values (`vm.Consts`, `vm.SourceInfo`, chunks). These are exposed as bridge primitives in the `ir/` namespace [1][21].

The pipeline transforms source forms through IR stages, applies optimizations, and emits bytecode, or Go (see below).

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

`ir.passes.pipeline/compile-form` drives this sequence for a `defn` form. The lowering step is chosen by the `*target*` var, which selects an entry in the `lowerings` registry: `:bytecode` (the default) calls `(ir.lower/lower f)`, and `:go` calls `(ir.lower-go/lower f :bridge)` [8]. In `:bridge` mode, `lower-go/lower` returns a `{:status :fallback}` result for an unsupported form; in any other mode it throws [3].

## Architecture

The IR framework spans multiple let-go files in `pkg/rt/core/ir/`.

Core data, build, and lowering:

| File | Role |
|------|------|
| `data.lg` | IR data layer: Function/Block/Inst atom shape, constructors, structural mutators, def→use cache. Carries `;; lgbgen:skip` and loads from source. |
| `data/generated.lg` | Field accessors and mutators in `ir.data.generated`, generated from `pkg/ir/ir_data.lg` [9]. |
| `zipper.lg` | Fn-scoped cursor over instructions in block order. |
| `build.lg` | `ir.build/build-fn`: transforms a Lisp `defn` form into an IR Function. |
| `dump.lg` | Text dump for debugging. |
| `dominance.lg` | Cooper/Harvey/Kennedy immediate-dominator analysis. |
| `lower.lg` | `ir.lower/lower`: IR → bytecode via chunk-emission bridge primitives. |
| `lower_go.lg` | `ir.lower-go/lower`: IR → Go AST, for the `:go` target [3]. |
| `passes.lg` | `defpass` DSL; binds `*current-fn*`, `*current-inst*`, `*current-zip*`. |
| `passes/pipeline.lg` | `default-pass-list`, `optimize-fn`, and `compile-form` (the end-to-end entry point). |
| `validate.lg` | `validate-fn!`: checks the IR after build and after each labeled pass. |
| `ops.lg`, `lattice.lg` | IR ops reified as types with per-op facets; the type lattice used by type inference. |
| `forms.lg`, `form_heads.lg` | Compiler-only collection forms that keep source slots through macroexpansion; the catalog of special-form heads dispatched by `build-list`. |
| `structurize.lg` | Recovers structured control flow from the block-parameter CFG. |
| `coverage.lg` | Classification of lowering coverage failures. |

Passes and analyses (`passes/`):

| File | Role |
|------|------|
| `dce.lg` | Dead-code elimination. |
| `constfold.lg` | Constant folding, algebraic identities, commutative canonicalization. |
| `cse.lg` | Per-block common-subexpression elimination. |
| `licm.lg` | Loop-invariant code motion. |
| `legalize.lg` | Threads cross-block direct references through fresh block arguments. |
| `infer_arg_types.lg`, `typeinfer.lg` | Backward inference of `:load-arg` types; forward type inference. |
| `fusion.lg` | Loop fusion of `reduce` over `map`/`filter`/`remove`/`keep`. |
| `inline.lg` | Inlining of small, side-effect-free callees. Off by default. |
| `lambda_lift.lg` | Hoists inner `fn` literals to top-level sibling functions. |
| `purity.lg`, `mutability.lg`, `liveness.lg` | Analyses: effect-free and pure instruction queries, var-root stability, per-block liveness. |
| `blockarg.lg` | Block-argument classification. Reports a census and changes nothing. |
| `cleanup.lg` | Dead-code removal on the execution-form path, not in `optimize-fn`. |
| `entry_frame.lg` | Generates the package-main Go entry file for AOT builds. |
| `trace.lg` | Instrumentation: records per-pass instruction-count deltas and timing. |

Each file is one layer. Namespaces under `pkg/rt/core/` are embedded as source (see [Loading Order](#loading-order)).

## Compilation Pipeline

**Step 1: Build**

```clojure
(ir.build/build-fn '(defn add [a b] (+ a b)))
; => Lisp atom holding the Function map (:name :arity :variadic? :arg-types :entry :consts :insts :blocks), plus side tables :source-info and :types
```

`build-fn` takes a `defn` form and returns the Function atom. The builder lowers Clojure forms into IR primitives: constants, block arguments, arithmetic ops, calls, and control-flow terminators [1][12].

**Step 2: Optimize**

```clojure
(ir.passes.pipeline/optimize-fn f)
; 1. legalize-fn!, then validate-fn! "build"
; 2. inline, only when ir.passes.inline/*enable-inline* is true (default false)
;    and the inline registry is non-empty
; 3. default-pass-list, in order; validate-fn! after each labeled pass:
;      infer-arg-types + typeinfer (type epoch)
;      constfold-1, cse, fusion, constfold-2, licm, constfold-3, dce
;      type epoch (skipped when no pass changed the instruction or block vectors)
; Returns: the same Function atom
```

The list is `default-pass-list` in `passes/pipeline.lg` [10]. Each entry runs once, in list order. Three loops in this path iterate to a fixed point. `dce` sweeps until a sweep removes nothing [11]. LICM's invariant marking (`collect-hoistable`) repeats until no new instruction is marked [13]. When inlining is enabled, `inline-with` repeats until `inline-pass` returns false, up to `max-inline-rounds` = 64 [16]. Lambda-lifted siblings use `uniform-pass-list`, which omits the type epochs, so their bodies stay on the boxed `vm.Value` path [10].

**Step 3: Lower**

```clojure
(ir.lower/lower f)
; => boxed *vm.CodeChunk (bytecode)
```

Lowers the optimized IR to stack-machine bytecode via chunk-emission primitives (`ir/chunk-emit`, `ir/chunk-emit-with-arg`, etc.). It throws when a value defined in one block is used directly in another block and is not re-emittable at the use site. The re-emittable ops are the cheap loads (`:const`, `:load-arg`, `:load-closed`), excluding `:load-var` (the var root is mutable) and function-literal constants (they have identity). The predicate is `ir/reemittable-at-use?` in `data.lg` [17]. Branch-target arguments are the other allowed cross-block channel [12].

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

The `defpass` macro defines a function `(my-pass f)` that visits every instruction in zipper order and returns `f`. For each visit it binds:
- `*current-fn*` — the IR Function being optimized
- `*current-inst*` — the instruction ID
- `*current-zip*` — cursor for in-order block traversal

Helpers available inside a pass body:
- `replace-refs!` — change operand references
- `replace-aux!` — change auxiliary data
- `remove!` — delete the instruction

Passes in the default list:

- **DCE** (`dce`) — Removes an instruction that is effect-free (per `purity/effect-free-inst?`) and has no uses. Sweeps repeat until a sweep removes nothing, because removing an instruction can leave its operands unused [11].
- **Constant folding** (`constfold`) — Three strategies: primitive folding of pure ops with constant operands; algebraic identities such as `(+ x 0)` → `x`, `(* x 1)` → `x`, `(* x 0)` → `0`; commutative canonicalization that moves a constant operand to the right [13].
- **CSE** (`cse`) — Eliminates redundant instructions within a block, keyed on `(op refs aux)`. Walks blocks explicitly rather than through the zipper [13].
- **Fusion** (`fusion`) — Rewrites `(reduce g init (map|filter|remove|keep f coll))` into transducer form when `*enable-fusion*` is true (default true) [14].
- **LICM** (`licm`) — Finds natural loops from dominators and back edges, and hoists loop-invariant pure instructions and total-pure calls (calls to known builtins that do not throw) to a pre-header [13].
- **Type inference** (`infer-arg-types`, `typeinfer`) — Infers `:load-arg` types from their users' constraints, then abstract-interprets types over the lattice in `lattice.lg` and stores them on instructions [10].

Passes that run outside the default list:

- **Legalize** (`legalize-fn!`) — Runs first in `optimize-fn`. Repairs cross-block direct references by threading the value through fresh block arguments, and changes only the references the validator would reject [15].
- **Inline** (`inline`) — Inlines callees with at most 40 instructions that do not rebind var roots and are not self-recursive. Runs only when `*enable-inline*` is true, which is false by default [16].
- **Lambda lift** (`lambda-lift`) — Hoists inner `fn` literals to top-level siblings. Per the comment at `passes/pipeline.lg` line 128, it runs only on the `:go` path [10].

## IR Data Model

An IR Function is a Lisp atom holding a map with `:name` (String), `:arity`, `:variadic?`, `:arg-types`, `:entry` (BlockID), `:consts`, `:insts` (indexed by InstId), and `:blocks` (indexed by BlockID) [17]. It also holds the side tables `:source-info` and `:types`, both transient vectors indexed by instruction id [17]:

```clojure
(ir/fn-name f)          ; => String
(ir/fn-arity f)         ; => int
(ir/fn-variadic? f)     ; => bool
(ir/fn-entry f)         ; => block-id (entry block)
(ir/blocks f)           ; => vector of block-ids, in construction order
(ir/block-insts bid f)  ; => vector of instruction-ids in order
(ir/block-term bid f)   ; => terminator instruction-id
```

`ir/fn-blocks` is not in the `ir` namespace. The generated accessor of that name lives in `ir.data.generated` and returns Block maps, not IDs [17].

Never reach into `@f` directly; use the accessor functions. They keep the abstraction stable [1].

## Extension: Adding an Optimization Pass

Create a new pass file under `pkg/rt/core/ir/passes/`, e.g., `my-optimization.lg`:

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

Then require it in `passes/pipeline.lg` and add an entry to `default-pass-list`. Each entry is `[pass-fn validate-label]`, where the label names the validation step that runs after the pass. An entry may carry a third element, `:epoch`, which marks a type-inference epoch. A `nil` label runs the pass with no validation step [10]:

```clojure
(:require ... [ir.passes.my-optimization :refer [my-optimization]])

(def default-pass-list
  [...
   [my-optimization "my-optimization"]
   ...])
```

No Go file is needed. `pkg/rt/core_embed_fs.go` embeds the whole `pkg/rt/core` tree with `//go:embed all:core`, so a new `.lg` file under that tree is embedded automatically [18]. The `ir.*` namespaces are left out of `core_compiled.lgb` and load from source when required (see [Loading Order](#loading-order)) [19].

Passes that need block-level state, such as CSE's per-block table, walk blocks explicitly with `(doseq [bid (ir/blocks f)] ...)` rather than using the `defpass` cursor [13].

## Adding an IR Op, Data Field, or Bridge Primitive

- **Op:** add a row to the `ops` vector in `pkg/ir/ir_ops.lg`, then run `make generate`. That regenerates `pkg/ir/op_generated.go` [9]. Update `build.lg` and `lower.lg` where the op must be built or lowered.
- **Data field:** add the field to the `defirdata` block in `pkg/ir/ir_data.lg`, then run `make generate`. That regenerates `pkg/rt/core/ir/data/generated.lg` [9]. Update `data.lg` if structural operations must initialize the field.
- **Bridge primitive:** add an `:extras` entry to `pkg/ir/ir_bridge.lg`, then run `make generate`. That regenerates `pkg/rt/ir_bridge_generated.go` [9].

`make generate` runs `scripts/generate.lg`, which produces all three generated artifacts [9][20].

## Bridge Primitives (Go ↔ Lisp)

Go provides the op-table queries, the chunk-emission primitives, the source-info primitives, and the constructors for the VM-side values. The list below is every `:lisp-name` entry in `pkg/ir/ir_bridge.lg` at b82588292b [21]:

- **Op table:** `ir/op-terminator?`, `ir/op-pure?`, `ir/op-cheap-load?`, `ir/op-stack-out`, `ir/op-local-carrying?`, `ir/op-infer-facet?`, `ir/op-lower-facet?`, `ir/op-kws` [21]
- **Chunk emission:** `ir/chunk-emit`, `ir/chunk-emit-with-arg`, `ir/chunk-emit-placeholder`, `ir/chunk-emit-dup-nth`, `ir/chunk-emit-recur`, `ir/chunk-update!`, `ir/chunk-length`, `ir/chunk-max-stack`, `ir/chunk-set-max-stack!`, `ir/chunk-intern-const`, `ir/chunk-add-source-info!` [21]
- **Value constructors:** `ir/new-consts`, `ir/new-chunk`, `ir/new-source-info`, `ir/new-named-source-info` [21]
- **Source info:** `ir/form-source-info`, `ir/source-info-symbol` [21]

Everything else is implemented in Lisp. `ir/new-fn`, `ir/new-branch-target`, and `ir/new-cond-target` are defined in `data.lg`, and the structural mutators (`ir/add-inst`, `ir/add-block`, `ir/set-refs!`, and others) are also defined there and re-interned into `ir` [17].

## Loading Order

The IR layer's load-time behavior is worth knowing when a compile fails with "nil is not a function."

- `data.lg` is excluded from the precompiled bundle by its `;; lgbgen:skip` directive. Its intern block at the bottom needs live function values to register the `ir/*` accessors, so it loads from source on demand [17][19].
- The other `ir.*` namespaces are excluded by a second rule, `isBundleSkippedTool` in `cmd/lgbgen/main.go`. It matches `ir`, every `ir.` descendant, `lg.compiler` and its descendants, and `lg.commands.*` [19]. The comment on that function gives the reason: bundling `lg.compiler` pulled the IR pipeline into the constant pool and moved boot from 4.1 ms to 23.4 ms, past an 8 ms budget (measured 2026-09-02) [19].
- The exclusion has to happen before the bundle is encoded, not only in the namespace order. `EncodeBundleOrdered` emits every constant in the pool, and each function constant carries its chunk, so an excluded namespace must not enter the pool before `writeBundle` [19].
- `data.lg` was the exception to that ordering until #838 (merged 2026-09-10, `83931029`). `lgbgen` had bootstrapped it into the shared pool before the bundle was written. `cmd/lgbstat` at `a9c183f9` attributed 111 of 937 chunks to `<embedded:ir.data:lgbgen-bootstrap>`. The bootstrap now runs in `compileToolsForLowering`, after `writeBundle` [19][22]. The commit reports that `core_compiled.lgb` went from 311,302 to 273,748 bytes, and that boot went from about 1.8 ms to about 1.6 ms [22].
- `ir.build` declares `(:require [ir.data])`, so loading build also loads data's source [12][17].

The IR README gives the likely cause of "nil is not a function" errors during `compile-form`: `data.lg` had not finished loading before the caller compiled. The fix is to add `ir.data` to a `:require` clause in the caller, or to load it with `(require '[ir.data])` at the top of the file [1]. `ir.build` declares `(:require [ir.data])` [17], so loading build also loads data's source.

## Testing

The IR regression tests are in `pkg/ir/` as `lisp_*_test.go` files, for example `lisp_cse_test.go`, `lisp_dce_trapping_test.go`, `lisp_dominance_test.go`, and `lisp_blockarg_test.go` [23]. Convention, not stated in the source: add a test for a new pass or op alongside these files.

## Citations

[1] **IR framework README** (at b82588292b)  
https://github.com/nooga/let-go/blob/b82588292b/pkg/rt/core/ir/README.md

[2] **ir/ source code** (let-go implementations) @ b82588292b  
https://github.com/nooga/let-go/tree/b82588292b/pkg/rt/core/ir

[3] **ir/lower_go.lg** — IR → Go AST lowering (for AOT compilation) @ b82588292b  
https://github.com/nooga/let-go/blob/b82588292b/pkg/rt/core/ir/lower_go.lg

[4] **Indexed-RPN IR** (this wiki)  
[indexed-rpn-ir.md](indexed-rpn-ir.md)

[5] **Bytecode Compiler** (this wiki)  
[bytecode-compiler.md](bytecode-compiler.md)

[6] **Stack VM** (this wiki)  
[stack-vm.md](stack-vm.md)

[7] **let-go** (this wiki)  
[../entities/let-go.md](../entities/let-go.md)

[8] **pkg/rt/core/ir/passes/pipeline.lg** lines 662–672 (`*target*` and the lowering registry) @ b82588292b  
https://github.com/nooga/let-go/blob/b82588292b/pkg/rt/core/ir/passes/pipeline.lg

[9] **scripts/generate.lg** (`gen-go`, `gen-lisp` calls) @ b82588292b  
https://github.com/nooga/let-go/blob/b82588292b/scripts/generate.lg

[10] **pkg/rt/core/ir/passes/pipeline.lg** `default-pass-list`, `run-pass-list`, `optimize-fn`, `uniform-pass-list` @ b82588292b  
https://github.com/nooga/let-go/blob/b82588292b/pkg/rt/core/ir/passes/pipeline.lg

[11] **pkg/rt/core/ir/passes/dce.lg** @ b82588292b  
https://github.com/nooga/let-go/blob/b82588292b/pkg/rt/core/ir/passes/dce.lg

[12] **pkg/rt/core/ir/build.lg** (`build-fn`) and **pkg/rt/core/ir/lower.lg** (`lower`) @ b82588292b  
https://github.com/nooga/let-go/blob/b82588292b/pkg/rt/core/ir/build.lg  
https://github.com/nooga/let-go/blob/b82588292b/pkg/rt/core/ir/lower.lg

[13] **pkg/rt/core/ir/passes/constfold.lg**, **cse.lg**, **licm.lg** headers @ b82588292b  
https://github.com/nooga/let-go/blob/b82588292b/pkg/rt/core/ir/passes/constfold.lg  
https://github.com/nooga/let-go/blob/b82588292b/pkg/rt/core/ir/passes/cse.lg  
https://github.com/nooga/let-go/blob/b82588292b/pkg/rt/core/ir/passes/licm.lg

[14] **pkg/rt/core/ir/passes/fusion.lg** (`fusion`, `*enable-fusion*`) @ b82588292b  
https://github.com/nooga/let-go/blob/b82588292b/pkg/rt/core/ir/passes/fusion.lg

[15] **pkg/rt/core/ir/passes/legalize.lg** header @ b82588292b  
https://github.com/nooga/let-go/blob/b82588292b/pkg/rt/core/ir/passes/legalize.lg

[16] **pkg/rt/core/ir/passes/inline.lg** (`*enable-inline*`, eligibility) @ b82588292b  
https://github.com/nooga/let-go/blob/b82588292b/pkg/rt/core/ir/passes/inline.lg

[17] **pkg/rt/core/ir/data.lg** (header shape, `new-fn`, accessors, intern block) and **pkg/rt/core/ir/data/generated.lg** @ b82588292b  
https://github.com/nooga/let-go/blob/b82588292b/pkg/rt/core/ir/data.lg  
https://github.com/nooga/let-go/blob/b82588292b/pkg/rt/core/ir/data/generated.lg

[18] **pkg/rt/core_embed_fs.go** (`//go:embed all:core`) @ b82588292b  
https://github.com/nooga/let-go/blob/b82588292b/pkg/rt/core_embed_fs.go

[19] **cmd/lgbgen/main.go** (`isBundleSkippedTool`, `hasLgbgenSkipDirective`, `compileToolsForLowering`) @ b82588292b  
https://github.com/nooga/let-go/blob/b82588292b/cmd/lgbgen/main.go

[20] **Makefile** `generate` target and comment @ b82588292b  
https://github.com/nooga/let-go/blob/b82588292b/Makefile

[21] **pkg/ir/ir_bridge.lg** (`:lisp-name` entries) and **pkg/rt/ir_bridge_generated.go** @ b82588292b  
https://github.com/nooga/let-go/blob/b82588292b/pkg/ir/ir_bridge.lg  
https://github.com/nooga/let-go/blob/b82588292b/pkg/rt/ir_bridge_generated.go

[22] **#838** commit `83931029` (`build(lgbgen): bootstrap ir.data after the bundle is written`); the figures for `cmd/lgbstat` at `a9c183f9` are in its commit message  
https://github.com/nooga/let-go/commit/83931029

[23] **pkg/ir/lisp_*_test.go** @ b82588292b  
https://github.com/nooga/let-go/tree/b82588292b/pkg/ir

---

See also: [Indexed-RPN IR](indexed-rpn-ir.md), [Bytecode Compiler](bytecode-compiler.md), [Stack VM](stack-vm.md), [let-go](../entities/let-go.md)
