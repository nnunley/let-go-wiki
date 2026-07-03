---
type: Source
category: source
title: VM performance and calling convention audit
description: Design document detailing VM interpreter bottlenecks, calling convention optimization, and a phased plan to reduce GC pressure and improve bytecode call performance.
tags:
  - vm
  - runtime
  - bytecode
  - reference
resource: https://github.com/nooga/let-go/blob/main/docs/design/vm-performance-optimization.md
sources:
  - "repo: nooga/let-go docs/design/vm-performance-optimization.md, 2026-06-07"
created: "2026-07-03"
updated: "2026-07-03"
status: active
---

## About this source

This document is an audit and optimization plan for the let-go VM interpreter ([stack-vm](../concepts/stack-vm.md)) and its calling convention. Authored by the let-go team and last verified on 2026-06-05, it identifies concrete performance bottlenecks in function calls and proposes a three-phase rollout to reduce memory retention, GC pressure, and call overhead.

## Key contributions

- **Identified hotspots**: Frame/stack allocation per call, argument slices retaining caller stack backing arrays, TCO limited to `*Func` (not `*Closure`), and generic invocation overhead.
- **Retention bug**: Argument slices created in `OP_INVOKE` reference the caller's `f.stack` array, causing the callee frame to retain the entire stack for its lifetime—a significant memory leak in call-heavy workloads.
- **Phased optimization roadmap**:
  - **Phase A** (correctness): Copy args before bytecode calls; extend TCO to closures.
  - **Phase B** (throughput): Introduce frame/stack pools; add `INVOKE_0/1/2/3` and `TAIL_CALL_0/1/2/3` opcodes; ensure native functions use direct wrappers.
  - **Phase C** (iteration): Add `Reducible` interface and chunked seqs for collection fast paths.
- **Concrete file pointers** to `pkg/vm/vm.go`, `pkg/vm/func.go`, `pkg/vm/native_func.go`, and `pkg/rt/lang.go`, with specific line references and implementation checklist.

## Relevant concepts

- [stack-vm](../concepts/stack-vm.md) — The bytecode interpreter loop and calling convention.
- [ir-optimizations](../concepts/ir-optimizations.md) — Compiler and [ir-pipeline](../concepts/ir-pipeline.md) optimizations that complement VM-level improvements.

## Derived pages

- [stack-vm](../concepts/stack-vm.md) — Bytecode interpreter architecture and calling convention.
- [ir-optimizations](../concepts/ir-optimizations.md) — IR-level compilation optimizations.

# Citations

```bibtex
@inproceedings{let-go-vm-perf,
  title={VM performance and calling convention — audit and optimization plan},
  author={let-go team},
  journal={let-go design docs},
  year={2026},
  url={https://github.com/nooga/let-go/blob/main/docs/design/vm-performance-optimization.md},
  note={Last verified: 2026-06-05}
}
```
