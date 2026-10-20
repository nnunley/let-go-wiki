---
type: Concept
category: concept
title: "Structurize"
description: "The pass that recovers a target-independent control tree from the IR's block-parameter CFG (if, loop, break, continue, seq, with goto as the escape hatch), which backend consumes it and which does not, the :try gap, and the keyword-cond to switch absorption."
tags: [compiler, go, bytecode]
resource: "https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/structurize.lg"
sources:
  - "repo: nooga/let-go pkg/rt/core/ir/structurize.lg, pkg/rt/core/ir/lower_go.lg, pkg/rt/core/ir/lower.lg, pkg/rt/core/ir/passes/liveness.lg, pkg/rt/core/ir/dominance.lg, pkg/rt/core/ir/build.lg, Makefile @ b82588292b, 2026-10-20"
  - "repo: nooga/let-go pkg/rt/core/ir/structurize.lg, pkg/rt/core/ir/lower_go.lg, pkg/rt/core/ir/lower.lg, pkg/rt/core/ir/passes/liveness.lg @ a9c183f9 (structurize and lower_go re-read after the #675 re-land, b7e04d6), 2026-09-09"
  - "issue: nooga/let-go#574 (EPIC-017, the structural level as root cause; open), #674 (param-carrying keyword-cond chains; open); pr: #675 (keyword-cond to switch, merged 2026-09-06 as b7e04d6), #579 (re-emits ordinary var loads on the bytecode path, merged 2026-07-22; its body attributes the residual DUP_NTH shuffle to the bytecode backend not receiving structural lowering), 2026-09-05"
created: "2026-09-05"
updated: "2026-10-20"
status: stable
---

# Structurize

`ir.structurize` (`pkg/rt/core/ir/structurize.lg`) walks the block-parameter CFG of an [IR](indexed-rpn-ir.md) function and returns a control tree together with a fallback count and the set of blocks and instructions it folded into a switch. Its header says that `build.lg` emits only `if` and `loop`/`recur` shapes, so the CFG is reducible. The pass does not check reducibility. A terminator it does not recognise becomes a `:goto` node and increments the fallback count.

The tree is target-independent. `lower_go.lg` is the only backend in `pkg/rt/core/ir` that calls `st/structurize`. The header also anticipates "a future wasm backend"; no wasm consumer exists there at b82588292b. The [bytecode lowering](bytecode-lowering.md) does not consume the tree.

## The tree

| Node | Meaning |
|---|---|
| `[:return bid]` | block `bid`'s terminator is `:return` |
| `[:tail bid]` | terminator is `:recur-fn`, the function-level recur back-edge. A `:tail-call` terminator throws. |
| `[:seq bid edge next]` | an unconditional `:branch` along `edge`, then `next` |
| `[:if bid tt et then else cont]` | `:branch-if`; `tt`/`et` are the true and false branch targets (they carry block args); `cont` is the join region from the immediate post-dominator, or `nil` when there is no valid join |
| `[:switch bid disc arms last-et default cont]` | a keyword-dispatch chain folded into one n-way node; see [Keyword-dispatch folding](#keyword-dispatch-folding-switch) |
| `[:loop bid body cont]` | `bid` is a loop header (a block with at least one predecessor it dominates); `body` uses `:continue` and `:break`; `cont` is the region after the loop, or `nil` when the loop has no single exit (`:none` or `:multi`) |
| `[:continue bid edge]` | back-edge to the enclosing loop header; `edge` is `nil` when reached as a block rather than as an edge |
| `[:break bid edge]` | exits the enclosing loop; `edge` is `nil` in the same case |
| `[:fallthrough bid]` | `bid` is the enclosing stop block, so the region rejoins the enclosing continuation |
| `[:goto bid]` | emitted for any terminator other than `:return`, `:recur-fn`, `:branch`, `:branch-if`, or `:tail-call` (which throws); increments the fallback count |

The `bid` leaves let the backend emit each block's instructions and edge copies.

Loop headers come from the dominator tree (`header->latches`). Join regions come from post-dominators: `post-idoms` runs the dominator computation on the reversed CFG rooted at a virtual exit node. The file carries its own copy of the iterative dominator algorithm (`g-idoms`), parameterised by successor and predecessor functions. `dominance.lg` names that algorithm as Cooper, Harvey, and Kennedy's "A Simple, Fast Dominance Algorithm" and runs it on forward edges only.

`structurize` returns the number of unstructured regions as `:fallbacks`. The header describes that counter as the figure to drive toward zero; the source records no value for it.

## Who consumes it

`lower_go.lg` requires `[ir.structurize :as st]` and calls `(st/structurize f)` in `lower-body`. `structurize.lg` requires `ir.data` and `ir.dominance`.

- When `:fallbacks` is zero, `lower-tree` lowers the tree to Go `if`, `for`, `break`, `continue`, and `switch` statements.
- When `:fallbacks` is nonzero, or when `lower-tree` returns nil for any node, the whole function is emitted by the goto-and-label emitter, which lowers every block. The choice is per function, not per region.
- With `LG_STRICT_STRUCTURED` set (read into `*strict-structured?*`), a function that is not emitted from the tree throws instead of taking the goto path, and the caller falls back to bytecode.
- Absorbed blocks and instructions are kept only on the structured path (`prepare-lower-body-metadata!`).

`lower.lg`, the [bytecode lowering](bytecode-lowering.md), does not require `ir.structurize`. It walks raw blocks by stack position. Cheap-load ops (`:const`, `:load-arg`, `:load-var`, `:load-closed`) are re-emitted at each use. Since #579 that includes ordinary `:load-var` instructions; before it, every `:load-var` was materialized once, while `:const`, `:load-arg`, and `:load-closed` were already re-emitted (#579 diff, `lower.lg` around line 767 at `13ada3629`; the `check-cross-block!` docstring at `lower.lg` lines 221-226 lists the cheap-load set but does not mention #579). `DUP_NTH` copies multi-use values from their slot (`lower.lg` header, line 11). A `:load-var` is body-emitted once and copied per use when its var is set!-targeted or it is live across an effectful op (`lower.lg` lines 310-390; the effect rule is at lines 372-385). The Makefile comment on the `ir-stress-bytecode` census says the same: `lower.lg` "doesn't use" structurize's control tree.

#574 (open, EPIC-017) names the missing structural level as the root cause of the cross-block splice rejection and of `:try` being unlowerable on the bytecode path, and lists "bytecode-adopts-structurize" under candidate stories not yet scheduled. #579 (merged 2026-07-22) made the bytecode backend re-emit ordinary `:load-var` instructions per use instead of copying them. Its body attributes the residual `DUP_NTH` shuffle, which comes from emission order around call arguments, to the bytecode backend not receiving structural lowering. Without the control tree the stack backend cannot know consumer order or that a value is dead after a use in a sibling arm, so it copies defensively.

## Keyword-dispatch folding (`:switch`)

`structure-straight` calls `collect-kw-chain` on each `:branch-if`. A test block matches `sz-eq-kw` when it ends in `branch-if` on `(= X kw)` and exactly one operand is a constant keyword. The fold applies only when all of these hold:

- At least three arms test the same canonical discriminant with distinct keywords. The discriminant is found by following single-predecessor block-arg copies back to the root value (`sz-canonical-disc`).
- Each absorbed test block is owned by the previous test's false edge: it has exactly one predecessor, and that predecessor is the previous test.
- Each absorbed test block has zero block params, exactly one `:eq`, no instruction other than `:const` and `:eq`, and a `:branch-if` terminator (`test-block-pure-eq-only?`).
- No absorbed test block is a loop header, continue target, or break target.

If any check fails, the chain stays as nested `:if` nodes.

`lower_go` emits a `:switch` as a Go type switch on the discriminant. The `vm.Keyword` case holds an inner string `switch` on `string(kw)`, where the tag is the keyword's full name, namespace included (`(subs (str kw) 1)`), so `:foo/a` and `:bar/a` stay distinct. Every other value takes the default clause. The default block is the chain's last false target and is not absorbed.

The pass reports folded blocks as `:absorbed-blocks` and folded instructions as `:absorbed-insts`. Each absorbed test block contributes its `const` and `eq` instructions and its `branch-if` terminator; the `eq` is the terminator's single condition ref. The owning block contributes its `branch-if` terminator and that condition `eq`. `reachable-nids` in [liveness](block-interface-and-liveness.md) does not seed from absorbed terminators or absorbed call and `:try` instructions, so the folded `eq` and its constant operands are not reached through the root `branch-if`. `lower_go` filters absorbed instructions out of block emission (`block-inst-stmts`). `lower_go` also reads `:absorbed-arg-subst`, but `structurize` does not return that key. The `lower_go` comment calls it inert scaffolding for #674.

Keyword dispatch is recognised by the `(= X :kw)` branch shape. The recognition code does not match on `cond` or `case` forms; the comment at `structurize.lg` line 195 describes the source shape as `cond`. #675 (merged 2026-09-06 as b7e04d6) re-landed this switch lowering.

## Known gaps

- **`:try` is not a structural node.** A `:try` is an instruction. `try-assign-stmts` is registered with the op catalog (`ops/register-lower-impl! :try`) and is lowered per instruction inside block emission, outside the tree walk. `function-needs-error?` treats a `:try` as needing the error path. #574 lists "structurize-`:try`" (capture the guarded region once at the structural level) as an unscheduled story.
- **Keyword-cond chains with block params.** The zero-params gate rejects the canonical `(cond (= x :a) 1 (= x :b) 2 ...)` form, because `build.lg` threads the discriminant through block params. Those chains fall back to nested `:if`. #674 (open) tracks the boundary analysis needed to admit them. It names the two Go-compile failure signatures, `declared and not used` and `undefined: step_*`, as the adversarial test set, and records that earlier attempts over-rejected or under-rejected.

## Citations

**Resource:** [pkg/rt/core/ir/structurize.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/structurize.lg): the pass and the tree grammar in its header

**Related:**
- [pkg/rt/core/ir/lower_go.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/lower_go.lg): the only consumer at b82588292b (`lower-body`, `lower-tree`, `prepare-lower-body-metadata!`)
- [pkg/rt/core/ir/lower.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/lower.lg): the backend that does not consume the tree
- [pkg/rt/core/ir/dominance.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/dominance.lg): forward dominators; the source of the copied algorithm
- [pkg/rt/core/ir/passes/liveness.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/passes/liveness.lg): `reachable-nids`, which skips absorbed instructions
- [Makefile](https://github.com/nooga/let-go/blob/main/Makefile): the `ir-stress-bytecode` comment on the two backends' differing failures
- Tests: [test/structurize_test.lg](https://github.com/nooga/let-go/blob/main/test/structurize_test.lg), [test/keyword_cond_switch_test.lg](https://github.com/nooga/let-go/blob/main/test/keyword_cond_switch_test.lg), [test/keyword_cond_switch_ir.lg](https://github.com/nooga/let-go/blob/main/test/keyword_cond_switch_ir.lg), [pkg/ir/structured_emission_test.go](https://github.com/nooga/let-go/blob/main/pkg/ir/structured_emission_test.go)
- Issues and PRs: [#574](https://github.com/nooga/let-go/issues/574), [#674](https://github.com/nooga/let-go/issues/674), [#675](https://github.com/nooga/let-go/pull/675), [#579](https://github.com/nooga/let-go/pull/579)

See also: [IR Passes](ir-passes.md), [Go Backend](go-backend.md), [Block Interface and Liveness](block-interface-and-liveness.md), [IR representation roadmap](../ideas/ir-representation-roadmap.md), [let-go](../entities/let-go.md)
