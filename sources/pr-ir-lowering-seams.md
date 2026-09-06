---
type: Source
category: source
title: "IR lowering seams and census (PRs #579, #580, #647, #648, #649)"
description: "nnunley's 2026-07/08 changes to the bytecode lowering and its measurement: var-load re-emission with a shape ratchet, strict mode with the first bytecode-path census, the def+name* seam, block-junk agreement with RPO order, and tail-call fusion."
tags: [compiler, bytecode, vm]
resource: "https://github.com/nooga/let-go/pull/580"
sources: ["pr: https://github.com/nooga/let-go/pull/580, 2026-09-05"]
created: "2026-09-05"
updated: "2026-09-05"
status: active
---

# IR lowering seams and census (PRs #579, #580, #647, #648, #649)

Five PRs by Norman Nunley, merged 2026-07-22 to 2026-08-18.

## Key takeaways

- **#579:** ordinary `:load-var` re-emitted per use (only `set!` targets materialise once); ir-stress failures 20 to 11, the `:validate/cross-block-ref` bucket retired; `fib` 24 to 23 instructions; a stack-discipline test pins the emitted shape. Names the missing structural level as the residual cause.
- **#580:** `*ir-compile-strict*` (throw instead of silent fallback); a `:lower` census mode with its own baseline; first measurement of the bytecode path at 70.7% versus 99.5% for Go; the 535 not-on-stack failures traced to discarding instruction indices for stack depths; comparison with fmpl's direct execution of indexed IR.
- **#647:** `(def x (name* ... (fn ...)))` routed through the IR path, proven by a strict-mode throw.
- **#648:** every fall-through predecessor must agree on junk-below (mismatch aborts and falls back); RPO block order; 223 newly lowering forms, 79 more in the block-arg bucket.
- **#649:** a single-use `:call` in return position emits `TAIL_CALL`; ratchet within noise.

## Derived pages

[bytecode-lowering](../concepts/bytecode-lowering.md) · [compile-paths](../concepts/compile-paths.md) · [block-interface-and-liveness](../concepts/block-interface-and-liveness.md) · [perf-ratchet](../concepts/perf-ratchet.md)

# Citations

[1] https://github.com/nooga/let-go/pull/580
