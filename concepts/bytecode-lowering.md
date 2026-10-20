---
type: Concept
category: concept
title: "Bytecode Lowering"
description: "How ir.lower turns an optimized IR function into stack bytecode: source-order emission with stable slots and DUP_NTH for reuse, cheap-load re-emission, junk-below accounting and the agreement rule, RPO emission order, tail-call fusion, the def+name* seam, and the shape ratchet that pins what it emits."
tags: [compiler, bytecode, vm]
resource: "https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/lower.lg"
sources:
  - "repo: nooga/let-go pkg/rt/core/ir/lower.lg, pkg/rt/core/core.lg (defn), test/ir_lower_stack_discipline_test.lg @ 0911118, 2026-09-05"
  - "pr: nooga/let-go#579 (var-load re-emission + shape ratchet), #648 (block-junk agreement, RPO, deferrable-branch guards), commit b3f68d62d (tail-call fusion, extracted from #625), #647 (def+name* seam), #580 (*ir-compile-strict* + bytecode census), #779 (fn-template consts are not rematerialised, merged 2026-09-06 as a32767d), #975 (single-use fn literals, reemittable-at-use?, b18b1fde3, 2026-10-06), 2026-09-05"
  - "repo: nooga/let-go pkg/rt/core/ir/lower.lg, pkg/rt/core/ir/data.lg, pkg/rt/core/ir/ops.lg, pkg/rt/core/ir/passes/pipeline.lg, pkg/rt/core/ir/lower_go.lg, pkg/rt/core/core.lg (defn), pkg/ir/ir_ops.lg, test/ir_lower_stack_discipline_test.lg, test/ir_tailcall_fusion.lg, test/ir_def_namestar_seam_test.lg @ b82588292b, 2026-10-20"
created: "2026-09-05"
updated: "2026-10-20"
status: stable
---

# Bytecode Lowering

`ir.lower` (`pkg/rt/core/ir/lower.lg`) is the bytecode backend of the [IR path](compile-paths.md). `pkg/rt/core/ir/passes/pipeline.lg` calls `(lower/lower (optimize-fn spec-ir))` and the result is a `vm.CodeChunk` for the [stack VM](stack-vm.md). The file header describes the lowerer as a Lisp port of the Go `pkg/ir/lower.go`, structured function-for-function so a parity test can drive iteration to byte-identical output with Go `ir.Lower`. At b82588292b `pkg/ir/lower.go` is not in the tree; the non-test files in `pkg/ir` are `defop_spec.lg`, `ir_bridge.lg`, `ir_data.lg`, `ir_ops.lg`, `op_exports.go`, `op_generated.go` and `op_lookup.go`. The header cites `docs/superpowers/specs/2026-05-22-retire-pkg-ir.md`, which is not in the tree at this commit.

## Strategy

The header of the file states the strategy:

- Body-emit every node in source order and record a stable stack slot at each definition site. `emit-inst!` sets the slot for any op with stack-out 1.
- A multi-use value lands at its slot and later uses `DUP_NTH` from there (`materialize!`, the tracked-slot path). A single-use value that is already on top of the stack at its last use is consumed in place (`refs-at-top-last-use?`, `consume-refs-in-place!`).

Cheap loads are `Const`, `LoadArg`, `LoadVar` and `LoadClosed`, the rows with `cheap?` set in the op catalog (`pkg/ir/ir_ops.lg`). The body walk skips a cheap load unless it is a set!-target var, a var load that crosses an effect (see [Cross-block references](#cross-block-references)), or `should-body-emit-cheap?` returns true. That function decides as follows:

- A function literal (a `:const` whose aux is a `:fn-template` or `:multi-fn-template`) with more than one use is body-emitted once, and each reuse is a `DUP_NTH`. It is not re-run per use, because `template-value` would produce a distinct `*vm.Func` for each reference (source comment). The multi-use rule dates from #779 (merged 2026-09-06 as a32767d). A single-use function literal is also body-emitted, unless its block ends in `:branch-if`; that single-use rule comes from #975 (b18b1fde3, 2026-10-06), because a pinned value under the test would reach the two successors at different depths.
- Any other cheap load with more than one use is not body-emitted; `materialize!` re-emits it at each use.
- A single-use cheap load is body-emitted when its one user's first reference is that value, or when the value is used only as a branch argument. Otherwise it is re-emitted at its use.

Operand materialization (`materialize!`) has three paths: the value is already on top at its last use (nothing emitted); the value is tracked on the stack (`DUP_NTH` from its slot); or the value is untracked, in which case a cheap load is re-emitted and any other op throws `not on stack for materialize`.

Branch terminators have one fast path, in `materialize-branch-args!`: when the branch args already occupy the top `argc` slots in order, they are consumed in place. Otherwise every arg is materialized to the top in order, and the values left below are junk that the branch lowering drops. A `:branch` emits `OP_RECUR` when its drop count is positive, or when the current block has junk and the target was recorded with junk 0. Otherwise it emits `OP_JUMP` when the target is not next in emission order, and emits nothing when the target is next (`emit-jump!`). A `:branch-if` emits `BRANCH_F` to its false target and falls through to the true target when that target is next in emission order (`emit-jump!`).

For a `:branch-if`, the condition is emitted after the branch args (its emission is deferred past the body walk) when all of these hold: it is not a `:block-arg`, its only user is the terminator, and it is not itself one of the terminator's branch args (`deferrable-branch-if-cond?`). `BRANCH_F` then pops the condition from the top.

The lowerer's state is one atom holding a map; every mutation is a `swap!`.

## Junk below and the agreement rule

Each block carries a "junk-below" count: the values still on the runtime stack beneath its parameters at entry. A `:branch-if` records, for both of its targets, junk equal to the lowerer's stack pointer plus the current block's junk, minus one for the popped condition, minus the target's parameter count. A clean `:branch` records the current block's junk. A `RECUR` edge records zero, because `OP_RECUR` rebuilds the stack from scratch. `bump-max-stack!` adds the junk to the lowerer's stack pointer to raise the chunk's `max-stack`. A final guard in `lower` adds the largest block-parameter count to `max-stack`.

`record-block-junk!` requires every predecessor edge that reports junk for a block to report the same value. These edges are a clean `:branch` (the current block's junk), both targets of a `:branch-if`, and a RECUR edge (zero). The junk is baked into the target's `OP_RECUR` drop counts (`ignore = drop-count - argc + cur-junk`), so a path entering with a different count over- or under-drops the stack, observed as `slice bounds out of range` underflows. The docstring states that the older rule took the maximum, which was harmless only while mismatching shapes could not lower at all. #648 introduced the agreement rule together with the RPO and deferral changes. A disagreement now throws `ir/lower: junk-below mismatch for block ...`, which aborts the function's lowering; the `defn` macro in `pkg/rt/core/core.lg` catches the exception and falls back to the direct compiler unless `*ir-compile-strict*` is set.

Block emission follows reverse post-order from the entry block (`rpo-block-order`), so that every non-back edge points forward. Back-edge predecessors are exempt, and unreachable blocks are appended in id order. Successors are visited highest-id-first, so the order matches id order whenever id order was already valid. #648 rebaselined the coverage ratchet with 223 newly lowering forms and 79 more in the block-arg bucket (PR body), which trades coverage for soundness.

`check-branch-if-symmetric-args!` runs before lowering. It throws if a `:branch-if`'s true and false targets carry different branch args, because the lowerer places one arg shape under the condition.

## Cross-block references

`check-cross-block!` rejects a use in a different block unless either the use is a terminator's branch-target argument (`is-terminator-branch-arg-use?`), or the definition is `reemittable-at-use?` in `pkg/rt/core/ir/data.lg`. That predicate accepts a cheap-load op except `:load-var` (the root is mutable) and except a function literal (it has identity; that exclusion is from #975). The function's own docstring still lists `:load-var` among the exempt ops; its body does not. A rejected use throws `ir/lower: cross-block use of value %N via direct Refs ... only branch-target args may cross blocks`. [Block interface and liveness](block-interface-and-liveness.md) covers why this rule exists and what would retire it.

Before #579 (merged 2026-07-22, "re-emit ordinary var loads instead of copying them"), `lower.lg` excluded every `:load-var` from cheap-load re-emission, so a var used twice was materialized once and copied per extra use. The PR body reports that the `:validate/cross-block-ref` bucket (8) retired, that ir-stress native-lowering failures went from 20 to 11, and that runtime was unchanged. Var loads are now handled by two rules in `lower.lg`:

- **Set!-target vars** (`load-var-snapshot?`) are materialized once, so two loads cannot straddle a `set!` and read different roots. The set! target is recognized both as a `:load-var` and as the Var-valued `:const` that `build-set!` emits (`var-key-of-ref`). `lower_go.lg` has the same `load-var-snapshot?` rule.
- **Loads live across an effect** (`load-var-crosses-effect?`) are materialized once. The effectful ops are `:call`, `:tail-call`, `:set-var` and `:def`. A cross-block use always counts as crossing. A same-block use counts only when an effectful instruction lies strictly between the load and the use. A load that is only the callee of a call (`callee-only-use?`) is exempt.

Every other var load is re-emitted at each use, as the plain bytecode compiler does (`test/ir_lower_stack_discipline_test.lg`, `ir-lowering-var-loads-match-plain-compiler`). The test file's own comments give the failure cases for these rules: a load before a `set!` of the same var must read the pre-`set!` value, and a load before a call that `set!`s the var must read the pre-call root.

## Tail-call fusion

Commit b3f68d62d (extracted from #625 [3/4], stacked on the RPO and block-junk fixes in #648) lowers a `:return` of a single-use `:call` as `TAIL_CALL`, so the frame is reused, instead of `INVOKE` followed by `RETURN`. The fusion applies only when the call is the last live instruction of its block (every later instruction in the block is `:invalid`), so skipping it in the body walk reorders nothing. The fused call's function and arguments are materialized, then `TAIL_CALL argc` is emitted, followed by a `RETURN` that is dead but kept for parity with the plain compiler. The IR models `try` bodies as inner closures, so a fusable call is never inside a guarded region of the frame that performs it.

`test/ir_tailcall_fusion.lg` covers bytecode/IR parity for tail calls, a shape check that a let-bound tail call emits `TAIL_CALL` and no `INVOKE`, and try-frame isolation (the try body is an inner function whose tail call is `TAIL_CALL`).
## The def+name* seam

`def` is a special form, so a grammar-style rule definition of the shape `(def NAME (name* ... (fn ...) ...))` never reaches the `defn` macro's IR hook (`test/ir_def_namestar_seam_test.lg`). #647 adds a def-side seam in the Go compiler (`maybeIRCompileDefFnArg`, per that test's header). For a top-level def whose value is a `name*`-wrapped single-arity fn, the seam calls `compile-def-fn-value` in `pkg/rt/core/ir/passes/pipeline.lg` and substitutes the compiled fn value for the fn form. `compile-def-fn-value` throws on a multi-arity fn form (`compile-def-fn-value: multi-arity fn form unsupported`), and the seam then falls back to the plain bytecode compile of the original form.

The seam is parity-preserving, so a test that only checks the result cannot show that it ran. The strict-mode test does: under `*ir-compile-strict*`, defining a `name*`-wrapped multi-arity fn throws, and the message names both `ir-compile-strict` and `multi-arity`. Without the seam, the same def would compile silently. #647 also unwraps return-hinted arity vectors (`^long [args]`) before testing for a single arity, aligned with #661.

## The shape ratchet

`test/ir_lower_stack_discipline_test.lg` pins what the backend emits, not only what it computes. It asserts upper bounds: `fib` at most 23 instructions and 4 `DUP_NTH`, and a `loop`/`recur` sum at most 18 instructions and 8 `DUP_NTH`. The file's comment records the plain compiler's figures as the targets, 18 instructions and 0 `DUP_NTH` for `fib` and 16 and 0 for the sum, measured 2026-07-19. A separate test, `ir-lowering-var-loads-match-plain-compiler`, checks that the IR path emits the same number of `LOAD_VAR` instructions as the plain compiler for `fib`. The file's comment says an improvement passes the bounds with room to spare and the numbers are then tightened in the same commit, following the discipline of the `ir-stress-gate` and `bench-ratchet` gates. See also the [perf ratchet](perf-ratchet.md).

The residual shuffle is emission order, per the test's comment: a call argument is computed before the callee is loaded, so the argument is copied above the callee and its original stays below as junk, which the trailing `RECUR` drops. The comment says closing the gap means scheduling operand materialization in consumer order (callee first, then arguments left to right), and tracks it as EPIC-018 (issue #575). `lower.lg` does not require `ir.structurize`; the [structured control tree](structurize.md) is consumed by the Go-source emitter in `lower_go.lg`.

## Citations

**Resource:** [pkg/rt/core/ir/lower.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/lower.lg): strategy header, `record-block-junk!`, `check-cross-block!`, `should-body-emit-cheap?`, `load-var-crosses-effect?`, `rpo-block-order`

**Related:**
- [pkg/rt/core/ir/data.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/data.lg): `reemittable-at-use?`, `fn-literal-const?`
- [pkg/rt/core/ir/passes/pipeline.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/passes/pipeline.lg): the `lower/lower` call site and `compile-def-fn-value`
- [pkg/rt/core/ir/lower_go.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/lower_go.lg): the Go-source backend, which has the same `load-var-snapshot?` rule
- [pkg/ir/ir_ops.lg](https://github.com/nooga/let-go/blob/main/pkg/ir/ir_ops.lg): the op catalog with the `cheap?` column
- [test/ir_lower_stack_discipline_test.lg](https://github.com/nooga/let-go/blob/main/test/ir_lower_stack_discipline_test.lg): the shape ratchet and the var-load snapshot tests
- [test/ir_tailcall_fusion.lg](https://github.com/nooga/let-go/blob/main/test/ir_tailcall_fusion.lg): tail-call fusion parity and shape
- [test/ir_def_namestar_seam_test.lg](https://github.com/nooga/let-go/blob/main/test/ir_def_namestar_seam_test.lg): the def+name* seam and its strict-mode throw
- [pkg/rt/core/core.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/core.lg): the `defn` hybrid fallback that catches an aborted lowering
- PRs: [#579](https://github.com/nooga/let-go/pull/579), [#648](https://github.com/nooga/let-go/pull/648), [#625](https://github.com/nooga/let-go/pull/625) (tail-call fusion, via commit b3f68d62d), [#647](https://github.com/nooga/let-go/pull/647), [#580](https://github.com/nooga/let-go/pull/580), [#661](https://github.com/nooga/let-go/pull/661), [#779](https://github.com/nooga/let-go/pull/779), [#975](https://github.com/nooga/let-go/pull/975)

See also: [Compile Paths](compile-paths.md), [IR Pipeline](ir-pipeline.md), [Stack VM](stack-vm.md), [let-go](../entities/let-go.md)
