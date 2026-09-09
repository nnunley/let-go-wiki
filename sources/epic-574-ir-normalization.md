---
type: Source
category: source
title: "Epic: IR normalization + execution-form cleanup (EPIC-017, issue #574)"
description: "nnunley's public epic on the IR's representation: the structural level as the root cause of bytecode-path gaps, six ranked physical-layout findings from an audit against Carbon SemIR and indexed RPN, and the stories that follow."
tags: [compiler, bytecode, vm, idea]
resource: "https://github.com/nooga/let-go/issues/574"
sources: ["issue: https://github.com/nooga/let-go/issues/574, 2026-09-05"]
created: "2026-09-05"
updated: "2026-09-05"
status: active
---

# Epic: IR normalization + execution-form cleanup (EPIC-017, issue #574)

Open epic by Norman Nunley, making an internal roadmap visible upstream (companion of #575). Its premise comes from an index-RPN execution spike (ITER-0057): the IR's representation mechanics, not the execution model, dominate interpreted performance.

## Key takeaways

- **Root cause:** `structurize` is incomplete (`:try` is not a structural node) and the bytecode backend never adopted the structural level; that one gap explains the cross-block splice rejection and `:try` being unlowerable on the bytecode path.
- **Evidence (2026-07-18):** the stack lowering's junk-below accounting proved fragile, and IR-lowered bytecode runs about twice the direct compiler's instruction count on branch-heavy code, roughly 67% of the excess being branch-arg `DUP_NTH` shuffle.
- **Ranked findings:** packed instruction records (top cost; #558's side table is the interim step), canonicalization and interning, freeze-after-construction (done), blocks as spans, frame width (gates the EPIC-018 tail), typed handles.
- **Unscheduled stories:** `structurize-:try`, `bytecode-adopts-structurize`.
- **Relationships:** feeds the EPIC-016 index-RPN VM re-check; the op-catalog work is the canonicalization half; #528's RPN-spike deletion is held until the verdict.

## Derived pages

[ir-representation-roadmap](../ideas/ir-representation-roadmap.md) · [structurize](../concepts/structurize.md) · [bytecode-lowering](../concepts/bytecode-lowering.md) · [op-catalog](../concepts/op-catalog.md)

# Citations

[1] https://github.com/nooga/let-go/issues/574
