---
type: Concept
category: concept
title: "Op Catalog"
description: "The single-source catalogs behind the IR: the op table in ir_ops.lg that generates the Go op enum and drives per-op facets, the form-head catalog for build-list dispatch, the load-time coherence checks that make a missing row a red build, and the accessor seam that hides the function's shape."
tags: [compiler, bytecode, go, lisp]
resource: "https://github.com/nooga/let-go/blob/main/pkg/ir/ir_ops.lg"
sources:
  - "repo: nooga/let-go pkg/ir/ir_ops.lg, pkg/ir/op_generated.go, pkg/rt/core/ir/{ops,form_heads,lower_go}.lg @ 0911118, 2026-09-05"
  - "pr: nooga/let-go#612 (catalog-driven op dispatch, generated OpByKeyword switch), #667 (form-head catalog + coherence check), #666 (per-op needs-rt contribution rules), #712 (fn shape through accessors); issue #268 (the consolidation epic), 2026-09-05"
  - "lg -e transcripts on lg 1.12.3-0.20260904132133 (0911118), 2026-09-05"
created: "2026-09-05"
updated: "2026-09-05"
status: stable
---

# Op Catalog

The [IR](indexed-rpn-ir.md) has a small vocabulary of ops (39 at `0911118`), and each op has facts: how many operands it pops, whether it pushes a result, whether it is pure, whether it terminates a block, which bytecode it maps to, how it is typed, how it lowers to Go. Norman's 2026 refactors (#612, #666, #667, #712, under the consolidation epic #268) moved those facts out of the `cond` arms in `build.lg`, `lower.lg`, `lower_go.lg`, and `typeinfer.lg` into catalogs that every consumer queries, and added checks that fail the build when a catalog and a consumer disagree. The design rule they share: a fact about an op lives in one column, and a consumer that needs it asks rather than repeating it.

## The op table

`pkg/ir/ir_ops.lg` holds one vector per op, and order is load-bearing because the Go enum is positional. Columns:

| Column | Meaning |
|---|---|
| `name`, `display`, `comment` | generates `Op<name>` and the `opTable` row |
| `stk-in`, `stk-out` | operands popped (`-1` variadic) and results pushed (0 or 1) |
| `pure?` | safe to CSE, fold, or hoist |
| `term?` | ends a basic block |
| `bytecode` | the `vm.OP_*` the [bytecode lowering](bytecode-lowering.md) emits, or `nil` |
| `cheap?` | `materialize!` may re-emit it at the use site (`Const`, `LoadArg`, `LoadVar`, `LoadClosed`) |
| `local-carry?` | the Go lowering materializes its result into a Go local (#612 §1) |
| `infer?`, `lower?` | the op's type-inference and Go-lowering facets are reified on an `ir.ops` op-type |

Running the file generates `pkg/ir/op_generated.go` (a [generated artifact](generated-artifacts.md)): the `Op` type, the `iota` constant block, `opInfo`, `opTable`, and the `Op` methods, all built through `gogen`'s `gquote`. #612 §2b added a generated `opByKeywordExact` string switch so the canonical keyword-to-op lookup is a `switch` rather than a scan; the PR measured it at 57 ns to 2.1 ns and allocation-free, with non-canonical spellings falling through to the lenient scan.

## Reified op facets

`ir.ops` (in `pkg/rt/core/ir/ops.lg`) defines an `IROp` protocol and one `deftype` per reified op, co-locating that op's `infer` and `lower-stmts` behaviour instead of scattering them across `typeinfer.lg` and `lower_go.lg`. `op-registry` maps the keyword to the instance. The dispatch sites consult the catalog's `infer?` and `lower?` columns first and fall back to their legacy `cond` arm for ops not yet reified.

Coherence is enforced at load time: the facet columns are the closed member set, and the check at the end of `ops.lg` throws when the columns and `op-registry` drift; `infer-op` and `lower-op` throw rather than return `nil` when asked for a facet'd op they cannot dispatch. Adding a facet is a red build until catalog column, registry entry, and dispatch arm all agree. `ir.ops` is a leaf namespace that requires only `ir.data` and `ir.lattice`, which keeps it below `typeinfer` and `lower-go` in the load order.

#666 applied the same shape to one more fact: whether a lowered function needs runtime access (`function-needs-rt?`) used to be several scattered conditionals, and is now `op-contributes-rt?`, a per-op contribution rule folded with OR over the function's instructions, with regression gates that turn red if either conditional case is flattened.

## The form-head catalog

The source side has its own catalog. `form_heads.lg` lists the 14 special-form heads `build-list` handles, each with whether `free-vars` and `captures-of` need an explicit handler for it (#667). `build-list` dispatches through a catalog-keyed handler lookup instead of a hardcoded `cond` chain, and the two scope functions derive their membership sets from catalog queries, precomputed once at load. The coherence check is bidirectional: a form missing from the catalog, or a catalogued form without a handler, fails generation naming the form. The check announces itself whenever the pipeline loads:

```
$ lg -e "(require 'ir.passes.pipeline)"
ir.form-heads catalog loaded (catalog validation passed)
ir.form-heads catalog loaded (bidirectional coherence check passed)
```

## The accessor seam

The catalogs describe ops; the function's shape is a separate representation, and #712 closed the last thirteen places that reached past `ir.data` into `(:insts @f)` and `(:blocks @f)` directly. It added the accessors that were missing (`all-insts`, `raw-blocks`, `all-types`, documented as representation-shaped and a last resort) and moved every caller onto them, so no `@f` remains outside the data layer. That is the precondition for the representation work in [the IR roadmap](../ideas/ir-representation-roadmap.md): packed instruction records can only move underneath callers that never touched the flat tables. One trap the PR recorded: a `defn` added to `ir/data.lg` is invisible until it is also listed in the intern block at the bottom of the file, and forgetting it fails at namespace load with a message naming an unrelated pass.

## Citations

**Resource:** [pkg/ir/ir_ops.lg](https://github.com/nooga/let-go/blob/main/pkg/ir/ir_ops.lg): the op table and the generator

**Related:**
- [pkg/rt/core/ir/ops.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/ops.lg): `IROp`, `op-registry`, the load-time coherence check
- [pkg/rt/core/ir/form_heads.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/form_heads.lg): the form-head catalog
- [pkg/rt/core/ir/lower_go.lg](https://github.com/nooga/let-go/blob/main/pkg/rt/core/ir/lower_go.lg): `op-contributes-rt?`
- PRs: [#612](https://github.com/nooga/let-go/pull/612), [#666](https://github.com/nooga/let-go/pull/666), [#667](https://github.com/nooga/let-go/pull/667), [#712](https://github.com/nooga/let-go/pull/712); epic [#268](https://github.com/nooga/let-go/issues/268)

See also: [Indexed-RPN IR](indexed-rpn-ir.md), [IR Pipeline](ir-pipeline.md), [IR Passes](ir-passes.md), [let-go](../entities/let-go.md)
