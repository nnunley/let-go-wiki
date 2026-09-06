---
type: Concept
category: concept
title: "Structurize"
description: "The pass that recovers a target-independent control tree from the IR's block-parameter CFG (if, loop, break, continue, seq, with goto as the escape hatch), which backend consumes it and which does not, the :try gap, and the keyword-cond to switch absorption."
tags: [compiler, go, bytecode]
resource: "https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/structurize.lg"
sources:
  - "repo: nooga/let-go pkg/rt/core/ir/structurize.lg, pkg/rt/core/ir/lower_go.lg, pkg/rt/core/ir/lower.lg @ 0911118, 2026-09-05"
  - "issue: nooga/let-go#574 (EPIC-017, the structural level as root cause), #674 (param-carrying keyword-cond chains); pr: #675 (keyword-cond to switch, merged 2026-09-06 as b7e04d6), #579 (the bytecode backend never adopted it), 2026-09-05"
created: "2026-09-05"
updated: "2026-09-06"
status: stable
---

# Structurize

`build.lg` only ever emits `if` and `loop`/`recur` shapes, so the CFG the [IR](indexed-rpn-ir.md) carries is reducible. `ir.structurize` (Norman's pass, `pkg/rt/core/ir/structurize.lg`) walks that CFG and returns a control tree that no backend has to rediscover: a Go backend can emit `if`/`for`/`break`/`continue`, a wasm backend could emit its structured blocks, and a stack backend could know consumer order. Which backends actually use it is the interesting part.

## The tree

| Node | Meaning |
|---|---|
| `[:return bid]` | block `bid`'s terminator is `:return` |
| `[:tail bid]` | terminator is `:recur-fn`, the function-level recur back-edge |
| `[:seq bid edge next]` | an unconditional `:branch`, then `next` |
| `[:if bid tt et then else cont]` | `:branch-if`; `tt`/`et` are the branch targets carrying block-args, `cont` the structured join region or `nil` |
| `[:loop bid body cont]` | `bid` is a loop header; `body` uses `:continue` and `:break`; `cont` follows the loop |
| `[:continue bid edge]` | back-edge to the enclosing loop header |
| `[:break bid edge]` | exits the enclosing loop |
| `[:fallthrough bid]` | the region rejoins an enclosing continuation |
| `[:goto bid]` | fallback for an unstructurable transfer |

The `bid` leaves let the backend emit each block's instructions and edge copies. Join regions come from post-dominators: the file carries a copy of `dominance.lg`'s Cooper, Harvey, and Kennedy algorithm parameterised by successor and predecessor functions so it can run on the reversed graph. `:goto` is the escape hatch that keeps correctness independent of coverage: a `:fallbacks` counter ratchets toward zero on the real corpus rather than the pass having to be complete on day one.

## Who consumes it

`lower_go.lg` is the consumer (`[ir.structurize :as st]`), and `structurize.lg` itself requires `ir.dominance`; the Go backend walks the tree to emit mutable locals with labels and gotos where it must and structured control flow where it can. `lower.lg`, the [bytecode lowering](bytecode-lowering.md), does not: it still walks raw blocks by stack position. #579 named that as the reason for the residual `DUP_NTH` shuffle in IR-lowered bytecode, because without the tree the stack backend cannot know consumer order or that a value is dead after a use in a sibling arm, so it copies defensively. #574 (EPIC-017) records the same fact as the single root cause behind the cross-block splice rejection and `:try` being unlowerable on the bytecode path, and lists "bytecode adopts structurize" as an unscheduled story.

## Two known gaps

- **`:try` is not a structural node.** try/catch leaks to the op level, and `lower_go` special-cases it outside the tree walk. Capturing the guarded region once at the structural level is the other unscheduled EPIC-017 story.
- **Keyword-cond chains.** `case` and `cond` over keywords lowered to nested `if`/`else` in Go until #675 (merged 2026-09-06, b7e04d6), which teaches structurize to absorb a chain into a `:switch` node and emit a native Go `switch` through `vm.KeywordName`, gated to the maximally conservative shape: every absorbed test block has zero block params and only pure `:const` and `:eq` instructions, with a side-effecting test block falling back. That gate excludes the canonical `(cond (= x :a) 1 (= x :b) 2 ...)`, whose discriminant `build.lg` threads through block params; #674 tracks the boundary analysis needed to admit it, with the two Go-compile failure signatures (`declared and not used`, `undefined: step_*`) as the adversarial test set, after several attempts oscillated between under- and over-rejection.

## Citations

**Resource:** [pkg/rt/core/ir/structurize.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/structurize.lg): the pass and the tree grammar in its header  
**Related:**
- [pkg/rt/core/ir/lower_go.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/lower_go.lg): the only consumer at `0911118`
- [pkg/rt/core/ir/lower.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/lower.lg): the backend that has not adopted it
- Issues and PRs: [#574](https://github.com/nooga/let-go/issues/574), [#674](https://github.com/nooga/let-go/issues/674), [#675](https://github.com/nooga/let-go/pull/675), [#579](https://github.com/nooga/let-go/pull/579)

See also: [IR Passes](ir-passes.md), [Go Backend](go-backend.md), [Block Interface and Liveness](block-interface-and-liveness.md), [IR representation roadmap](../ideas/ir-representation-roadmap.md), [let-go](../entities/let-go.md)
