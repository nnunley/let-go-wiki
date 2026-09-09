---
type: Idea
category: idea
title: "IR Representation Roadmap (EPIC-017 and EPIC-018)"
description: "The two public epics for the IR's representation: normalize the op catalog and adopt the structural level (EPIC-017), and build shared liveness on the block interface, give the stack VM locals, and erase redundant block-args (EPIC-018), with the ranked physical-layout findings and the index-RPN VM gate that sequences them."
tags: [compiler, idea, vm, bytecode]
resource: "https://github.com/nooga/let-go/issues/574"
sources:
  - "issue: nooga/let-go#574 (EPIC-017), #575 (EPIC-018), #620 (constant-space tail calls), #519 (more of let-go in let-go), #665 (zero-alloc inst iteration), #664 (merge-side copy cascades); pr: #580 (fmpl comparison), #712 (accessor seam), 2026-09-05"
created: "2026-09-05"
updated: "2026-09-05"
status: active
---

# IR Representation Roadmap (EPIC-017 and EPIC-018)

Norman made two internal epics visible upstream as #574 and #575 (companions; the dates in them refer to an internal iteration log). Together they say where the IR's representation is going and why. The finding that drives both: an execution spike (ITER-0057) showed that the IR's representation mechanics, not the execution model, dominate interpreted performance. Removing string dispatch, per-instruction guards, and dead-parameter edge writes moved the numeric slice from 0.88× to about 1.04× geomean (1.23× to 1.28× at scale).

## EPIC-017: normalization and the structural level

**Root cause, as the epic states it.** The design already has the right levels: [structurize](../concepts/structurize.md) captures a target-independent control tree and `lower_go` consumes it. Two holes break the layering: `:try` is not a structural node, so try/catch leaks to the op level; and the bytecode backend never adopted the structural level, going straight from the low CFG to stack bytecode. That second hole is the single root cause behind the cross-block splice rejection and `:try` being unlowerable on the bytecode path. Supporting evidence from 2026-07-18: the junk-below accounting proved fragile (per-predecessor disagreement corrupting `OP_RECUR` drop counts), and IR-lowered bytecode measured about twice the instruction count of the direct compiler on branch-heavy code, roughly 67% of the excess being branch-arg `DUP_NTH` shuffle.

**Ranked physical-layout findings**, from an audit against Carbon's SemIR and indexed RPN:

1. Packed instruction records: instructions are boxed persistent vectors with nested refs vectors, against roughly 16-byte tagged unions with inline operand words and a side table for spills. The top measured cost; #558's type side table is the interim step.
2. Canonicalization and interning (STORY-0058): `:gt` to `:lt` normalization is cheap now; `:inc`/`:dec` respecialization is gated on the structural level.
3. Mutation by tombstone replaced with freeze-after-construction (STORY-0059, done as a pre-execution cleanup pass).
4. Blocks as `(start, len)` spans via post-optimize dense renumbering.
5. Frame width (STORY-0060): hybrid framing, slot reuse for single-use values and stable indexed slots for multi-use and cross-block values. This gates the EPIC-018 tail.
6. Typed handles over raw index ints (low priority).

Unscheduled stories: `structurize-:try` (capture the guarded region once) and `bytecode-adopts-structurize` (retire the junk-below machinery). The [op catalog](../concepts/op-catalog.md) work is the canonicalization half of this epic, finished rather than deleted per #528.

## EPIC-018: block interface as shared liveness metadata

The cross-block and locals half; [block interface and liveness](../concepts/block-interface-and-liveness.md) covers the mechanism and the story table. Done: shared per-block liveness, relocation of ad-hoc reachability helpers, the single-value resolver, and the block-arg classification census. Pending, backend-coupled: `OP_LOAD_LOCAL`/`OP_STORE_LOCAL` in the stack VM, lowering cross-block refs through locals (retiring `check-cross-block!`), and retiring the fold-outline workaround so the general inliner works on the bytecode path.

## The gate

Both epics feed the EPIC-016 re-check: whether an index-RPN VM that executes the IR directly should become the mainline. The pending EPIC-018 tail holds until that verdict, because if it flips to go the stack-VM half is superseded; the index-to-stack-depth conversion that generates the not-on-stack failures does not get fixed in that design, it ceases to exist. #580's comparison with fmpl (which executes indexed IR directly with `values[i]` as the result of instruction `i`) is the public statement of that argument, along with the traps either design must carry: closures snapshot captured values not slot references, `OP_RECUR` writes parameter slots explicitly, catch handlers get their own slot scope. #528's proposal to delete the RPN spike is held (or pin-and-delete) until the verdict.

## Adjacent open issues

- #620: constant-space tail calls on the explicit-frame VM (closures, multi-arity, `apply`).
- #665: zero-allocation instruction iteration for `.lg` pipeline walks, recovering the alloc cost the contribution model accepted.
- #664: merge-side copy cascades in lowered output that escape DCE and CSE.
- #519: capability unlocks for writing more of let-go in let-go and lowering it.

## Citations

- [nooga/let-go#574](https://github.com/nooga/let-go/issues/574) EPIC-017, [#575](https://github.com/nooga/let-go/issues/575) EPIC-018
- [#580](https://github.com/nooga/let-go/pull/580): the fmpl comparison and the "why the 535 exist" analysis
- [#712](https://github.com/nooga/let-go/pull/712): the accessor seam the representation change depends on
- [#620](https://github.com/nooga/let-go/issues/620), [#665](https://github.com/nooga/let-go/issues/665), [#664](https://github.com/nooga/let-go/issues/664), [#519](https://github.com/nooga/let-go/issues/519)

See also: [Indexed-RPN IR](../concepts/indexed-rpn-ir.md), [Bytecode Lowering](../concepts/bytecode-lowering.md), [Stack VM](../concepts/stack-vm.md), [Master Plan Roadmap](master-plan-roadmap.md), [let-go](../entities/let-go.md)
