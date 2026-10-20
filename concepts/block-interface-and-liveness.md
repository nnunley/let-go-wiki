---
type: Concept
category: concept
title: "Block Interface and Liveness"
description: "Block-args as the stack VM's substitute for locals, the shared per-block liveness analysis, the block-arg classifier and its census (rematerialize, slot, thread), the cross-block rejection in the bytecode lowering, and the measured cost that motivates erasing block-args."
tags: [compiler, vm, bytecode]
resource: "https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/passes/liveness.lg"
sources:
  - "repo: nooga/let-go pkg/rt/core/ir/passes/{liveness,blockarg,pipeline}.lg, pkg/rt/core/ir/lower.lg (check-cross-block!) @ a9c183f9 (liveness re-read after #675), 2026-09-09"
  - "issue: nooga/let-go#575 (EPIC-018, story ledger), #574 (EPIC-017); pr: #580 (why the not-on-stack bucket exists), #579 (DUP_NTH measurement), 2026-09-05"
  - "repo: nooga/let-go pkg/rt/core/ir/passes/{liveness,blockarg,pipeline}.lg, pkg/rt/core/ir/{data,lower,lower_go,structurize}.lg, pkg/ir/lisp_liveness_test.go, pkg/ir/lisp_blockarg_test.go, docs/perf/ir-stress-bytecode-baseline.edn @ b82588292b, 2026-10-20"
  - "issue: nooga/let-go#575, #574 (state and bodies checked 2026-10-20); pr: #579, #580, #675, #558, #712 (titles, merge dates and bodies checked 2026-10-20)"
created: "2026-09-05"
updated: "2026-10-20"
status: stable
---

# Block Interface and Liveness

A block in the [IR](indexed-rpn-ir.md) takes parameters, and every value that crosses a block boundary is threaded through a branch-target argument. That is how block-parameter SSA works, and it is also an accommodation: the [stack VM](stack-vm.md) has no writable frame slots, so a value can reach another block only on the operand stack in a known position. EPIC-018 (#575) sets out to make the block interface carry shared liveness metadata, give the VM real locals, and then erase the block-args that a single-source value makes redundant. The foundation stories (0068 to 0071) are in the source at b82588292b. The backend stories (0072 to 0074) are not, and are held behind a gate (see below).

## The convention

Liveness (`passes/liveness.lg`) is per-block backward dataflow over instruction ids. It reads block structure. Its only mutable state is the memo atom `liveness-memo`, keyed by a structural signature of the function. Its load-bearing convention is that a block's parameters are inputs, not definitions: a parameter used in its block is live-in to that block, which is what makes the predecessor's edge argument live. Only instruction results are block-local definitions. In the file's own notation:

```
reads[B]    = inst-refs(B) ∪ (terminator-refs(B) − edge-args(B))
results[B]  = inst-results(B)                          ; not params
live-in[B]  = (reads[B] ∪ live-out[B]) − results[B]
live-out[B] = ⋃ over targets t of
                {v ∈ live-in[t] : v ∉ params(t)} ∪ {arg[i] : param[i] ∈ live-in[t]}
```

These equations match `compute-liveness` and `succ-contribution` in the file. Results are memoised on a content-based structural signature (`fn-signature`), never on object identity. `compute-liveness` has no caller outside the tests in `pkg/ir/lisp_liveness_test.go`.

`reachable-nids` is the other exported analysis in the file. It computes the set of InstIds whose value emitted code reads, and `lower_go` uses it for its `live?` check (`pkg/rt/core/ir/lower_go.lg`, the `live?` definition near line 770). When the set is absent, `live?` falls back to the IR uses table. Its roots are the refs of the value-reading terminators (`:return`, `:branch-if`, `:tail-call`, `:recur-fn`) and the refs of every `:call` and `:try` instruction. It is closed under instruction refs and under block-arg edges, so a reachable block-param's incoming edge-args are reachable. Since #675, seeding skips the terminators and calls that [structurize](structurize.md) folded into a `:switch` (`:absorbed-insts`).

`lower_go` has no `live-nids` of its own. #575 (STORY-0069) records that its `live-nids` was the one genuine duplicate of this analysis, and it was relocated onto `reachable-nids`. The comment in `pkg/ir/lisp_liveness_test.go` (around line 287) says that exactness against the old `live-nids` is locked by the byte-identical regenerated `core_go_lowered/` tree. `TestReachableNidsConsistent` (lines 290 to 305) checks `reachable-nids` against `compute-liveness`'s cross-block-live values. `reachable-nids` reaches `lower_go` through a setter. `passes/pipeline.lg` line 44 runs `(lower-go/set-reachable-nids-fn! (resolve 'ir.passes.liveness/reachable-nids))` when the pipeline namespace loads, and `lower_go` stores the function in an atom. `lower_go` does not `:require` the liveness namespace. The comment above that line says the reference is deferred to runtime. The `resolve` call runs at load time.

## Classifying block-args

`passes/blockarg.lg` decides, without changing anything, how each block-arg's value would cross its boundary once a slot lowering exists:

- `:rematerialize`: a single-value arg whose source is a ref-free cheap load (`:const`, `:load-arg`, `:load-closed`), recomputable at the use site. `:load-var` is deliberately excluded, because a mutable var root must be materialised once, matching the cross-block gate in `lower.lg`.
- `:slot`: a single-value arg from any other source, which wants durable storage.
- `:thread`: a genuine merge with distinct reaching values, where the block-arg is the channel.

It sees through single-value block-args with `ir/resolve-single-source` (`pkg/rt/core/ir/data.lg`, around line 298). That function traces an arg through its block-arg chain to an underlying InstId when every incoming edge denotes the same value. "The same value" means the same InstId or a ref-free equivalent, such as `:load-var` of one var. It applies transitively, and a genuine merge returns the arg itself (STORY-0070). `classify-census` counts the three buckets over a function. The `:rematerialize` and `:slot` buckets are the single-value copies, and the `:thread` bucket is the real merges (STORY-0071). The classifier and the census are called only from `pkg/ir/lisp_blockarg_test.go`.

## What the bytecode lowering does today

`lower.lg`'s `check-cross-block!` (line 220) walks every use. It throws unless the use is a branch-target argument or `ir/reemittable-at-use?` holds for the definition. That predicate (`data.lg`, line 187) is true for a cheap-load op other than `:load-var`, and it is false for function-literal constants. The thrown message reads "only branch-target args may cross blocks". The section comments in `lower.lg` (around lines 312 to 325 and 372 to 385) describe how `:load-var` is handled elsewhere. A `:load-var` is materialized once only when the same function `set!`s that var, or when the load is live across an effectful op (`:call`, `:tail-call`, `:set-var`, `:def`). Otherwise it is re-emitted at each use.

The not-on-stack bucket follows from this. #580 (merged 2026-07-24) reports 535 of 713 bytecode-path failures in `:lower/not-on-stack/*`. The IR holds every operand as an index, but the lowering discards that index for a stack depth (`value-stack-pos`, `DUP_NTH`). A value defined in another block has no computable depth.

The AOT inline splice is not used on the bytecode default path. `passes/pipeline.lg` (around lines 827 to 841) leaves the splicing inliner's registry unbound there, because splicing creates cross-block direct refs that the stack lowering rejects. Instead, `fold-outline!` (`pipeline.lg`, line 179) rewrites each fold-over-rest combinator call to a call of an unrolled fixed-arity sibling in the same namespace. It runs only when `ir.passes.inline/*enable-inline*` is true.

The cost figures come from two sources. #575 records that the 2026-07-18 lowering investigation put branch-arg `DUP_NTH` shuffle at about 67% of the roughly 2x instruction bloat in IR-lowered hot functions. #579 measured two fixtures before its change. `fib 21` took 18 instructions through the direct compiler and 24 through the IR path, six of them `DUP_NTH`. A `loop`/`recur` sum took 16 and 18. #579 then re-emitted ordinary var loads, which brought `fib` to 23 instructions and four `DUP_NTH`, with runtime unchanged (1.14x). #580 restates #579's measurement that a `loop`/`recur` sum spends 8 of 18 instructions on `DUP_NTH` shuffle. `test/ir_lower_stack_discipline_test.lg` (`ir-lowering-shuffle-ratchet`), measured 2026-07-19, sets the ceilings at fib 23 instructions and 4 `DUP_NTH`, and sumloop 18 instructions and 8 `DUP_NTH`, with the plain compiler's counts (18 and 16 instructions, 0 `DUP_NTH`) as targets. These numbers are the measurements in those PRs and the test file. They were not re-run at b82588292b. `docs/perf/ir-stress-bytecode-baseline.edn` (captured 2026-08-04) holds the 713 of 2432 bucket census.

The junk-below bookkeeping that locals would remove is also the source of a class of latent miscompiles. `lower.lg` now detects a mismatch between predecessors' junk-below values and falls back instead of accepting it. `record-block-junk!` (lines 135 to 156) throws at line 154 when a block's recorded junk disagrees with a new report, and RECUR-edge predecessors report junk 0 (line 625). The fallback costs IR coverage (see [bytecode lowering](bytecode-lowering.md)).

## The plan and its gate

| Story | State at b82588292b | What |
|---|---|---|
| 0068 | done | shared per-block liveness (`passes/liveness.lg`) |
| 0069 | done | relocate ad-hoc reachability helpers onto it (`lower_go` uses `reachable-nids`) |
| 0070 | done | single-value resolver (`ir/resolve-single-source`) |
| 0071 | done | block-arg classification and census (`passes/blockarg.lg`) |
| 0072 | pending | `OP_LOAD_LOCAL` / `OP_STORE_LOCAL` in the stack VM (no such opcodes in `pkg/vm` at b82588292b) |
| 0073 | pending | `lower.lg` consumes cross-block refs via locals; retires `check-cross-block!` and the junk-below class (`check-cross-block!` is still present) |
| 0074 | pending | retire the fold-outline workaround; the general inliner unblocks on the bytecode path (`fold-outline!` is still present) |

The pending tail is held until STORY-0060 and the EPIC-016 re-check verdict on an index-RPN mainline VM (#575). If that verdict is go, the stack-VM half is superseded. A VM that executes the indexed IR directly never performs the index-to-depth conversion. #580 makes this point with fmpl's `values[i]` frame. #575 also says the RPN-spike deletion proposed in #528 interacts with this gate. #712 routed fn-shape access through accessors, and #558 moved inferred types into a positional side table. Both are merged. #575 says #558's accessor-stable side table keeps this work rebase-safe over inst-layout changes. As of 2026-10-20, #574 and #575 are open.

## Citations

**Resource:** [pkg/rt/core/ir/passes/liveness.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/passes/liveness.lg): the analysis and its equations

**Related:**
- [pkg/rt/core/ir/passes/blockarg.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/passes/blockarg.lg): `classify-block-arg`, `classify-census`
- [pkg/rt/core/ir/lower.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/lower.lg): `check-cross-block!`
- [pkg/rt/core/ir/data.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/data.lg): `reemittable-at-use?`, `resolve-single-source`
- [pkg/rt/core/ir/passes/pipeline.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/passes/pipeline.lg): `set-reachable-nids-fn!` wiring, `fold-outline!`
- [pkg/rt/core/ir/lower_go.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/lower_go.lg): `live?`, `set-reachable-nids-fn!`
- Issues and PRs: [#575](https://github.com/nooga/let-go/issues/575), [#574](https://github.com/nooga/let-go/issues/574), [#580](https://github.com/nooga/let-go/pull/580), [#579](https://github.com/nooga/let-go/pull/579), [#675](https://github.com/nooga/let-go/pull/675), [#558](https://github.com/nooga/let-go/pull/558), [#712](https://github.com/nooga/let-go/pull/712)

See also: [Structurize](structurize.md), [Compile Paths](compile-paths.md), [IR Passes](ir-passes.md), [IR representation roadmap](../ideas/ir-representation-roadmap.md), [let-go](../entities/let-go.md)
