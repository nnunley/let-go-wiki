---
type: Concept
category: concept
title: "Higher-Order & Loop Optimizations"
description: "Lambda lifting and higher-order specialization to eliminate dynamic dispatch and closure allocation in combinator-based code."
tags: [compiler, bytecode, vm]
resource: "https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/passes/pipeline.lg"
sources: ["design: docs/superpowers/specs/2026-06-28-lambda-lift-and-higher-order-specialization-design.md (local, 2026-07-02)", "design: docs/superpowers/specs/2026-06-28-multiblock-inliner-and-loop-unroll-design.md (local, 2026-07-02)"]
created: "2026-07-02"
updated: "2026-07-02"
status: speculative
---

## What they are

Lambda lifting and higher-order specialization are two complementary IR optimization passes designed to eliminate the overhead of dynamic dispatch and closure allocation in higher-order combinator code. Together, they transform code that passes functions as values (common in parser combinators and DSLs) into efficient direct-call recursive descent.

**Lambda lifting** hoists inner function literals (`:make-closure` closures over IR.Function templates) to top-level IR.Functions, making them nameable and eligible for direct-call registry entry. Lifted functions remain semantically identical but become independently callable.

**Higher-order specialization** (via inlining and partial evaluation) then inlines small combinator functions when their function-typed arguments are statically known, unrolling variadic loops over known argument sequences and replacing dynamic trampoline dispatch with straight-line recursive-descent calls.

## When they matter

Combinator-based code—particularly parser combinators and DSLs that build parse trees from small, reusable building blocks—suffers from two structural overheads:

1. **Dynamic dispatch** — Rules passed as opaque function values via `call` trampolines (evaluating a rule re-allocates the entire combinator tree per invocation)
2. **Per-node closure allocation** — Every combinator invocation allocates a fresh closure-wrapped function value

The yamlstar YAML parser (212 grammar rules implemented as closures) is a proving corpus: interpreted at ~36 ms, but naive native lowering still ~55 ms (slower than interpreted!) because lowering the rule bodies to native Go left the hot path untouched—the dispatch-bound combinator invocation cost dominates.

These passes apply only to Go-target (AOT) compilation; bytecode VM paths are unchanged.

## Lambda Lifting

Lambda lifting runs inside `compile-form*`, between `ir.build/build-fn` (source → IR) and `optimize-fn` (optimization pipeline).

### Transform per function

1. **Find candidates:** `:make-closure` instructions whose `:ref[0]` is a function-template `:const`.
2. **Compute free variables** — values referenced via `:load-closed`:
   - **Capture-free** (e.g., yamlstar rule bodies referencing only `parser`) — lift the body verbatim to a new top-level IR.Function.
   - **Capturing** — lift with captured values as explicit leading parameters; update every use-site to pass those captured arguments. (Yamlstar mostly hits capture-free.)
3. **Rewrite closure sites:**
   - **Direct calls** → direct call to the lifted sibling with captured args.
   - **Escapes as a value** (stored in `def`, passed to combinators) → reference to the lifted sibling (if capture-free) or a thin partial-application closure (if capturing). The lifted function is now independently direct-callable.
4. **Deterministic naming:** `<outer-go-name>__lifted<ordinal>`, ordered by build-deterministic first-occurrence of the `:make-closure` instruction. No global gensym counter (avoids known nondeterminism).

### Multi-decl threading

Lifted functions are lowered independently through the optimization pipeline and lowering, producing one `{:status :lowered :decl …}` result per function. These are emitted as a `:multi-fn-template`-shaped result (reusing the existing multi-arity flattening path), so the framework's existing `registry-entry-from-result` registers each lifted sibling in the direct-call registry, making it callable across sites.

## Higher-Order Specialization (Inlining + Partial Evaluation)

Specialization runs inside `optimize-fn`, before type inference, so inlined bodies are type-inferred and become direct-callable.

### Three mechanisms

1. **Inline-eligible call inlining.** When the callee resolves to a known IR.Function (lifted sibling or registered `defn`) and passes eligibility gates, inline the body with arguments substituted.
2. **Partial evaluation / loop unrolling over known sequences.** Combinators loop over variadic `& funcs` arguments. When that arg list is statically known (typical for literal combinator expressions), unroll into a fixed sequence of straight-line iterations. After unrolling, each `(call p f)` has a known target → rewrites to a direct call.
3. **Constant folding of matcher arguments** — delegated to the existing `constfold` pass (e.g., `(first "-")` → character constant).

### Eligibility (automatic, no user annotations)

Derived from existing analyses:

- **Safety gate** (`mutability.lg` `rebinds-var-roots?`) — callee must not mutate var roots (same gate as direct calls).
- **Purity** (`purity.lg`) — informs whether post-inline cleanup (constant folding, common-subexpression elimination, dead-code elimination) is safe.
- **Size/recursion heuristic** — small, non-recursive (or boundedly recursive), and inlining enables a direct call.
- **`name*` transparency** falls out automatically: small wrappers inline and fold by the same rule—no special case needed.

Nothing in these criteria names yamlstar; yamlstar benefits because its combinators are small and its grammar is static—the exact profile these passes target.

### Seeing through `call`

The `call` trampoline is large (state push/pop, receivers, trace, meta, trampoline-on-returned-value, boolean type check). The inliner does **not** wholesale-inline `call`. Once a `(call p f)` has a statically-known `f`, it rewrites to a **direct call to `f`** wrapped only in the semantically-required envelope (return-value trampoline and boolean check). Receiver/trace/state-stack bookkeeping (event/debug machinery) is trimmed in a later stage.

## Multi-Block Inlining (Redesign)

Original inlining handled single-block callees. Multi-block callees (those with loops or branches) require handling the cross-block-ref invariant: a reference must be in the same block, except via block parameters and cheap loads (`:const`/`:load-arg`/`:load-closed`, not `:load-var`). Values must flow through positional block `:params` + branch-target `:args` (indexed-RPN model).

### Tail-position multi-block inlining

Inline a multi-block callee when the call result feeds the caller's `:return` (tail position):

1. **Precondition check:** the caller block's terminator is `:return` whose operand is the call result (tail position).
2. **Clone callee blocks:** for each callee block, create fresh blocks; record block and instruction maps.
3. **Remap intra-block refs** through the instruction map.
4. **Entry wiring:** the callee entry block's `:load-arg i` instructions become `:block-arg i`; terminate the caller block with a `:branch` to the cloned entry, passing call operands as branch `:args`.
5. **Terminator remap:** each cloned terminator's branch targets go through the block map; `add-pred!` for each edge.
6. **Return rewiring:** each cloned `:return v` becomes the caller's `:return` (callee returns become caller returns).
7. **Validate:** `validate-fn!` ensures the cross-block-ref invariant is satisfied.

Why tail-position is safe: there is no continuation block and no value defined-before-call-used-after, so no live-across threading. The invariant is satisfied purely by remapping intra-callee refs and routing operands via entry block-args.

### Fold-over-rest specialization and loop unrolling

At a call to a variadic fold-over-rest combinator with N known rest operands:

1. **Recognize the idiom:** structurally match a tail-loop whose sole loop variable initializes to the rest-arg, each iteration consumes `(first loopvar)` and recurs with `(rest loopvar)`, terminating on `(empty? loopvar)`.
2. **Specialize to fixed arity:** replace the rest-seq `:load-arg` with N explicit parameters; unroll the fold loop into N straight-line iterations (e.g., `any` → `(if (call₀) true (if (call₁) true (if (call₂) false)))`).
3. **Unroll cap:** bounded by `max-unroll`; over-cap leaves the call generic (no silent truncation).
4. **Inline the specialized clone** via tail-position multi-block inlining (now acyclic and tail-shaped at the rule site).
5. **Direct calls emerge:** each unrolled iteration's `((first xs) p)` becomes a direct call to the rule sub-function.

For `any`/`all`, the unrolling is straightforward pure short-circuit logic. `rep` (min/max-bounded repetition) is harder and may be a follow-on.

## Verification and Determinism

Every PR must:
- `make generate` + `make check-generated` clean (regenerates `core_compiled.lgb` + `core_go_lowered/` + checksums).
- **gogen-parity** — lowered Go output runs identically to interpreted.
- **Determinism test** — lifted-sibling names and inlining order driven by structural order, never hash-map iteration.
- Full `go test ./pkg/ir/ -v` green (these passes mutate IR; broad regression scope).
- **yamlstar parse benchmark** — measured native parse time vs 36 ms interpreted baseline.

## Citations

**Resource:** [pkg/rt/core/ir/passes/pipeline.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/passes/pipeline.lg) — pass orchestrator and integration point for lifting and specialization.

**Related passes** (in `pkg/rt/core/ir/passes/`):
- `mutability.lg` — mutation analysis (inlining safety gate)
- `purity.lg` — effect analysis (cleanup eligibility, loop unroll safety)
- `constfold.lg` — constant folding (post-inline cleanup)
- `cse.lg` — common-subexpression elimination (post-inline cleanup)
- `dce.lg` — dead-code elimination (post-inline cleanup)
- `typeinfer.lg` — type inference (refines types after inlining)
- `licm.lg` — loop-invariant code motion (reference for block-parameter threading)

**Design docs** (local, planning/approval stage):
- `docs/superpowers/specs/2026-06-28-lambda-lift-and-higher-order-specialization-design.md` — stages 1+2, lambda lifting and single-block inlining
- `docs/superpowers/specs/2026-06-28-multiblock-inliner-and-loop-unroll-design.md` — redesign of stage 2 for multi-block inlining and loop unrolling

**Related concepts** (this wiki):
- [IR Passes](ir-passes.md) — the optimization pass pipeline and DSL
- [IR Pipeline](ir-pipeline.md) — build, optimize, lower architecture
- [Indexed-RPN IR](indexed-rpn-ir.md) — the IR data model
- [Bytecode Compiler](bytecode-compiler.md) — lowering to bytecode
