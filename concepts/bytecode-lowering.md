---
type: Concept
category: concept
title: "Bytecode Lowering"
description: "How ir.lower turns an optimized IR function into stack bytecode: source-order emission with stable slots and DUP_NTH for reuse, cheap-load re-emission, junk-below accounting and the agreement rule, RPO emission order, tail-call fusion, the def+name* seam, and the shape ratchet that pins what it emits."
tags: [compiler, bytecode, vm]
resource: "https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/lower.lg"
sources:
  - "repo: nooga/let-go pkg/rt/core/ir/lower.lg, pkg/rt/core/core.lg (defn), test/ir_lower_stack_discipline_test.lg @ 0911118, 2026-09-05"
  - "pr: nooga/let-go#579 (var-load re-emission + shape ratchet), #648 (block-junk agreement, RPO, deferrable-branch guards), #649 (tail-call fusion), #647 (def+name* seam), #580 (census), #779 (fn-template consts are not rematerialised, merged 2026-09-06 as a32767d), 2026-09-05"
created: "2026-09-05"
updated: "2026-09-06"
status: stable
---

# Bytecode Lowering

`ir.lower` (`pkg/rt/core/ir/lower.lg`) is the backend the [IR path](compile-paths.md) drives at load time: it takes an optimized IR function and emits a `vm.CodeChunk` for the [stack VM](stack-vm.md). It began as a function-for-function Lisp port of the Go `pkg/ir/lower.go`, with byte-identical output as the convergence criterion of the retire-`pkg/ir` work, and the 2026 changes to it are about making a stack machine a good target for an IR that was designed with indices, not depths.

## Strategy

The header of the file states it:

- Body-emit every node in source order and record a stable stack slot at each definition site.
- A multi-use value lands at its slot and later uses `DUP_NTH` from there; a single-use value consumed at the top of the stack is used in place.
- Cheap loads (`Const`, `LoadArg`, `LoadVar`, `LoadClosed`, the `cheap?` column of the [op catalog](op-catalog.md)) defer to use-site re-emission when single-use and not the consumer's first reference, which matches the direct compiler's natural layout. A `:const` whose aux is a `:fn-template` or `:multi-fn-template` is the exception since #779 (merged 2026-09-06, a32767d): a function literal is an allocation with observable identity, so it is materialised once per lowering site and every reuse goes through `DUP_NTH`; re-running the template made `(let [f (fn [x] x) g f] (identical? f g))` false under `*ir-compile*` and true under the direct compiler.
- Branch terminators recognise two fast paths: arguments already at the target positions, and arguments already at the top of the stack.

The lowerer's state is one atom holding a map; every mutation is a `swap!`.

## Junk below and the agreement rule

A `BRANCH_F` leaves the predecessor's stack pointer one below the target's parameters, while a clean `BRANCH` or `OP_RECUR` leaves nothing. So each block carries a "junk-below" count, the values still on the runtime stack beneath its parameters at entry, populated by predecessor terminators and used to compute the true runtime stack pointer for `maxStack`. #648 made every fall-through predecessor agree: the junk is baked into the target's `OP_RECUR` drop counts, so a path entering with a different count over- or under-drops the stack, observed as `slice bounds out of range` underflows. The old rule took the maximum, which was harmless only while mismatching shapes could not lower at all; the deferral and RPO fixes in the same PR let them lower, so a disagreement now aborts the function's lowering and the `defn` hybrid falls back to the direct compiler. `RECUR`-edge predecessors report zero junk, and that zero is recorded so a disagreement with a non-zero predecessor is caught rather than silently accepted. The same PR moved block emission to reverse post-order (a true-target that is next in emission order falls through, otherwise it jumps) and rebaselined the coverage ratchet with 223 newly lowering forms and 79 more in the block-arg bucket, a deliberate trade of coverage for soundness.

## Cross-block references

`check-cross-block!` rejects any cross-block direct reference unless the definition is a cheap-load op other than `:load-var` (a mutable root must be materialised once; the function's own docstring still lists `:load-var` among the exempt ops, its body does not), or the use is a branch-target argument. This is the single rule behind most of what the bytecode path cannot lower; [block interface and liveness](block-interface-and-liveness.md) covers why and what would retire it. #579 removed one avoidable case: `lower.lg` had excluded every `:load-var` from cheap-load re-emission, so a var used twice was materialised once and copied per extra use. Only `set!`-target vars need that, because two loads could otherwise straddle the `set!` and read different roots; ordinary var loads are now re-emitted per use as the direct compiler does. That retired the whole `:validate/cross-block-ref` bucket (8) and took ir-stress native failures from 20 to 11, with runtime unchanged.

## Tail-call fusion

#649 emits `TAIL_CALL` for a single-use `:call` in return position, so the frame is reused. Its test covers bytecode/IR parity, an opcode falsifier, and try-frame isolation, and its ratchet numbers were neutral to slightly better (compiler init and IR compile within 2.5%).

## The def+name* seam

Grammar-style rule definitions of the shape `(def NAME (name* ... (fn ...) ...))` did not reach the IR path at all, because `name*` is just a call to the direct compiler. #647 routes them through `compile-def-fn-value`, and proves the seam ran with a strict-mode test: under `*ir-compile-strict*` a multi-arity `name*`-wrapped function throws naming `multi-arity`, whereas silence would mean the seam never fired. It also unwraps return-hinted arity vectors before testing for single arity, aligned with #661.

## The shape ratchet

`test/ir_lower_stack_discipline_test.lg` pins what the backend emits, not only what it computes: `fib` at most 23 instructions and 4 `DUP_NTH`, a `loop`/`recur` sum at most 18 and 8, with the direct compiler's 18 and 16 (and no shuffle) as the targets, and non-`set!` var loads re-emitted per use. Upper bounds, so an improvement passes and then tightens the numbers in the same commit, the same discipline as the other two [ratchets](perf-ratchet.md). The residual shuffle is emission order: a call argument is computed before the callee is loaded, so it must be copied above it, and that traces to `lower.lg` never having received the [structural level](structurize.md).

## Citations

**Resource:** [pkg/rt/core/ir/lower.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/lower.lg): strategy header, `record-block-junk!`, `check-cross-block!`, RPO emission

**Related:**
- [test/ir_lower_stack_discipline_test.lg](https://github.com/nooga/let-go/blob/main/test/ir_lower_stack_discipline_test.lg): the shape ratchet
- [pkg/rt/core/core.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/core.lg): the `defn` hybrid fallback that catches an aborted lowering
- PRs: [#579](https://github.com/nooga/let-go/pull/579), [#648](https://github.com/nooga/let-go/pull/648), [#649](https://github.com/nooga/let-go/pull/649), [#647](https://github.com/nooga/let-go/pull/647), [#580](https://github.com/nooga/let-go/pull/580)

See also: [Compile Paths](compile-paths.md), [IR Pipeline](ir-pipeline.md), [Stack VM](stack-vm.md), [let-go](../entities/let-go.md)
