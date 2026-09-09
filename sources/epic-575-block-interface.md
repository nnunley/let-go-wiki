---
type: Source
category: source
title: "Epic: block interface as shared liveness metadata + block-arg erasure (EPIC-018, issue #575)"
description: "nnunley's public epic for the cross-block and locals half of the IR work: shared liveness on the block interface, real locals for the stack VM, and erasing single-source block-args, with a story ledger and a sequencing gate."
tags: [compiler, bytecode, vm, idea]
resource: "https://github.com/nooga/let-go/issues/575"
sources: ["issue: https://github.com/nooga/let-go/issues/575, 2026-09-05"]
created: "2026-09-05"
updated: "2026-09-05"
status: active
---

# Epic: block interface as shared liveness metadata + block-arg erasure (EPIC-018, issue #575)

Open epic by Norman Nunley, companion of #574. Block-args are the stack VM's accommodation for missing locals: every cross-block value is threaded through branch-target arguments, and `lower.lg` rejects any direct cross-block reference (`check-cross-block!`).

## Key takeaways

- **Done (backend-independent):** STORY-0068 shared per-block liveness (`ir.passes.liveness`), 0069 relocating ad-hoc reachability helpers onto it (`lower_go`'s `live-nids` was the one real duplicate), 0070 the single-value resolver, 0071 block-arg classification and census.
- **Pending (backend-coupled):** 0072 `OP_LOAD_LOCAL`/`OP_STORE_LOCAL`, 0073 resolver lowering that retires `check-cross-block!` and the junk-below class, 0074 retiring the fold-outline workaround so the general inliner unblocks on bytecode.
- **Gate:** held until the EPIC-016 index-RPN VM re-check; a go verdict supersedes the stack-VM half.
- **Why now:** the DUP shuffle is about 67% of the 2× instruction bloat, and the junk-below bookkeeping is the source of a class of latent miscompiles now guarded by fallback at the cost of coverage.

## Derived pages

[block-interface-and-liveness](../concepts/block-interface-and-liveness.md) · [ir-representation-roadmap](../ideas/ir-representation-roadmap.md) · [bytecode-lowering](../concepts/bytecode-lowering.md)

# Citations

[1] https://github.com/nooga/let-go/issues/575
