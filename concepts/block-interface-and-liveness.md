---
type: Concept
category: concept
title: "Block Interface and Liveness"
description: "Block-args as the stack VM's substitute for locals, the shared per-block liveness analysis, the block-arg classifier and its census (rematerialize, slot, thread), the cross-block rejection in the bytecode lowering, and the measured cost that motivates erasing block-args."
tags: [compiler, vm, bytecode]
resource: "https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/passes/liveness.lg"
sources:
  - "repo: nooga/let-go pkg/rt/core/ir/passes/{liveness,blockarg}.lg, pkg/rt/core/ir/lower.lg (check-cross-block!) @ 0911118, 2026-09-05"
  - "issue: nooga/let-go#575 (EPIC-018, story ledger), #574 (EPIC-017); pr: #580 (why the not-on-stack bucket exists), #579 (DUP_NTH measurement), 2026-09-05"
created: "2026-09-05"
updated: "2026-09-05"
status: stable
---

# Block Interface and Liveness

A block in the [IR](indexed-rpn-ir.md) takes parameters, and every value that crosses a block boundary is threaded through a branch-target argument. That is how block-parameter SSA works, and it is also an accommodation: the [stack VM](stack-vm.md) has no writable frame slots, so the only way a value can reach another block is on the operand stack in a known position. EPIC-018 (#575) is Norman's programme to make the block interface carry shared liveness metadata, give the VM real locals, and then erase the block-args that a single-source value makes redundant. The foundation half is done; the backend half is pending behind a design gate.

## The convention

Liveness (`passes/liveness.lg`) is per-block backward dataflow over instruction ids, reading structure and mutating nothing. Its load-bearing convention is that a block's parameters are inputs, not definitions: a parameter used in its block is live-in to that block, which is what makes the predecessor's edge argument live. Only instruction results are block-local definitions. In the file's own notation:

```
reads[B]    = inst-refs(B) ∪ (terminator-refs(B) − edge-args(B))
results[B]  = inst-results(B)                          ; not params
live-in[B]  = (reads[B] ∪ live-out[B]) − results[B]
live-out[B] = ⋃ over targets t of
                {v ∈ live-in[t] : v ∉ params(t)} ∪ {arg[i] : param[i] ∈ live-in[t]}
```

Results are memoised on a content-based structural signature, never on object identity. `lower_go`'s own `live-nids` was the one genuine duplicate of this analysis and was relocated onto it (#575, STORY-0069).

## Classifying block-args

`passes/blockarg.lg` decides, without changing anything, how each block-arg's value would cross its boundary once a slot lowering exists:

- `:rematerialize`: a single-value arg whose source is a ref-free cheap load (`:const`, `:load-arg`, `:load-closed`), recomputable at the use site. `:load-var` is deliberately excluded, because a mutable var root must be materialised once, matching `lower.lg`'s cross-block gate.
- `:slot`: a single-value arg from any other source, which wants durable storage.
- `:thread`: a genuine merge with distinct reaching values, where the block-arg is the channel.

It sees through single-value block-args with `ir/resolve-single-source`, which traces an arg to its unique source when every in-edge agrees (STORY-0070, scoped to single value rather than single source). `classify-census` counts the three buckets over a function; the first two are the spurious copies, the third the real merges (STORY-0071).

## What the bytecode lowering does today

`lower.lg`'s `check-cross-block!` walks every use and rejects a cross-block direct reference unless the definition is a cheap-load op other than `:load-var` (re-emitted at the use site by `materialize!`) or the use is a branch-target argument. That rejection is why the not-on-stack bucket in the #580 census exists (535 of 713 bytecode-path failures on 2026-07-24): the IR already holds every operand as an index, but the lowering discards the index for a stack depth, and a value defined in another block has no computable depth. It is also why the AOT inline splice is unusable on the bytecode path, so fold-unroll ships an outline-to-sibling workaround instead of inlining.

The cost was measured on 2026-07-18: IR-lowered bytecode ran about twice the instruction count of the direct compiler on branch-heavy code, with roughly 67% of the excess being branch-arg `DUP_NTH` shuffle, and #579 put numbers on two fixtures (`fib` 24 versus 18 instructions with six `DUP_NTH`; a `loop`/`recur` sum spending 8 of 18 on shuffle). The junk-below bookkeeping that locals would remove is also the source of a class of latent miscompiles, now guarded by fallback at the cost of coverage (see [bytecode lowering](bytecode-lowering.md)).

## The plan and its gate

| Story | State | What |
|---|---|---|
| 0068 | done | shared per-block liveness |
| 0069 | done | relocate ad-hoc reachability helpers onto it |
| 0070 | done | single-value resolver |
| 0071 | done | block-arg classification and census |
| 0072 | pending | `OP_LOAD_LOCAL` / `OP_STORE_LOCAL` in the stack VM |
| 0073 | pending | `lower.lg` consumes cross-block refs via locals; retires `check-cross-block!` and the junk-below class |
| 0074 | pending | retire the fold-outline workaround; the general inliner unblocks on the bytecode path |

The pending tail is held until the EPIC-016 re-check verdict on an index-RPN mainline VM: if that flips to go, the stack-VM half is superseded, because a VM that executes the indexed IR directly never performs the index-to-depth conversion at all (the #580 body makes the same point from fmpl's `values[i]` frame). #558's accessor-stable side table is what keeps this work rebase-safe over instruction-layout changes, and #712 finished closing the accessor seam.

## Citations

**Resource:** [pkg/rt/core/ir/passes/liveness.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/passes/liveness.lg): the analysis and its equations  
**Related:**
- [pkg/rt/core/ir/passes/blockarg.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/passes/blockarg.lg): `classify-block-arg`, `classify-census`
- [pkg/rt/core/ir/lower.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/lower.lg): `check-cross-block!`
- Issues and PRs: [#575](https://github.com/nooga/let-go/issues/575), [#574](https://github.com/nooga/let-go/issues/574), [#580](https://github.com/nooga/let-go/pull/580), [#579](https://github.com/nooga/let-go/pull/579)

See also: [Structurize](structurize.md), [Compile Paths](compile-paths.md), [IR Passes](ir-passes.md), [IR representation roadmap](../ideas/ir-representation-roadmap.md), [let-go](../entities/let-go.md)
